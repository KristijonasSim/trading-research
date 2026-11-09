# https://quantpedia.com/Screener/Details/15
import pandas as pd
from datetime import datetime

class CountryEquityIndexesMomentumAlgorithm(QCAlgorithm):

    def Initialize(self):

        self.SetStartDate(2002, 1, 1)  
        self.SetEndDate(datetime.now())  
        self.SetCash(100000) 
        # create a dictionary to store momentum indicators for all symbols 
        self.data = {}
        period = 6*21
        # choose ten sector ETFs
        self.symbols = ["EWJ",  # iShares MSCI Japan Index ETF
                        "EZU",  # iShares MSCI Eurozone ETF
                        "EFNL", # iShares MSCI Finland Capped Investable Market Index ETF
                        "EWW",  # iShares MSCI Mexico Inv. Mt. Idx
                        "ERUS", # iShares MSCI Russia ETF
                        "IVV",  # iShares S&P 500 Index
                        "ICOL", # Consumer Discretionary Select Sector SPDR Fund
                        "AAXJ", # iShares MSCI All Country Asia ex Japan Index ETF
                        "AUD",  # Australia Bond Index Fund
                        "EWQ",  # iShares MSCI France Index ETF
                        "BUND", # Pimco Germany Bond Index Fund
                        "EWH",  # iShares MSCI Hong Kong Index ETF
                        "EPI",  # WisdomTree India Earnings ETF
                        "EIDO"  # iShares MSCI Indonesia Investable Market Index ETF
                        "EWI",  # iShares MSCI Italy Index ETF
                        "GAF",  # SPDR S&P Emerging Middle East & Africa ETF
                        "ENZL", # iShares MSCI New Zealand Investable Market Index Fund
                        "NORW"  # Global X FTSE Norway 30 ETF
                        "EWY",  # iShares MSCI South Korea Index ETF
                        "EWP",  # iShares MSCI Spain Index ETF
                        "EWD",  # iShares MSCI Sweden Index ETF
                        "EWL",  # iShares MSCI Switzerland Index ETF
                        "GXC",  # SPDR S&P China ETF
                        "EWC",  # iShares MSCI Canada Index ETF
                        "EWZ",  # iShares MSCI Brazil Index ETF
                        "ARGT", # Global X FTSE Argentina 20 ETF
                        "AND",  # Global X FTSE Andean 40 ETF
                        "AIA",  # iShares S&P Asia 50 Index ETF
                        "EWO",  # iShares MSCI Austria Investable Mkt Index ETF
                        "EWK",  # iShares MSCI Belgium Investable Market Index ETF
                        "BRAQ", # Global X Brazil Consumer ETF
                        "ECH",  # iShares MSCI Chile Investable Market Index ETF
                        "CHIB", # Global X China Technology ETF
                        "EGPT", # Market Vectors Egypt Index ETF
                        "ADRU"] # BLDRS Europe 100 ADR Index ETF

        for symbol in self.symbols:
            self.AddEquity(symbol, Resolution.Daily)

    def OnData(self, data):
        if not self.Portfolio.Invested:
            for symbol in self.symbols:           
                self.SetHoldings(symbol, 1/len(self.symbols))