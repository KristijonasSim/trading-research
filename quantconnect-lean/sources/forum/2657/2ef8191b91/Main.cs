using QuantConnect.Data.Market;
using QuantConnect.Securities;
using System;
using System.Collections.Generic;
using QuantConnect.Orders;
using QuantConnect.Orders.Slippage;
using QuantConnect.Indicators;
using QuantConnect.Data;
using System.Collections.Concurrent;
using QuantConnect.Securities.Interfaces;

namespace QuantConnect.Algorithm.CSharp
{
	//QC adaption of QT algorithm from https://www.quantopian.com/posts/yavols-yet-another-volatility-strategy-xiv-sniper-using-rsi2
	//credit to Kory Hoang and Cesar Alvarez for original version
	//apologies for messy code, copied some bits from other project when starting out and I don't want
	//to spend a lot of time cleaning it
    public sealed partial class VixRsiAlgorithm : FixedSetHoldingsAlgorithm
    {
        private const string _algoID = "vixrsi";
        private const decimal _securityLeverage = 2; //set per Security, in this case equal to IB intraday limits
        private const Resolution _resolution = Resolution.Minute;
        private const bool _disableRealisticFills = true;

 		//you will notice when you tune this up that the algo doesn't look that great,
 		//on the other hand slippage for TLT might be exaggerated,
 		//you might be able to achieve better results by using limit orders in reality
        private const decimal SLIPPAGE = 0.00m / 100m;

        public override void Initialize()
        {
            SetCash(100000);

            SetStartDate(2011, 1, 1);
            //SetEndDate(2017, 1, 1);
            //SetEndDate(2016, 1, 10);
            //SetStartDate(2005, 11, 1);
            //SetEndDate(2016, 10, 01);

            try
            {
                ActualInitialization();
            }
            catch (Exception e)
            {
                ReportException(e, this);
                throw;
            }
        }

        public static void ReportException(Exception e, QCAlgorithm algo)
        {
            algo.Error(algo.Time + ": " + e.Message + "\n" + e.StackTrace);
            algo.Log(algo.Time + ": " + e.Message + "\n" + e.StackTrace);
        }

        private readonly List<Tradable> _tradables = new List<Tradable>();

        private void ActualInitialization()
        {

            Schedule.On(Schedule.DateRules.EveryDay(), Schedule.TimeRules.At(0, 0, 0), AtMidnight);

            SetBrokerageModel(Brokerages.BrokerageName.InteractiveBrokersBrokerage);

            _tradables.Add(new Tradable(this, "XIV", "TLT"));

            Schedule.On(DateRules.EveryDay(_tradables[0].Symbol), TimeRules.AfterMarketOpen(_tradables[0].Symbol, -1), BeforeOpen);
            Schedule.On(DateRules.EveryDay(_tradables[0].Symbol), TimeRules.BeforeMarketClose(_tradables[0].Symbol, 0.92), RebalanceBeforeClose);

            SetBenchmark(_tradables[0].Symbol);

            if (LiveMode)
            {
                Schedule.On(DateRules.EveryDay(), TimeRules.Every(TimeSpan.FromMinutes(1)), CheckOrderEvents);
            }  
        }

        public override void OnEndOfAlgorithm()
        {
            CheckOrderEvents();

            //_paramSetPollingThread.Cancel();
            //_paramSetPollingThread.Join();
        }

        private void AtMidnight()
        {
            //Xtend.DiscardScheduledEvents();
        }

        private void BeforeOpen()
        {
            foreach (var tradable in _tradables)
            {
                tradable.BeforeOpen();
            }
        }

        public void OnWarmupData(Slice slice)
        {
            //OnData(slice);
        }

        private void RebalanceBeforeClose()
        {
            foreach (var tradable in _tradables)
            {
                tradable.RebalanceBeforeClose();
            }
        }

        public override void OnData(Slice slice)
        {
            CheckOrderEvents();

            foreach (var kv in slice.Bars)
            {
                var tradable = _tradables.Find(x => x.Symbol == kv.Key);
                if (tradable != null)
                {
                    tradable.OnData(kv.Value);
                }
            }
        }

        private readonly ConcurrentQueue<OrderEvent> _orderEvents = new ConcurrentQueue<OrderEvent>();

        public override void OnOrderEvent(OrderEvent ev)
        {
            _orderEvents.Enqueue(ev.Clone()); 
        }

        private void CheckOrderEvents()
        {
            for (;;)
            {
                OrderEvent ev;
                if (!_orderEvents.TryDequeue(out ev))
                    break;

                var tradable = _tradables.Find(x => x.Symbol == ev.Symbol);
                if (tradable != null)
                {
                    tradable.OnOrderEvent(ev);
                }
            }
        }

        private sealed class Tradable
        {
            private readonly VixRsiAlgorithm _algo;
            public readonly Security Security;
            public readonly Security SafeSecurity;

            private readonly TickFillSource _tickFillSource;

            private readonly SimpleMovingAverage _averageSlippage = new SimpleMovingAverage(200);
            private readonly SimpleMovingAverage _averageOrderLatency = new SimpleMovingAverage(200);
            private readonly Maximum _maxOrderLatency = new Maximum(200);

