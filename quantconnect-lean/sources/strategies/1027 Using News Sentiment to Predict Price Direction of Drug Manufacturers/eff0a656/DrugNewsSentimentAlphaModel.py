from QuantConnect.Data.Custom.Tiingo import *
from SentimentByPhrase import SentimentByPhrase
from nltk.util import ngrams

class DrugNewsSentimentAlphaModel(AlphaModel):
    """
    This class emits insights to take long intraday positions for securities 
    that have positive news sentiment.
    """
    symbol_data_by_symbol = {}
    sentiment_by_phrase = SentimentByPhrase.dictionary
    max_phrase_words = max([len(phrase.split()) for phrase in sentiment_by_phrase.keys()])
    sign = lambda _, x: int(x and (1, -1)[x < 0])
    
    
    def __init__(self, bars_before_insight=30):
        """
        Input:
         - bars_before_insight
            The number of bars to wait each morning before looking to emit insights
        """
        self.bars_before_insight = bars_before_insight
    
    
    def Update(self, algorithm, data):
        """
        Called each time our alpha model receives a new data slice.
        
        Input:
         - algorithm
            Algorithm instance running the backtest
         - data
            A data structure for all of an algorithm's data at a single time step
        
        Returns a list of Insights to the portfolio construction model
        """
        insights = []
        
        for symbol, symbol_data in self.symbol_data_by_symbol.items():
        
            # If it's after-hours or within 30-minutes of the open, update
            # cumulative sentiment for each symbol    
            if symbol_data.bars_seen_today < self.bars_before_insight:
                tiingo_symbol = symbol_data.tiingo_symbol
                if data.ContainsKey(tiingo_symbol) and data[tiingo_symbol] is not None:
                    article = data[tiingo_symbol]
                    symbol_data.cumulative_sentiment += self.CalculateSentiment(article)
        
            if data.ContainsKey(symbol) and data[symbol] is not None:
                symbol_data.bars_seen_today += 1

                # 30-mintes after the open, emit insights in the direction of the cumulative sentiment.
                # Only emit insights on Wednesdays to capture the analomaly documented by Berument and 
                # Kiymaz (2001).
                if symbol_data.bars_seen_today == self.bars_before_insight and data.Time.weekday() == 2:
                    next_close_time = symbol_data.exchange.Hours.GetNextMarketClose(data.Time, False)
                    direction = self.sign(symbol_data.cumulative_sentiment)
                    if direction == 0:
                        continue
                    insight = Insight.Price(symbol, 
                                            next_close_time - timedelta(minutes=2),
                                            direction)
                    insights.append(insight)
        
                # At the close, reset the cumulative sentiment
                if not symbol_data.exchange.DateTimeIsOpen(data.Time):
                    symbol_data.cumulative_sentiment = 0
                    symbol_data.bars_seen_today = 0
        
        return insights
        
        
    def OnSecuritiesChanged(self, algorithm, changes):
        """
        Called each time our universe has changed.
        
        Input:
         - algorithm
            Algorithm instance running the backtest
         - changes
            The additions and subtractions to the algorithm's security subscriptions
        """
        for security in changes.AddedSecurities:
            self.symbol_data_by_symbol[security.Symbol] = SymbolData(security, algorithm)

        for security in changes.RemovedSecurities:
            symbol_data = self.symbol_data_by_symbol.pop(security.Symbol, None)
            if symbol_data:
                algorithm.RemoveSecurity(symbol_data.tiingo_symbol)
            
    
    def CalculateSentiment(self, article):
        """
        Calculates the sentiment of a Tiingo news article by analyzing the article's
        title and description. We utilize a dictionary of sentiment values composed
        by experts in the domain who reviewed news articles over several years.
        
        Input:
         - article
            Tiingo news article object
            
        Returns the sentiment value of the article.
        """
        sentiment = 0
        for content in (article.Title, article.Description):
            words = content.lower().split()
            for num_words in range(1, self.max_phrase_words + 1):
                for gram in ngrams(words, num_words):
                    phrase = ' '.join(gram)
                    if phrase in self.sentiment_by_phrase.keys():
                        sentiment += self.sentiment_by_phrase[phrase]
        return sentiment


class SymbolData:
    """
    This class is used to store information on each security in the universe and
    initilize the Tiingo news feeds for the security.
    """
    cumulative_sentiment = 0
    bars_seen_today = 0
    
    def __init__(self, security, algorithm):
        self.exchange = security.Exchange
        self.tiingo_symbol = algorithm.AddData(TiingoNews, security.Symbol).Symbol