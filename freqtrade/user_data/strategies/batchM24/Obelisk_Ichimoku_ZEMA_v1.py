# --- Do not remove these libs ---
from freqtrade.strategy import IStrategy, merge_informative_pair, DecimalParameter, IntParameter
from pandas import DataFrame
import talib.abstract as ta
# import freqtrade.vendor.qtpylib.indicators as qtpylib

# --------------------------------
import pandas as pd
import numpy as np
import technical.indicators as ftt
from freqtrade.exchange import timeframe_to_minutes
import logging
import math
import backtrader as bt

from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.configuration import load_config
import freqtrade.vendor.qtpylib.indicators as qtpylib

from technical.util import resample_to_interval
from utils import common

logger = logging.getLogger(__name__)


def ssl_atr(dataframe, length=7):
  df = dataframe.copy()
  df['smaHigh'] = df['high'].rolling(length).mean() + df['atr']
  df['smaLow'] = df['low'].rolling(length).mean() - df['atr']
  df['hlv'] = np.where(
      df['close'] > df['smaHigh'], 1,
      np.where(df['close'] < df['smaLow'], -1, np.NAN))
  df['hlv'] = df['hlv'].ffill()
  df['sslDown'] = np.where(df['hlv'] < 0, df['smaHigh'], df['smaLow'])
  df['sslUp'] = np.where(df['hlv'] < 0, df['smaLow'], df['smaHigh'])
  return df['sslDown'], df['sslUp']


# One issue in general with FT usage:
# FT returns new dataframes that are expected in checks from other functions,
# like next() etc.


# Actual class used by BackTrader
class BT_Ichimoku_Proxy(bt.Strategy):
  params = (
      ('fast', 50),
      ('slow', 200),
      ('order_percentage', 0.05),
  )

  def __init__(self):
    ft_config = load_config.load_config_file(common.FREQTRADE_CONFIG_DEFAULT)
    self.ft_ichimoku = FreqTrade_Obelisk_Ichimoku_ZEMA_v1(ft_config)
    self.crossovers = []
    dataframe = self.data.p.dataname
    self.ft_ichimoku.dataframe = dataframe

    # resample to hourly
    dataframe_hr = resample_to_interval(dataframe, 60)

    # resample to 5m
    # dataframe_5m = resample_to_interval(dataframe, 5)
    dataframe_for_usage = dataframe

    self.ft_ichimoku.informative_df = dataframe_hr
    populated_df = self.ft_ichimoku.populate_indicators(dataframe_for_usage, {})

    df_buy = self.ft_ichimoku.populate_buy_trend(populated_df, {})
    self.df_buy_sell = self.ft_ichimoku.populate_sell_trend(df_buy, {})

    # let's print the whole df for debugging, if needed
    # print(f'Final DF = {self.df_buy_sell.to_string()}')

    # Just for debugging, lets print out all the buys we had
    all_buys = self.df_buy_sell.buy.values
    removed_nan_buys = [x for x in all_buys if str(x) != 'nan']
    print(f'removed_nan_buys = {removed_nan_buys}')

  def next(self):
    try:
      for i, d in enumerate(self.datas):
        first_5_dates = self.df_buy_sell.index[:5]
        last_5_dates = self.df_buy_sell.index[-5:]

        if len(self) > len(self.df_buy_sell):
          continue

        idx = len(self) - 1

        if self.getposition(d).size == 0 and self.df_buy_sell.buy[idx] > 0:
          self.buy(data=d, size=1)

        if self.getposition(d).size > 0 and self.df_buy_sell.sell[idx] > 0:
          self.close(data=d)
    except Exception as e:
      print(f'exception: i={i};exception: {str(e)}')
      raise e


# class BtIchimoku(bt.Strategy):

#     lines = (
#         'tenkan_sen',
#         'kijun_sen',
#         'senkou_span_a',
#         'senkou_span_b',
#         'chikou_span',
#     )
#     params = (
#         ('tenkan', 9),
#         ('kijun', 26),
#         ('senkou', 52),
#         ('senkou_lead', 26),  # forward push
#         ('chikou', 26),
#         ('order_percentage', 0.05),  # backwards push
#     )

#     def __init__(self):

#         self.ichimoku_list = []

#         for d in self.datas:

