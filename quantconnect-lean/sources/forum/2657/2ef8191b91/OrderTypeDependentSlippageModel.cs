using QuantConnect.Orders.Slippage;
using System;
using QuantConnect.Orders;
using QuantConnect.Securities;

namespace QuantConnect.Algorithm.CSharp
{
    class OrderTypeDependentSlippageModel : ISlippageModel
    {
        public ISlippageModel LimitOrderSlippage { get; set; }
        public ISlippageModel MarketOrderSlippage { get; set; }
        public ISlippageModel MarketOnCloseOrderSlippage { get; set; }
        public ISlippageModel MarketOnOpenOrderSlippage { get; set; }
        public ISlippageModel StopLimitOrderSlippage { get; set; }
        public ISlippageModel StopMarketOrderSlippage { get; set; }

        public OrderTypeDependentSlippageModel(ISlippageModel defaultModel)
        {
            LimitOrderSlippage = defaultModel;
            MarketOrderSlippage = defaultModel;
            MarketOnCloseOrderSlippage = defaultModel;
            MarketOnOpenOrderSlippage = defaultModel;
            StopLimitOrderSlippage = defaultModel;
            StopMarketOrderSlippage = defaultModel;
        }

        public void SetMarketSlippageModel(ISlippageModel model)
        {
            MarketOrderSlippage = model;
            MarketOnCloseOrderSlippage = model;
            MarketOnOpenOrderSlippage = model;
            StopMarketOrderSlippage = model;
        }

        public void SetLimitSlippageModel(ISlippageModel model)
        {
            LimitOrderSlippage = model;
            StopLimitOrderSlippage = model;
        }

        public decimal GetSlippageApproximation(Security asset, Order order)
        {
            switch (order.Type)
            {
                case OrderType.Limit:
                    return LimitOrderSlippage.GetSlippageApproximation(asset, order);
                case OrderType.Market:
                    return MarketOrderSlippage.GetSlippageApproximation(asset, order);
                case OrderType.MarketOnClose:
                    return MarketOnCloseOrderSlippage.GetSlippageApproximation(asset, order);
                case OrderType.MarketOnOpen:
                    return MarketOnOpenOrderSlippage.GetSlippageApproximation(asset, order);
                case OrderType.StopLimit:
                    return StopLimitOrderSlippage.GetSlippageApproximation(asset, order);
                case OrderType.StopMarket:
                    return StopMarketOrderSlippage.GetSlippageApproximation(asset, order);
                default:
                    throw new NotImplementedException("Slippage specialization not implemented for order type " + order.Type.ToString());
            }
        }
    }
}