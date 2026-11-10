/*
 * QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
 * Lean Algorithmic Trading Engine v2.0. Copyright 2014 QuantConnect Corporation.
 * 
 * Licensed under the Apache License, Version 2.0 (the "License"); 
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
*/

using System;
using QuantConnect.Data.Market;
using QuantConnect.Securities;
using QuantConnect.Orders.Fills;
using QuantConnect.Orders;
using QuantConnect.Data;
using System.Linq;

namespace QuantConnect.Algorithm.CSharp
{
    /// <summary>
    /// Represents the default fill model used to simulate order fills
    /// but with the following modification for limit orders:
    /// Trade volumes do not allow a fill unless they are >= VolumeThreshold.
    /// Limitation: Quotes are not used.
    /// </summary>
    public class ImmediateWhenVolumeFillModel : ImmediateFillModel
    {
        private readonly QCAlgorithm _algo;

        public ImmediateWhenVolumeFillModel(QCAlgorithm algo)
        {
            _algo = algo;

            VolumeThreshold = 1;
            OrderDelay = TimeSpan.FromSeconds(0);
        }

        /// <summary>
        /// Threshold below which orders do not fill. Defaults to 1.
        /// </summary>
        public long VolumeThreshold { get; set; }

        /// <summary>
        /// Uniform delay to orders in backtest simulation.
        /// Note, has a different meaning in FillOnNextAvailableTick.
        /// </summary>
        public TimeSpan OrderDelay { get; set; }

        /// <summary>
        /// Optional tick fill source.
        /// </summary>
        public TickFillSource TickFillSource { get; set; }

        /// <summary>
        /// For best effort HFT simulation with second precision tick data.
        /// If this is used, OrderDelay instead works as a barrier beyond which
        /// last price is used instead.
        /// </summary>
        public bool FillOnNextAvailableTick { get; set; }

        /// <summary>
        /// Treat asset as if a fill will always be possible at same price as last tick.
        /// </summary>
        public bool HighlyLiquidAsset { get; set; }

        /// <summary>
        /// Default limit order fill model in the base security class.
        /// </summary>
        /// <param name="asset">Security asset we're filling</param>
        /// <param name="order">Order packet to model</param>
        /// <returns>Order fill information detailing the average price and quantity filled.</returns>
        /// <seealso cref="StopMarketFill(Security, StopMarketOrder)"/>
        /// <seealso cref="MarketFill(Security, MarketOrder)"/>
        public override OrderEvent LimitFill(Security asset, LimitOrder order)
        {
            if (FillOnNextAvailableTick)
                throw new NotSupportedException("FillOnNextAvailableTick");

            //Initialise;
            var utcTime = asset.LocalTime.ConvertToUtc(asset.Exchange.TimeZone);
            var fill = new OrderEvent(order, utcTime, 0);
            fill.Status = order.Status; //necessary, engine will process fill if quantity filled != 0 or status differs

            //If its cancelled don't need anymore checks:
            if (order.Status == OrderStatus.Canceled) return fill;

            //Get the range of prices in the last bar:
            var prices = GetPrices(asset, order);
            if (prices == null) return fill;

            if (prices.Volume < VolumeThreshold) return fill;

            if (prices.Time < order.Time + OrderDelay) return fill;

            //-> Valid Live/Model Order: 
            switch (order.Direction)
            {
                case OrderDirection.Buy:
                    //Buy limit seeks lowest price
                    if (prices.Low < order.LimitPrice)
                    {
                        //Set order fill:
                        fill.Status = OrderStatus.Filled;

                        //TODO: include option to fill "current bar" order was created in with below price, which was default QC code (unfortunately, leads to highly unrealistic fills with waiting limit orders)
                        //fill.FillPrice = Math.Min(prices.High, order.LimitPrice);
                        fill.FillPrice = order.LimitPrice;
                    }
                    break;
                case OrderDirection.Sell:
                    //Sell limit seeks highest price possible
                    if (prices.High > order.LimitPrice)
                    {
                        fill.Status = OrderStatus.Filled;

                        //TODO: include option to fill "current bar" order was created in with below price, which was default QC code (unfortunately, leads to highly unrealistic fills with waiting limit orders)
                        //fill.FillPrice = Math.Max(prices.Low, order.LimitPrice);
                        fill.FillPrice = order.LimitPrice;
                    }
                    break;
            }

            // assume the order completely filled
            if (fill.Status == OrderStatus.Filled)
            {
                fill.FillQuantity = order.Quantity;
                fill.OrderFee = asset.FeeModel.GetOrderFee(asset, order);
            }

            fill.UtcTime = prices.Time;

            return fill;
        }

