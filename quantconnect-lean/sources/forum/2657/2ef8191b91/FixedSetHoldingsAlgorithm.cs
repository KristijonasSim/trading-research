using QuantConnect.Algorithm;
using QuantConnect.Orders;
using QuantConnect.Securities;
using System;

namespace QuantConnect
{
    public abstract class FixedSetHoldingsAlgorithm : QCAlgorithm
    {
        /// <summary>
        /// Alias for SetHoldings to avoid the M-decimal errors.
        /// </summary>
        /// <param name="symbol">string symbol we wish to hold</param>
        /// <param name="percentage">double percentage of holdings desired</param>
        /// <param name="liquidateExistingHoldings">liquidate existing holdings if neccessary to hold this stock</param>
        /// <seealso cref="MarketOrder"/>
        public void FixedSetHoldings(Symbol symbol, double percentage, bool liquidateExistingHoldings = false)
        {
            FixedSetHoldings(symbol, (decimal)percentage, liquidateExistingHoldings);
        }

        /// <summary>
        /// Alias for SetHoldings to avoid the M-decimal errors.
        /// </summary>
        /// <param name="symbol">string symbol we wish to hold</param>
        /// <param name="percentage">float percentage of holdings desired</param>
        /// <param name="liquidateExistingHoldings">bool liquidate existing holdings if neccessary to hold this stock</param>
        /// <param name="tag">Tag the order with a short string.</param>
        /// <seealso cref="MarketOrder"/>
        public void FixedSetHoldings(Symbol symbol, float percentage, bool liquidateExistingHoldings = false, string tag = "")
        {
            FixedSetHoldings(symbol, (decimal)percentage, liquidateExistingHoldings, tag);
        }

        /// <summary>
        /// Alias for SetHoldings to avoid the M-decimal errors.
        /// </summary>
        /// <param name="symbol">string symbol we wish to hold</param>
        /// <param name="percentage">float percentage of holdings desired</param>
        /// <param name="liquidateExistingHoldings">bool liquidate existing holdings if neccessary to hold this stock</param>
        /// <param name="tag">Tag the order with a short string.</param>
        /// <seealso cref="MarketOrder"/>
        public void FixedSetHoldings(Symbol symbol, int percentage, bool liquidateExistingHoldings = false, string tag = "")
        {
            FixedSetHoldings(symbol, (decimal)percentage, liquidateExistingHoldings, tag);
        }

        /// <summary>
        /// Automatically place an order which will set the holdings to between 100% or -100% of *PORTFOLIO VALUE*.
        /// E.g. SetHoldings("AAPL", 0.1); SetHoldings("IBM", -0.2); -> Sets portfolio as long 10% APPL and short 20% IBM
        /// E.g. SetHoldings("AAPL", 2); -> Sets apple to 2x leveraged with all our cash.
        /// </summary>
        /// <param name="symbol">Symbol indexer</param>
        /// <param name="percentage">decimal fraction of portfolio to set stock</param>
        /// <param name="liquidateExistingHoldings">bool flag to clean all existing holdings before setting new faction.</param>
        /// <param name="tag">Tag the order with a short string.</param>
        /// <seealso cref="MarketOrder"/>
        public void FixedSetHoldings(Symbol symbol, decimal percentage, bool liquidateExistingHoldings = false, string tag = "")
        {
            //Initialize Requirements:
            Security security;
            if (!Securities.TryGetValue(symbol, out security))
            {
                Error(symbol.ToString() + " not found in portfolio. Request this data when initializing the algorithm.");
                return;
            }

            //If they triggered a liquidate
            if (liquidateExistingHoldings)
            {
                foreach (var kvp in Portfolio)
                {
                    var holdingSymbol = kvp.Key;
                    var holdings = kvp.Value;
                    if (holdingSymbol != symbol && holdings.AbsoluteQuantity > 0)
                    {
                        //Go through all existing holdings [synchronously], market order the inverse quantity:
                        Order(holdingSymbol, -holdings.Quantity, false, tag);
                    }
                }
            }

            //Only place trade if we've got > 1 share to order.
            var quantity = FixedCalculateOrderQuantity(symbol, percentage);
            if (Math.Abs(quantity) > 0)
            {
                MarketOrder(symbol, quantity, false, tag);
            }
        }