            private readonly RelativeStrengthIndex _rsi7 = new RelativeStrengthIndex(7);
            private readonly RelativeStrengthIndex _rsi2 = new RelativeStrengthIndex(2);

            private decimal _oldRsi7;
            private decimal _oldRsi2;

            private bool _nextDayBuy;
            private bool _nextDaySell;

            private decimal _takeProfitPrice;
            private decimal _takeLossPrice;

            public Symbol Symbol
            {
                get { return Security.Symbol; }
            }

            public Tradable(VixRsiAlgorithm algo, string symbol, string invSymbol)
            {
                _algo = algo;
                Security = algo.AddSecurity(SecurityType.Equity, symbol, _resolution, true, _securityLeverage, false);
                if (invSymbol != null)
                    SafeSecurity = algo.AddSecurity(SecurityType.Equity, invSymbol, _resolution, true, _securityLeverage, false);
                else
                    SafeSecurity = null;
                if (_disableRealisticFills)
                    Security.SlippageModel = new ConstantSlippageModel(SLIPPAGE);
                _tickFillSource = new TickFillSource(Symbol);

                if (!_disableRealisticFills)
                {
                    var fillModel = new ImmediateWhenVolumeFillModel(algo);
                    //fillModel.TickFillSource = _tickFillSource;
                    fillModel.HighlyLiquidAsset = true;
                    fillModel.OrderDelay = TimeSpan.FromSeconds(1);
                    Security.FillModel = fillModel;
                }

                Security.DataFilter = new CustomDataFilter();
            }

            private class CustomDataFilter : ISecurityDataFilter
            {
                public bool Filter(Security vehicle, BaseData data)
                {
                    if (data.DataType == MarketDataType.Tick)
                    {
                        var tick = (Tick)data;
                        if (tick.Suspicious)
                            return false;
                    }

                    return true;
                }
            }

            private bool CanBeInMarket(DateTime now)
            {
                return true;
            }

            public void OnData(TradeBar bar)
            {
                if (Security.HoldStock)
                {
                    if (Security.Price > _takeProfitPrice || Security.Price <_takeLossPrice)
                    {
                        _nextDaySell = false;
                        Exit();
                    }
                }
            }

            public void RebalanceBeforeClose()
            {
                _rsi2.Update(_algo.Time, Security.Price);
                _rsi7.Update(_algo.Time, Security.Price);

                const decimal trigger1 = 25;
                const decimal trigger2 = 75;

                if (_rsi7 > trigger1 && _oldRsi7 < trigger1 && !Security.HoldStock)
                {
                    Enter();
                }
                else if (_rsi2 > trigger2 && _oldRsi2 < trigger2 && !Security.HoldStock)
                {
                    _nextDayBuy = true;
                }
                else if (Security.HoldStock && _rsi2 < trigger2 && _oldRsi2 > trigger2)
                {
                    _nextDaySell = true;
                }

                _oldRsi2 = _rsi2;
                _oldRsi7 = _rsi7;
            }

            private void Enter()
            {
                //auto converted to market on open if outside market hours

                _takeLossPrice = Security.Price * 0.98m;
                _takeProfitPrice = Security.Price * 1.05m;
                _algo.Liquidate(SafeSecurity.Symbol);
                _algo.FixedSetHoldings(Security.Symbol, 1);
            }

            private void Exit()
            {
                //auto converted to market on open if outside market hours

                _algo.Liquidate(Security.Symbol);
                _algo.FixedSetHoldings(SafeSecurity.Symbol, 1);
            }

            public void BeforeOpen()
            {
                if (!_algo.LiveMode)
                    UpdateOrderStats();

                if (_nextDayBuy)
                {
                    _nextDayBuy = false;
                    if (!Security.HoldStock)
                        Enter();
                }

                if (_nextDaySell)
                {
                    _nextDaySell = false;
                    if (Security.HoldStock)
                        Exit();
                }
            }

            private decimal GetExpectedOrderLatency()
            {
                if (_averageOrderLatency.Samples != 0)
                    return _averageOrderLatency;
                return 1;
            }

            private void UpdateOrderStats()
            {
                var negativeSlippage = -_averageSlippage.Current.Value;
                _algo.SetRuntimeStatistic("Slippage", negativeSlippage.ToString("P3"));
                _algo.SetRuntimeStatistic("Latency", _averageOrderLatency.Current.Value.ToString("F2"));
                _algo.SetRuntimeStatistic("LatencyMax", _maxOrderLatency.Current.Value.ToString("F2"));
            }

            private void HandleOrderFilled(OrderEvent ev)
            {
            }

            public void OnOrderEvent(OrderEvent ev)
            {
                switch (ev.Status)
                {
                    case OrderStatus.Invalid:
                        _algo.Debug("Order error: " + ev.Message);
                        _algo.Debug("Order error for " + Symbol.ToString() + ": " + ev.Status);
                        break; //TODO: handle error in some way, maybe retry after a while?
                    case OrderStatus.Filled:
                        HandleOrderFilled(ev);
                        break;
                }
            }
        }
    }
}