'''
https://www.quantitativo.com/p/robustness-of-the-211-sharpe-mean
focus on sp500 constituents

'''

from AlgorithmImports import *

from collections import deque
from datetime import time, timedelta
import numpy as np
import requests
import pandas as pd


class SymbolData:
    def __init__(self, symbol, algo):

        self.symbol = symbol
        self.close = 0.0
        self.open = 0.0
        self.high = 0.0
        self.low = 0.0

        self.close_on_open_trigger = False
        self.long_on_open_trigger = False
        self.todays_high = 0.0
        self.todays_low = 999999.9
        self.yesterdays_high = 0.0
        self.yesterdays_close = 0.0

        # Rolling Mean High Minus Low
        self.rolling_mean_length = 25
        self.rolling_mean_high_low_list = deque(maxlen=self.rolling_mean_length)
        
        # SMA
        self.rolling_sma_list = deque(maxlen=200)

        ## Lower band
        self.lower_band_multiple = 2.5
        self.rolling_high_list = deque(maxlen=10)

        ## ATR
        self.atr = None
        self.atr_periods = 10
        self.atr_values_list = deque(maxlen=self.atr_periods)

        ## Volume
        self.volume_history_days = 60
        self.volumes_list = deque(maxlen=self.volume_history_days)
        self.todays_total_volume = 0.0

         
        # Initialize technical indicators
        self.ibs = 0.0
        self.lower_band = 0.0
        self.natr = 0

    def update(self, bar, algo): 

        self.high, self.low, self.close, self.open, self.volume = bar.High, bar.Low, bar.Close, bar.Open, bar.Volume

        ## Daily high/low
        self.todays_high = max(self.todays_high, self.high)
        self.todays_low = min(self.todays_low, self.low)

        self.todays_total_volume = self.todays_total_volume + self.volume
        
        # algo.Debug(f'{algo.Time} {self.symbol} UPDATED {self.high} {self.todays_high}')

    def update_eod(self, algo):
        # algo.Debug(f'{algo.Time} : update_eod running')

        self.rolling_high_list.append(self.todays_high)
        self.rolling_mean_high_low_list.append(self.todays_high - self.todays_low)
        self.rolling_sma_list.append(self.close)
        self.volumes_list.append(self.todays_total_volume)

        ## ATR
        tr = max(self.todays_high - self.todays_low, abs(self.todays_high - self.yesterdays_close), abs(self.todays_low - self.yesterdays_close))
        self.atr_values_list.append(tr)
        self.atr = np.mean(self.atr_values_list)
        # normalized
        self.natr = self.atr / self.close


        ## Rolling Mean High Minus Low
        if len(self.rolling_mean_high_low_list) >= self.rolling_mean_length:
            high_low_mean = np.mean(self.rolling_mean_high_low_list)

            ## Lower band
            self.lower_band = max(self.rolling_high_list) - self.lower_band_multiple * high_low_mean

        ## IBS
        if self.todays_high != self.todays_low:
            self.ibs = (self.close - self.todays_low) / (self.todays_high - self.todays_low)
        else:
            self.ibs = 0.0
    
    def eod_reset(self):
        self.yesterdays_high = self.todays_high
        self.todays_high = 0.0
        self.todays_low = 999999.9
        self.yesterdays_close = self.close
        self.todays_total_volume = 0.0