        private bool TryOrderQuantity(int orderQuantity, Security security, decimal marginRemaining, decimal targetOrderValue)
        {
            //note that margin requirements and order value + fees are assumed to be monotonic w.r.t. orderQuantity,
            //otherwise binary search would not work and an exhaustive search would be necessary

            var order = new MarketOrder(security.Symbol, orderQuantity, UtcTime);
            var orderValue = order.GetValue(security);
            var orderFees = security.FeeModel.GetOrderFee(security, order);

            // calculate the margin required for the order
            var marginRequired = security.MarginModel.GetInitialMarginRequiredForOrder(security, order);

            return marginRequired <= marginRemaining && orderValue + orderFees <= targetOrderValue;
        }

        /// <summary>
        /// Calculate the order quantity to achieve target-percent holdings.
        /// </summary>
        /// <param name="symbol">Security object we're asking for</param>
        /// <param name="target">Target percentag holdings, this is an unlevered value, so 
        /// if you have 2x leverage and request 100% holdings, it will utilize half of the 
        /// available margin</param>
        /// <returns>Order quantity to achieve this percentage</returns>
        public int FixedCalculateOrderQuantity(Symbol symbol, decimal target)
        {
            var security = Securities[symbol];
            return FixedCalculateOrderQuantity(symbol, target, (int)security.Holdings.Quantity);
        }

        public int FixedCalculateOrderQuantity(Symbol symbol, decimal target, int initialQuantity)
        {
            var security = Securities[symbol];
            var price = security.Price;
            if (price == 0)
                price = (security.BidPrice + security.AskPrice) / 2;

            // if targeting zero, simply return the negative of the quantity
            if (target == 0) return (int)-initialQuantity;

            // can't order it if we don't have data
            if (price == 0) return 0;

            // this is the value in dollars that we want our holdings to have
            var targetPortfolioValue = target * Portfolio.TotalPortfolioValue;
            var quantity = initialQuantity;
            var currentHoldingsValue = price * quantity;

            // remove directionality, we'll work in the land of absolutes
            var targetOrderValue = Math.Abs(targetPortfolioValue - currentHoldingsValue);
            var direction = targetPortfolioValue > currentHoldingsValue ? OrderDirection.Buy : OrderDirection.Sell;

            // determine the unit price in terms of the account currency
            var unitPrice = new MarketOrder(symbol, 1, UtcTime).GetValue(security);

            // calculate the total margin available
            var marginRemaining = Portfolio.GetMarginRemaining(symbol, direction);
            if (marginRemaining <= 0) return 0;

            // compute the initial order quantity
            int orderQuantity;
            int maxOrderQuantity = (int)(targetOrderValue / unitPrice); //upper bound
            int minOrderQuantity = 1; //lower bound

            if (TryOrderQuantity(maxOrderQuantity, security, marginRemaining, targetOrderValue))
            {
                orderQuantity = maxOrderQuantity;
            }
            else if (!TryOrderQuantity(minOrderQuantity, security, marginRemaining, targetOrderValue))
            {
                orderQuantity = 0;
            }
            else
            {
                //binary search
                for (;;)
                {
                    orderQuantity = (maxOrderQuantity + minOrderQuantity) / 2;
                    if (orderQuantity == minOrderQuantity)
                    {
                        orderQuantity = minOrderQuantity;
                        break;
                    }

                    if (TryOrderQuantity(orderQuantity, security, marginRemaining, targetOrderValue))
                    {
                        minOrderQuantity = orderQuantity;
                    }
                    else
                    {
                        maxOrderQuantity = orderQuantity;
                    }
                }
            }

            //Rounding off Order Quantity to the nearest multiple of Lot Size
            if (orderQuantity % Convert.ToInt32(security.SymbolProperties.LotSize) != 0)
            {
                orderQuantity = orderQuantity - (orderQuantity % Convert.ToInt32(security.SymbolProperties.LotSize));
            }

            // add directionality back in
            return (direction == OrderDirection.Sell ? -1 : 1) * orderQuantity;
        }
    }
}