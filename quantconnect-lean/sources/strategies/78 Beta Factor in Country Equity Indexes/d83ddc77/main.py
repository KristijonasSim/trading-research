from Alphas.ConstantAlphaModel import ConstantAlphaModel
from AlphaModel import BetaAlphaModel
from Risk.NullRiskManagementModel import NullRiskManagementModel
from datetime import datetime
from PortfolioConstructionModel import MonthlyPortfolioConstructionModel

class BetaAlgorithm(QCAlgorithmFramework):

    def Initialize(self):

        self.SetStartDate(2012, 1, 1)   #Set Start Date
        self.SetEndDate(2018, 3, 1)    #Set End Date
        self.SetCash(100000)            #Set Strategy Cash

        self.UniverseSettings.Resolution = Resolution.Daily
        tickers =  [
                    "EWJ",  # iShares MSCI Japan Index ETF
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
        symbols = [Symbol.Create(ticker, SecurityType.Equity, Market.USA) for ticker in tickers]
        self.SetUniverseSelection(ManualUniverseSelectionModel(symbols))
        self.SetAlpha(BetaAlphaModel())
        self.SetPortfolioConstruction(MonthlyPortfolioConstructionModel())
        self.SetExecution(ImmediateExecutionModel())
        self.SetRiskManagement(NullRiskManagementModel())
        self.AddEquity("SPY", Resolution.Daily)