class MyAlgorithm(QCAlgorithm):
    def Initialize(self):
        '''
        This method is the entry point of your algorithm where you define a series of settings.
        LEAN only calls this method one time, at the start of your algorithm.
        '''
        self.Debug(f'--- Initializing Algorithm ----')
        
        self.SetStartDate(2023, 1, 1)
        self.SetEndDate(2024, 7, 10)
        self.SetCash(100000)
        self.set_benchmark("SPY")
        
        # Define universe selection method
        self.AddEquity("SPY", Resolution.Minute)

        # Use Filter to select universe based on market cap and price
        self.universe_settings.asynchronous = True
        self.UniverseSettings.Resolution = Resolution.Minute
        self.add_universe(self.universe.etf("SPY"))
        
        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, AccountType.MARGIN)
        self.portfolio.set_positions(SecurityPositionGroupModel.NULL)
        self.universe_settings.leverage = 10
        
        # self.set_brokerage_model(BrokerageName.ALPACA)

        # Initialize market open and close times
        self.market_open_time = time(9, 31)
        self.market_close_time = time(15, 59)
        
        self.number_of_stocks = 3
        self.symbol_data = {}
        self.buy_on_open_list = []

        self.store_trades = ''
        self.store_decisions = ''
        self.store_holdings = ''
        self.store_longlist = ''
        self.store_longlist_entries = ''
        self.errors = ''

        ## IBS
        self.ibs_threshold = 0.3


    def OnData(self, data):
        
        if self.Time.hour == 0:
            return

        # Update the indicator values
        for symbol in self.symbol_data:

            try:
                bar = data.Bars[symbol]

                symboldata = self.symbol_data[symbol]
                symboldata.update(bar, self)
            except:
                continue
                # maybe newly added to universe and no tradebar?
        
        # Check if we need to close

        ## MARKET OPEN
        if self.Time.time() == self.market_open_time:
            self.check_close_on_open()
            self.check_buy_on_open()

        ## MARKET CLOSE
        elif self.Time.time() == self.market_close_time:
            # self.Debug(f'{self.Time} market close time')
            self.update_eod_data() # update last data and calculate EOD
            self.check_closure_close_sma()
            self.check_closure_eod() 
            self.check_long_eod()
            self.eod_reset_data()

    def check_closure_close_sma(self):
        # self.Debug(f'{self.Time} checking closure hourly')

        currInvested = [x.Symbol for x in self.Portfolio.Values if x.Invested]
        
        for symbol in currInvested:
            try:
                symboldata = self.symbol_data[symbol]
                sma_list = symboldata.rolling_sma_list
                sma_length = len(sma_list)
                sma_value = np.mean(sma_list)
                low = symboldata.low
                close = symboldata.close

                # We will close the trade whenever the price is lower than the 200-day SMA;
                if close < sma_value:
                    # self.Debug(f'{self.Time} !! closing symbol {symbol}, low {low} < sma {sma}')
                    self.Liquidate(symbol)

                    ## DATASTORE
                    # Trades
                    data = {'time': self.Time, 'symbol': symbol.value, 'low': low, 'close': close, 'sma': sma_value, 'direction': 'liquidate'}
                    self.store_trades += f'{data},'

                    # Decision
                    data = {'time': self.Time, 'symbol': symbol.value, 'reason': 'closing_because_low<sma', 'low': low, 'close': close, 'sma': sma_value, 'sma_length': sma_length}
                    self.store_decisions += f'{data},'
            except:
                self.Debug(f'{self.Time} {symbol} couldnt close hourly as symbol data missing. Maybe delisted?')

    def check_buy_on_open(self):
        # self.Debug(f'{self.Time} checking long on open')
        for symbol in self.buy_on_open_list:
            ## DATASTORE
            data = {'time': self.Time, 'symbol': symbol.value}
            self.store_longlist += f'{data},'

            if symbol in self.symbol_data:
                holding_percentage = (1 / self.number_of_stocks) * 0.9
                # self.Debug(f'{symbol} setting holding for {holding_percentage}%')

                self.set_holdings(symbol, holding_percentage)

                ## DATASTORE
                symboldata = self.symbol_data[symbol]
                sma_list = symboldata.rolling_sma_list
                sma_value = np.mean(sma_list)
                low = symboldata.low
                close = symboldata.close

                num_holdings = sum(x.Invested for x in self.Portfolio.Values)

                data = {'time': self.Time, 'symbol': symbol.value, 'low': low, 'close': close, 'sma': sma_value, 'direction': 'long', 'amount': holding_percentage, 'num_holdings': num_holdings}
                self.store_trades += f'{data},'
            else:
                data = {'time': self.Time, 'symbol': symbol.value, 'error': 'symbol in self.buyonopen list but not in symobl_data'}
                self.errors += f'{data},'

        self.buy_on_open_list = []

    def check_close_on_open(self):
        # self.Debug(f'{self.Time} checking close on open')

        currInvested = [x.Symbol for x in self.Portfolio.Values if x.Invested]

        for symbol in currInvested:
            
            if symbol not in self.symbol_data:
                # self.Debug(f'{self.Time} !! 350 {symbol} no longer found in symbol_data. CLosing.')
                self.Liquidate(symbol)

                ## DATASTORE
                # Trades
                data = {'time': self.Time, 'symbol': symbol.value, 'direction': 'liquidate'}
                self.store_trades += f'{data},'

                # Decision
                data = {'time': self.Time, 'symbol': symbol.value, 'reason': 'closing as dropped from symbol_data'}
                self.store_decisions += f'{data},'

            else:
                symboldata = self.symbol_data[symbol]

                if symboldata.close_on_open_trigger:
                    # self.Debug(f'{self.Time} !! {symbol} Closing on market open!')
                    self.Liquidate(symbol)
                    
                    ## DATASTORE
                    # Trades
                    data = {'time': self.Time, 'symbol': symbol.value, 'direction': 'liquidate'}
                    self.store_trades += f'{data},'

                    symboldata.close_on_open_trigger = False

    def update_eod_data(self):
        # self.Debug(f'{self.Time} running update_eod_data')
        for symbol in self.symbol_data:
            self.symbol_data[symbol].update_eod(self)

    def check_closure_eod(self):
        holdings_list = [str(symbol) for symbol in self.Portfolio.Keys if self.Portfolio[symbol].Invested]
        self.Debug(f"{self.Time} EOD: Securities Held: {holdings_list}")
        
        ## OBJECT SORE
        data = {'time': self.Time, 'holdings': holdings_list}
        self.store_holdings += f'{data},'

        currInvested = [x.Symbol for x in self.Portfolio.Values if x.Invested]

        for symbol in currInvested:
            symboldata = self.symbol_data[symbol]

            close = symboldata.close
            yesterdays_high = symboldata.yesterdays_high

            # When the stock closes above yesterday's high, we will exit on the next open;
            if close > yesterdays_high:
                # self.Debug(f'{self.Time} {symbol} will close on tomorrows open as close {close} > yesterday high {yesterdays_high}')
                symboldata.close_on_open_trigger = True
                sma_list = symboldata.rolling_sma_list
                sma_length = len(sma_list)
                sma_value = np.mean(sma_list)

                # Decision
                data = {'time': self.Time, 'symbol': symbol.value, 'reason': 'closing as close>yesterday_hight', 'yesterdays_high':yesterdays_high, 'close': close, 'sma': sma_value, 'sma_length': sma_length}
                self.store_decisions += f'{data},'

    def check_long_eod(self):
        symbols_long_list = {}

        num_holdings = sum(x.Invested for x in self.Portfolio.Values)

        for symbol in self.symbol_data:

            if not self.Portfolio[symbol].Invested:

                symboldata = self.symbol_data[symbol]
                sma_list = symboldata.rolling_sma_list
                sma_length = len(sma_list)

                # for i, value in enumerate(sma.Window):
                #     self.Debug(f"{i}: {value.Time}, {value.Value}")

                # self.Debug(f"{self.Time} sma ready {sma.is_ready}")

                close = symboldata.close

                if sma_length == 200 and close > 10:
                        
                    # self.Debug(f"{self.Time} {symbol} close: {symboldata.close} high: {symboldata.todays_high} low: {symboldata.todays_low} yesthigh: {symboldata.yesterdays_high} yest close: {symboldata.yesterdays_close} vol: {symboldata.todays_total_volume} sma: {sma.current.value} ")

                    lower_band = symboldata.lower_band
                    ibs = symboldata.ibs
                    natr = symboldata.natr
                    sma_value = np.mean(sma_list)

                    # Only trade the stock if the allocated capital for the trade does not exceed 5% of the stock's median ADV of the past 3 months
                    allocation_per_symbol = self.portfolio.total_portfolio_value / self.number_of_stocks
                    adv_median = np.median(symboldata.volumes_list)             

                    if adv_median > allocation_per_symbol:
                            
                        # closes under the lower band, and IBS is lower than 0.3, we go long at the next open
                        if close < lower_band and ibs < self.ibs_threshold and close > sma_value:

                            # self.Debug(f'{self.Time} {symbol} meets entry criteria: close {close} lower band {lower_band} ibs {ibs} sma {sma}. adv_median {adv_median} allocation per symbol {allocation_per_symbol}')
                            
                            symbols_long_list[symbol] = natr

                            ## DATASTORE
                            data = {'time': self.Time, 'symbol': symbol.value, 'lower_band': lower_band,'ibs':ibs,'sma':sma_value,'natr':natr, 'adv_median':adv_median,'close':close,'sma_length':sma_length, 'num_holdings': num_holdings}
                            self.store_longlist_entries += f'{data},'

        # Sort them by volatility (Normalized Average True Range) and prioritize the most volatile ones;
        symbols_long_list_sorted = sorted(symbols_long_list.items(), key=lambda x: x[1], reverse=True)
        num_holdings = sum(x.Invested for x in self.Portfolio.Values)
        number_of_available_stocks = self.number_of_stocks - num_holdings
        top_symbols = [item[0] for item in symbols_long_list_sorted[:number_of_available_stocks]]

        self.buy_on_open_list = top_symbols

        # self.Debug(f'{self.Time} length of long symbols list {len(self.buy_on_open_list)}')

    def eod_reset_data(self):
        # self.Debug(f'{self.Time} running eod_reset_data')
        for symbol in self.symbol_data:
            self.symbol_data[symbol].eod_reset()

    def on_securities_changed(self, changes: SecurityChanges) -> None:
        for security in changes.added_securities:

            if security.symbol == 'SPY':
                continue

            if security.symbol not in self.symbol_data:
           
                self.symbol_data[security.symbol] = SymbolData(security.symbol, self)


        for security in changes.removed_securities:
            # self.debug(f"{self.time}: Universe: Removed {security.symbol}")
            
            if security.symbol in self.symbol_data:
                self.symbol_data.pop(security.symbol)

        # self.Debug(f'{self.Time} - len of entire universe = {len(self.symbol_data)}')

    def on_end_of_algorithm(self):
        self.object_store.save('store_trades', self.store_trades)
        self.object_store.save('store_decisions', self.store_decisions)
        self.object_store.save('store_holdings', self.store_holdings)
        self.object_store.save('store_longlist_entries', self.store_longlist_entries)
        self.object_store.save('store_longlist', self.store_longlist)
        self.object_store.save('errors', self.errors)