        /// <summary>
        /// Default market fill model for the base security class. Fills at the last traded price.
        /// </summary>
        /// <param name="asset">Security asset we're filling</param>
        /// <param name="order">Order packet to model</param>
        /// <returns>Order fill information detailing the average price and quantity filled.</returns>
        /// <seealso cref="SecurityTransactionModel.StopMarketFill"/>
        /// <seealso cref="SecurityTransactionModel.LimitFill"/>
        public override OrderEvent MarketFill(Security asset, MarketOrder order)
        {
            //Default order event to return.
            var utcTime = asset.LocalTime.ConvertToUtc(asset.Exchange.TimeZone);
            var fill = new OrderEvent(order, utcTime, 0);
            fill.Status = order.Status; //necessary, engine will process fill if quantity filled != 0 or status differs

            if (order.Status == OrderStatus.Canceled) return fill;

            // make sure the exchange is open before filling
            if (!IsExchangeOpen(asset)) return fill;

            var prices = GetPrices(asset, order);
            if (prices == null) return fill;

            if (!HighlyLiquidAsset && prices.Volume < VolumeThreshold) return fill;

            var maxTime = prices.Time;
            if (HighlyLiquidAsset && TickFillSource == null && _algo.UtcTime > maxTime)
                maxTime = _algo.UtcTime;

            var orderTime = order.Time;
            if (!FillOnNextAvailableTick)
                orderTime += OrderDelay;

            if (maxTime <= orderTime) return fill;

            //Order [fill]price for a market order model is the current security price
            fill.FillPrice = prices.Current;
            fill.Status = OrderStatus.Filled;

            //Calculate the model slippage: e.g. 0.01c
            var slip = asset.SlippageModel.GetSlippageApproximation(asset, order);

            //Apply slippage
            switch (order.Direction)
            {
                case OrderDirection.Buy:
                    fill.FillPrice += slip;
                    break;
                case OrderDirection.Sell:
                    fill.FillPrice -= slip;
                    break;
            }

            // assume the order completely filled
            if (fill.Status == OrderStatus.Filled)
            {
                fill.FillQuantity = order.Quantity;
                fill.OrderFee = asset.FeeModel.GetOrderFee(asset, order);
            }

            fill.UtcTime = prices.Time;

            return fill;
        }

