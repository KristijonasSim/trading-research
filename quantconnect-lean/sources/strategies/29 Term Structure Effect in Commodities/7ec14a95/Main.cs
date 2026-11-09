namespace QuantConnect 
{   
    /*
    *   Term Structure Effect in Commodities
    *   http://quantpedia.com/Screener/Details/22
    */
    public class CommodityTermStructure : QCAlgorithm
    {
       	private FuturesChains _chains = new FuturesChains();
       	
        public override void Initialize()
        {
            SetStartDate(2016, 1, 1);
            SetEndDate(2018, 7, 1);
            SetCash(1000000);
			
			var tickers = new string[] {
				Futures.Softs.Cocoa,
				Futures.Softs.Coffee,
				Futures.Grains.Corn,
				Futures.Softs.Cotton2,
				Futures.Grains.Oats,
				Futures.Softs.OrangeJuice,
				Futures.Grains.SoybeanMeal,
				Futures.Grains.SoybeanOil,
				Futures.Grains.Soybeans,
				Futures.Softs.Sugar11,
				Futures.Grains.Wheat,
				Futures.Meats.FeederCattle,
				Futures.Meats.LeanHogs,
				Futures.Meats.LiveCattle,
				Futures.Energies.CrudeOilWTI,
				Futures.Energies.HeatingOil,
				Futures.Energies.NaturalGas,
				Futures.Energies.Gasoline,
				Futures.Metals.Gold,
				Futures.Metals.Palladium,
				Futures.Metals.Platinum,
				Futures.Metals.Silver
			};
			
			foreach (var ticker in tickers)
			{
				var future = AddFuture(ticker);
				future.SetFilter(TimeSpan.Zero, TimeSpan.FromDays(90));
			}
			AddEquity("SPY", Resolution.Minute);
			Schedule.On(DateRules.MonthStart("SPY"), TimeRules.AfterMarketOpen("SPY", 30), Rebalance);
        }

        // Saves the Futures Chains 
        public override void OnData(Slice slice) {
        	foreach (var chain in slice.FutureChains)
        	{
        		if (chain.Value.Contracts.Count < 2) continue;
        		
        		if (!_chains.ContainsKey(chain.Key))
        		{
        			_chains.Add(chain.Key, chain.Value);
        		}
        		
        		_chains[chain.Key] = chain.Value;
        	}
        }

        // Trades are only defined on end of day
		public void Rebalance()
		{
            Liquidate();
            
            var quintile = (int)Math.Floor(_chains.Count / 5.0);
            var rollReturns = new Dictionary<Symbol, double>();
            
            foreach (var chain in _chains) {
				var contracts = chain.Value.OrderBy(x => x.Expiry);

				// R = (log(Pn) - log(Pd)) * 365 / (Td - Tn)
                // R - Roll returns
                // Pn - Nearest contract price
                // Pd - Distant contract price
                // Tn - Nearest contract expire date
                // Pd - Distant contract expire date

                var nearestContract = contracts.FirstOrDefault();
                var distantContract = contracts.ElementAtOrDefault(1);
                var priceNearest = nearestContract.LastPrice > 0 ? nearestContract.LastPrice : (nearestContract.AskPrice + nearestContract.BidPrice) / 2m;
                var priceDistant = distantContract.LastPrice > 0 ? distantContract.LastPrice : (distantContract.AskPrice + distantContract.BidPrice) / 2m;
                var logPriceNearest = Math.Log((double)priceNearest);
                var logPriceDistant = Math.Log((double)priceDistant);
                
                if(distantContract.Expiry == nearestContract.Expiry) {
                	Log("ERROR: Nearest and distant contracts with same expire!" + nearestContract);
                	continue;
                }
                
                var expireRange = 365 / (distantContract.Expiry - nearestContract.Expiry).TotalDays;
                
                rollReturns.Add(chain.Key, (logPriceNearest - logPriceDistant) * expireRange);
            }
            
            // Order positive roll returns
            var backwardation = rollReturns
            	.OrderByDescending(x => x.Value)
                .Where(x => x.Value > 0)
                .Take(quintile)
                .ToDictionary(x => x.Key, y => y.Value);
            
            var contango = rollReturns
            	.OrderBy(x => x.Value)
                .Where(x => x.Value < 0)
                .Take(quintile)
                .ToDictionary(x => x.Key, y => y.Value);
            
            // 
            var count = Math.Min(backwardation.Count(), contango.Count());
            if(count != quintile) {
                backwardation = backwardation.Take(count).ToDictionary(x => x.Key, y => y.Value);
                contango = contango.Take(count).ToDictionary(x => x.Key, y => y.Value);
            }
            
            //Log("backwardation: " + string.Join(", ", backwardation));
            //Log("     contango: " + string.Join(", ", contango));
			
			// We cannot long-short if count is zero
			if (count == 0) {
				_chains.Clear();
				return;
			}
			
            var weight = 0.5m / count;
            
            // Sell top contango
            foreach (var symbol in contango.Keys) {
            	var contractSymbol = _chains[symbol].OrderBy(x => x.Expiry).ElementAtOrDefault(1).Symbol;
            	SetHoldings(contractSymbol, -weight);
            }            
            // Buy top backwardation 
            foreach (var symbol in backwardation.Keys) {
            	var contractSymbol = _chains[symbol].OrderBy(x => x.Expiry).ElementAtOrDefault(1).Symbol;
            	SetHoldings(contractSymbol, weight);
            }
            

            
            _chains.Clear();
		}

    }
}