#             self.ichimoku = bt.indicators.Ichimoku(
#                 d,
#                 tenkan=self.params.tenkan,
#                 kijun=self.params.kijun,
#                 senkou=self.params.senkou,
#                 senkou_lead=self.params.senkou_lead,
#                 chikou=self.params.chikou)

#             self.ichimoku_list.append(self.ichimoku)

#     def next(self):

#         for i, d in enumerate(self.datas):

#             if self.getposition(d).size == 0:
#                 if self.data.close[0] > self.ichimoku_list[
#                         i].lines.senkou_span_a[0] > self.ichimoku_list[
#                             i].lines.senkou_span_b[0]:
#                     amount_to_invest = (self.params.order_percentage *
#                                         self.broker.cash)
#                     self.size = math.floor(amount_to_invest / self.data.close)

#                     self.buy(data=d, size=self.size)

#             if self.getposition(d).size > 0:
#                 if self.data.close[0] <= self.ichimoku_list[
#                         i].lines.senkou_span_a[0] or self.data.close[
#                             0] <= self.ichimoku_list[i].lines.senkou_span_b[0]:

#                     self.close(data=d)


class FreqTrade_Obelisk_Ichimoku_ZEMA_v1(IStrategy):

  # Optimal timeframe for the strategy
  timeframe = '5m'

  # generate signals from the 1h timeframe
  informative_timeframe = '1h'

  # WARNING: ichimoku is a long indicator, if you remove or use a
  # shorter startup_candle_count your backtest results will be unreliable
  startup_candle_count = 399

  # NOTE: this strat only uses candle information, so processing between
  # new candles is a waste of resources as nothing will change
  process_only_new_candles = True

  # ROI table:
  minimal_roi = {"0": 0.078, "40": 0.062, "99": 0.039, "218": 0}

  stoploss = -0.294

  # Buy hyperspace params:
  buy_params = {'low_offset': 0.964, 'zema_len_buy': 51}

  # Sell hyperspace params:
  sell_params = {'high_offset': 1.004, 'zema_len_sell': 72}

  low_offset = DecimalParameter(
      0.80, 1.20, default=1.004, space='buy', optimize=True)
  high_offset = DecimalParameter(
      0.80, 1.20, default=0.964, space='sell', optimize=True)
  zema_len_buy = IntParameter(30, 90, default=72, space='buy', optimize=True)
  zema_len_sell = IntParameter(30, 90, default=51, space='sell', optimize=True)

  dataframe = None
  informative_df = None

  def informative_pairs(self):
    return ['^NSEI']
    # pairs = self.dp.current_whitelist()
    # informative_pairs = [(pair, self.informative_timeframe)
    #                      for pair in pairs]
    # return informative_pairs

  def slow_tf_indicators(
      self, dataframe: DataFrame, metadata: dict) -> DataFrame:

    displacement = 30
    ichimoku = ftt.ichimoku(
        dataframe,
        conversion_line_period=20,
        base_line_periods=60,
        laggin_span=120,
        displacement=displacement)

    dataframe['chikou_span'] = ichimoku['chikou_span']

    # cross indicators
    dataframe['tenkan_sen'] = ichimoku['tenkan_sen']
    dataframe['kijun_sen'] = ichimoku['kijun_sen']

    # cloud, green a > b, red a < b
    dataframe['senkou_a'] = ichimoku['senkou_span_a']
    dataframe['senkou_b'] = ichimoku['senkou_span_b']
    dataframe['leading_senkou_span_a'] = ichimoku['leading_senkou_span_a']
    dataframe['leading_senkou_span_b'] = ichimoku['leading_senkou_span_b']
    dataframe['cloud_green'] = ichimoku['cloud_green'] * 1
    dataframe['cloud_red'] = ichimoku['cloud_red'] * -1

    dataframe.loc[:, 'cloud_top'] = dataframe.loc[:,
                                                  ['senkou_a', 'senkou_b']].max(
                                                      axis=1)
    dataframe.loc[:,
                  'cloud_bottom'] = dataframe.loc[:,
                                                  ['senkou_a', 'senkou_b']].min(
                                                      axis=1)

    # DANGER ZONE START

    # NOTE: Not actually the future, present data that is normally shifted forward for display as the cloud
    dataframe['future_green'] = (
        dataframe['leading_senkou_span_a'] >
        dataframe['leading_senkou_span_b']).astype('int') * 2
    dataframe['future_red'] = (
        dataframe['leading_senkou_span_a'] <
        dataframe['leading_senkou_span_b']).astype('int') * 2

    # The chikou_span is shifted into the past, so we need to be careful not to read the
    # current value.  But if we shift it forward again by displacement it should be safe to use.
    # We're effectively "looking back" at where it normally appears on the chart.
    dataframe['chikou_high'] = (
        (dataframe['chikou_span'] >
         dataframe['cloud_top'])).shift(displacement).fillna(0).astype('int')

    dataframe['chikou_low'] = (
        (dataframe['chikou_span'] < dataframe['cloud_bottom'])
    ).shift(displacement).fillna(0).astype('int')

    # DANGER ZONE END

    dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
    ssl_down, ssl_up = ssl_atr(dataframe, 10)
    dataframe['ssl_down'] = ssl_down
    dataframe['ssl_up'] = ssl_up
    dataframe['ssl_ok'] = ((ssl_up > ssl_down)).astype('int') * 3
    dataframe['ssl_bear'] = ((ssl_up < ssl_down)).astype('int') * 3

    dataframe['ichimoku_ok'] = (
        (dataframe['tenkan_sen'] > dataframe['kijun_sen'])
        & (dataframe['close'] > dataframe['cloud_top'])
        & (dataframe['future_green'] > 0)
        & (dataframe['chikou_high'] > 0)).astype('int') * 4

    dataframe['ichimoku_bear'] = (
        (dataframe['tenkan_sen'] < dataframe['kijun_sen'])
        & (dataframe['close'] < dataframe['cloud_bottom'])
        & (dataframe['future_red'] > 0)
        & (dataframe['chikou_low'] > 0)).astype('int') * 4

    dataframe['ichimoku_valid'] = (
        (
            dataframe['leading_senkou_span_b']
            == dataframe['leading_senkou_span_b'])  # not NaN
    ).astype('int') * 1

    dataframe['trend_pulse'] = (
        (dataframe['ichimoku_ok'] > 0)
        & (dataframe['ssl_ok'] > 0)).astype('int') * 2

    dataframe['bear_trend_pulse'] = (
        (dataframe['ichimoku_bear'] > 0)
        & (dataframe['ssl_bear'] > 0)).astype('int') * 2

    dataframe['trend_over'] = (
        (dataframe['ssl_ok'] == 0)
        | (dataframe['close'] < dataframe['cloud_top'])).astype('int') * 1

    dataframe['bear_trend_over'] = (
        (dataframe['ssl_bear'] == 0)
        | (dataframe['close'] > dataframe['cloud_bottom'])).astype('int') * 1

    dataframe.loc[(dataframe['trend_pulse'] > 0), 'trending'] = 3
    dataframe.loc[(dataframe['trend_over'] > 0), 'trending'] = 0
    dataframe['trending'].fillna(method='ffill', inplace=True)

    dataframe.loc[(dataframe['bear_trend_pulse'] > 0), 'bear_trending'] = 3
    dataframe.loc[(dataframe['bear_trend_over'] > 0), 'bear_trending'] = 0
    dataframe['bear_trending'].fillna(method='ffill', inplace=True)

    return dataframe

  def fast_tf_indicators(
      self, dataframe: DataFrame, metadata: dict) -> DataFrame:
    if 'runmode' in self.config and self.config['runmode'].value == 'hyperopt':
      for len in range(30, 91):
        dataframe[f'zema_{len}'] = ftt.zema(dataframe, period=len)
    else:
      dataframe[f'zema_{self.zema_len_buy.value}'] = ftt.zema(
          dataframe, period=self.zema_len_buy.value)
      dataframe[f'zema_{self.zema_len_sell.value}'] = ftt.zema(
          dataframe, period=self.zema_len_sell.value)
      dataframe[f'zema_buy'] = ftt.zema(
          dataframe, period=self.zema_len_buy.value) * self.low_offset.value
      dataframe[f'zema_sell'] = ftt.zema(
          dataframe, period=self.zema_len_sell.value) * self.high_offset.value

    return dataframe

  def populate_indicators(
      self, dataframe: DataFrame, metadata: dict) -> DataFrame:
    assert (
        timeframe_to_minutes(self.timeframe) == 5), "Run this strategy at 5m."

    if self.timeframe == self.informative_timeframe:
      dataframe = self.slow_tf_indicators(dataframe, metadata)
    else:
      #     assert self.dp, "DataProvider is required for multiple timeframes."
      informative = self.informative_df
      # informative = self.dp.get_pair_dataframe(
      #     pair=metadata['pair'], timeframe=self.informative_timeframe)
      informative = self.slow_tf_indicators(informative.copy(), metadata)

      del dataframe['date']
      dataframe = merge_informative_pair(
          dataframe,
          informative,
          self.timeframe,
          self.informative_timeframe,
          ffill=True)
      # don't overwrite the base dataframe's OHLCV information
      skip_columns = [
          (s + "_" + self.informative_timeframe)
          for s in ['date', 'open', 'high', 'low', 'close', 'volume']
      ]
      dataframe.rename(
          columns=lambda s: s.replace(
              "_{}".format(self.informative_timeframe), "")
          if (not s in skip_columns) else s,
          inplace=True)

    dataframe = self.fast_tf_indicators(dataframe, metadata)

    return dataframe

  def populate_buy_trend(
      self, dataframe: DataFrame, metadata: dict) -> DataFrame:
    zema = f'zema_{self.zema_len_buy.value}'

    dataframe.loc[
        (dataframe['ichimoku_valid'] > 0)
        & (dataframe['bear_trending'] == 0)
        & (dataframe['close'] <
           (dataframe[zema] * self.low_offset.value)), 'buy'] = 1
    return dataframe

  def populate_sell_trend(
      self, dataframe: DataFrame, metadata: dict) -> DataFrame:
    zema = f'zema_{self.zema_len_sell.value}'

    dataframe.loc[(
        (dataframe['close'] > (dataframe[zema] * self.high_offset.value))),
                  'sell'] = 1

    return dataframe

  def confirm_trade_exit(
      self, pair: str, trade: 'Trade', order_type: str, amount: float,
      rate: float, time_in_force: str, sell_reason: str,
      current_time: 'datetime', **kwargs) -> bool:

    if sell_reason in ('roi',):
      dataframe, _ = self.dataframe  #  self.dp.get_analyzed_dataframe(pair, self.timeframe)
      current_candle = dataframe.iloc[-1]
      if current_candle is not None:
        current_candle = current_candle.squeeze()
        # don't sell during ichimoku uptrend
        if current_candle['trending'] > 0:
          return False

    return True

  plot_config = {
      # Main plot indicators (Moving averages, ...)
      'main_plot':
          {
              'senkou_a':
                  {
                      'color': 'green',
                      'fill_to': 'senkou_b',
                      'fill_label': 'Ichimoku Cloud',
                      'fill_color': 'rgba(0,0,0,0.2)',
                  },
              # plot senkou_b, too. Not only the area to it.
              'senkou_b': {
                  'color': 'red',
              },
              'tenkan_sen': {
                  'color': 'blue'
              },
              'kijun_sen': {
                  'color': 'orange'
              },

              # 'chikou_span': { 'color': 'lightgreen' },
              'ssl_up': {
                  'color': 'green'
              },
              # 'ssl_down': { 'color': 'red' },

              # 'ema50': { 'color': 'violet' },
              # 'ema200': { 'color': 'magenta' },
              'zema_buy': {
                  'color': 'blue'
              },
              'zema_sell': {
                  'color': 'orange'
              },
          },
      'subplots':
          {
              "Trend":
                  {
                      'trending': {
                          'color': 'green'
                      },
                      'bear_trending': {
                          'color': 'red'
                      },
                  },
              "Bull":
                  {
                      'trend_pulse': {
                          'color': 'blue'
                      },
                      'trending': {
                          'color': 'orange'
                      },
                      'trend_over': {
                          'color': 'red'
                      },
                  },
              "Bull Signals":
                  {
                      'ichimoku_ok': {
                          'color': 'green'
                      },
                      'ssl_ok': {
                          'color': 'red'
                      },
                  },
              "Bear":
                  {
                      'bear_trend_pulse': {
                          'color': 'blue'
                      },
                      'bear_trending': {
                          'color': 'orange'
                      },
                      'bear_trend_over': {
                          'color': 'red'
                      },
                  },
              "Bear Signals":
                  {
                      'ichimoku_bear': {
                          'color': 'green'
                      },
                      'ssl_bear': {
                          'color': 'red'
                      },
                  },
              "Misc": {
                  'ichimoku_valid': {
                      'color': 'green'
                  },
              },
          }
  }
