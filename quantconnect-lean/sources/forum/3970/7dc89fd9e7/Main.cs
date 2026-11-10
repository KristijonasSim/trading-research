//Copyright HardingSoftware.com, 2018.
//Granted to the public domain.
//Use entirely at your own risk.
namespace QuantConnect 
{   
    public class EquityQueue : QCAlgorithm
    {
    	string tickersString ="SPY,EEM,IWM,EFA,XLF,XLE,HYG,EWZ,FXI,TLT,XOP,DIA,XLK,XLI,TQQQ,IVV,XLV,GLD,GDX,XLU,XLP,IYR,IEMG,SMH,LQD,VWO,XLY,VOO,JNK,EWJ,EMB,IEF,KRE,XBI,IEFA,VNQ,XLB,VEA,GDXJ,MDY";
    	
    	int maPeriod=2; //The length of the indicator.
		decimal leverage=0.99m;
		
		Resolution resolution=Resolution.Daily;
		List<StockData> stockDatas = new List<StockData>();
		string stockHeld="";
		
        public override void Initialize() 
        {
            SetStartDate(2008, 6, 1);
            SetEndDate(2018, 6, 1);
            SetCash(50000);
            Transactions.MarketOrderFillTimeout = TimeSpan.FromSeconds(30);
			string[] tickers = tickersString.Split(new string[1] { "," }, StringSplitOptions.RemoveEmptyEntries);
			foreach (string ticker in tickers)
			{
				Symbol symbol = QuantConnect.Symbol.Create(ticker, SecurityType.Equity, Market.USA);
				AddEquity(symbol, resolution);
				StockData stockData=new StockData();
				stockData.Ticker=ticker;
				stockData.MovingAverage = new ExponentialMovingAverage(maPeriod);
				stockDatas.Add(stockData);
				var history = History(ticker, maPeriod+1, resolution);
	            foreach (var tradeBar in history)
	            {
	            	stockData.history.Enqueue(tradeBar.Close);
	           		if (stockData.history.Count>1)
		        	{
		        		decimal firstHistory=stockData.history.Dequeue();
		        		decimal change=(stockData.history.Last()-firstHistory)/firstHistory;
						stockData.MovingAverage.Update(Time,change);
		        	}
	            }
			}
        }

        public override void OnData(Slice data) 
        {
        	foreach (StockData stockData in stockDatas)
        	{
        		if (data.Bars.ContainsKey(stockData.Ticker)==false)
        		{
        			continue;
        		}
	        	stockData.history.Enqueue(data.Bars[stockData.Ticker].Close);
	        	if (stockData.history.Count>1)
	        	{
	        		decimal firstHistory=stockData.history.Dequeue();
	        		decimal change=(stockData.history.Last()-firstHistory)/firstHistory;
					stockData.MovingAverage.Update(Time,change);
	        	}
				stockData.Fitness=stockData.MovingAverage;
        	}

    	    var sortedStockDatasEnumerable = from x in stockDatas
    	    	//where x.Fitness > 0
    			orderby x.Fitness
    			select x;
        	
        	List<StockData> sortedStockDatas=sortedStockDatasEnumerable.ToList();
        	if (sortedStockDatas.Count>0)		
        	{
        		StockData selectedStockData=sortedStockDatas.First();
				if (selectedStockData.Ticker != stockHeld)
        		{
        			Liquidate();
        			SetHoldings(selectedStockData.Ticker, leverage);
					stockHeld=selectedStockData.Ticker;
        		}
        	}
    	    else if (stockDatas.Any(x=>Portfolio[x.Ticker].Quantity>0))
    		{
    			Liquidate();
    		}
        }
        
        class StockData
        {
        	public string Ticker;
			public Queue<decimal> history=new Queue<decimal>();
			public ExponentialMovingAverage MovingAverage;
			public decimal Fitness;
        }
    }
}