        /// <summary>
        /// Get the minimum and maximum price for this security in the last bar:
        /// </summary>
        /// <param name="asset">Security asset we're checking</param>
        /// <param name="direction">The order direction, decides whether to pick bid or ask</param>
        private Prices GetPrices(Security asset, Order order)
        {
            var direction = order.Direction;
            var low = asset.Low;
            var high = asset.High;
            var open = asset.Open;
            var close = asset.Close;
            var current = asset.Price;
            var volume = 0;
            var time = asset.LocalTime;

            if (direction == OrderDirection.Hold)
            {
                return new Prices(current, open, high, low, close, volume, time, asset.Exchange.TimeZone);
            }

            if (TickFillSource != null)
            {
                var closestTick = asset.Cache.GetData<Tick>();
                var orderTime = order.Time;
                if (!FillOnNextAvailableTick)
                    orderTime += OrderDelay;

                foreach (var t in TickFillSource.Ticks)
                {
                    if (t.TickType != TickType.Trade)
                        continue;

                    if (t.Quantity < VolumeThreshold)
                        continue;

                    var tickTime = t.Time.ConvertToUtc(asset.Exchange.TimeZone);
                    if (tickTime > orderTime)
                    {
                        var fillTime = orderTime;
                        if (FillOnNextAvailableTick)
                            fillTime = tickTime;

                        if (HighlyLiquidAsset && !FillOnNextAvailableTick)
                        {
                            var closestTickTime = closestTick.Time.ConvertToUtc(asset.Exchange.TimeZone);

                            //allow using last price despite being from past
                            if (Math.Abs((tickTime - orderTime).TotalSeconds) < Math.Abs((closestTickTime - orderTime).TotalSeconds))
                            {
                                closestTick = t;
                                //_algo.Debug("before order: " + (closestTickTime - orderTime).TotalSeconds);
                            }
                            else
                            {
                                //_algo.Debug("before order: " + (closestTickTime - orderTime).TotalSeconds);
                            } 

                            if (closestTickTime > fillTime)
                                fillTime = closestTickTime;
                        }
                        else
                        {
                            closestTick = t;
                        }

                        return new Prices(closestTick.Price, open, high, low, close, closestTick.Quantity, fillTime);
                    }
                    else
                    {
                        closestTick = t;
                    }
                }

                return null;
            }

            var tick = asset.Cache.GetData<Tick>();
            if (tick != null)
            {
                return new Prices(tick.Price, open, high, low, close, tick.Quantity, tick.Time, asset.Exchange.TimeZone);
            }

            var tradeBar = asset.Cache.GetData<TradeBar>();
            if (tradeBar != null)
            {
                return new Prices(tradeBar, asset.Exchange.TimeZone);
            }

            var lastData = asset.GetLastData();
            var lastBar = lastData as TradeBar;
            if (lastBar != null)
            {
                return new Prices(lastBar, asset.Exchange.TimeZone);
            }

            return new Prices(current, open, high, low, close, volume, time, asset.Exchange.TimeZone);
        }

        /// <summary>
        /// Determines if the exchange is open using the current time of the asset
        /// </summary>
        private static bool IsExchangeOpen(Security asset)
        {
            if (!asset.Exchange.DateTimeIsOpen(asset.LocalTime))
            {
                // if we're not open at the current time exactly, check the bar size, this handle large sized bars (hours/days)
                var currentBar = asset.GetLastData();
                if (asset.LocalTime.Date != currentBar.EndTime.Date || !asset.Exchange.IsOpenDuringBar(currentBar.Time, currentBar.EndTime, false))
                {
                    return false;
                }
            }
            return true;
        }

        private class Prices
        {
            public readonly decimal Current;
            public readonly decimal Open;
            public readonly decimal High;
            public readonly decimal Low;
            public readonly decimal Close;
            public readonly decimal Volume;
            public readonly DateTime Time;

            public Prices(TradeBar bar, NodaTime.DateTimeZone timeZone)
                : this(bar.Close, bar.Open, bar.High, bar.Low, bar.Close, bar.Volume, bar.Time, timeZone)
            {
            }

            public Prices(decimal current, decimal open, decimal high, decimal low, decimal close, decimal volume, DateTime time, NodaTime.DateTimeZone timeZone)
            {
                Current = current;
                Open = open == 0 ? current : open;
                High = high == 0 ? current : high;
                Low = low == 0 ? current : low;
                Close = close == 0 ? current : close;
                Volume = volume;
                Time = time.ConvertToUtc(timeZone);
            }

            public Prices(decimal current, decimal open, decimal high, decimal low, decimal close, decimal volume, DateTime utcTime)
            {
                Current = current;
                Open = open == 0 ? current : open;
                High = high == 0 ? current : high;
                Low = low == 0 ? current : low;
                Close = close == 0 ? current : close;
                Volume = volume;
                Time = utcTime;
            }
        }
    }
}