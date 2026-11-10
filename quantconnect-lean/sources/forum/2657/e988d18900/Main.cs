using System.Drawing;
using System.Threading;
using System.Threading.Tasks;

namespace QuantConnect 
{
    public partial class Spread : QCAlgorithm 
    {
    	[Parameter]
    	public decimal iStopPercents = 0.01m;
    	
    	[Parameter]
    	public decimal iMinSpread = 1m;
    	
		[Parameter]
    	public int iPeriodSlow = 50;

		[Parameter]
    	public int iPeriodFast = 1;

		[Parameter]
		public string iSymbol1 = "XIV";

		[Parameter]
		public string iSymbol2 = "VXX";

		ExponentialMovingAverage iFma1 = null;
		ExponentialMovingAverage iSma1 = null;
		ExponentialMovingAverage iFma2 = null;
		ExponentialMovingAverage iSma2 = null;

		CompositeIndicator<IndicatorDataPoint> iOsc1 = null;
		CompositeIndicator<IndicatorDataPoint> iOsc2 = null;
		CompositeIndicator<IndicatorDataPoint> iSpread = null;

		StandardDeviation iDev1 = null;
		StandardDeviation iDev2 = null;
		StandardDeviation iDev = null;

		decimal iBalance = 10000m;
		string iChartName = "Deals";
		int iDirection = 0;
		int iOrderId = 0;

		public class iDeal
		{
			public int SL;
			public int TP;	
			public int Market;	
		};

        Dictionary<int, iDeal> iDeals = new Dictionary<int, iDeal>();

        public override void Initialize()
        {
        	var resolution = Resolution.Hour;

        	SetCash(iBalance);
        	SetWarmUp(iPeriodSlow);
            //SetStartDate(2008, 1, 1);
            //SetEndDate(2009, 12, 1);
            SetStartDate(2017, 1, 1);
            SetEndDate(DateTime.Now.Date); 
            SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage);
            AddSecurity(SecurityType.Equity, iSymbol1, resolution, true, 4m, false);
            AddSecurity(SecurityType.Equity, iSymbol2, resolution, true, 4m, false);

			iFma1 = EMA(iSymbol1, iPeriodFast, resolution);
			iSma1 = EMA(iSymbol1, iPeriodSlow, resolution);
			iFma2 = EMA(iSymbol2, iPeriodFast, resolution);
			iSma2 = EMA(iSymbol2, iPeriodSlow, resolution);

			iOsc1 = iSma1.Minus(iFma1);
			iOsc2 = iSma2.Minus(iFma2);
			iSpread = iOsc1.Minus(iOsc2);

			var deviation = new StandardDeviation(iPeriodSlow);
			
			iDev = deviation.Of(iOsc2.Minus(iOsc1));
			iDev1 = STD(iSymbol1, iPeriodSlow);
			iDev2 = STD(iSymbol2, iPeriodSlow);

            var chart = new Chart(iChartName);
			var seriesStock1 = new Series("Stock #1", SeriesType.Line, 0) { Color = Color.Gray };
			var seriesBuy1 = new Series("Buy #1", SeriesType.Scatter, 0) { Color = Color.Blue, ScatterMarkerSymbol = ScatterMarkerSymbol.Triangle };
			var seriesSell1 = new Series("Sell #1", SeriesType.Scatter, 0) { Color = Color.Red, ScatterMarkerSymbol = ScatterMarkerSymbol.TriangleDown };
			var seriesStock2 = new Series("Stock #2", SeriesType.Line, 1) { Color = Color.Gray };
			var seriesBuy2 = new Series("Buy #2", SeriesType.Scatter, 1) { Color = Color.Blue, ScatterMarkerSymbol = ScatterMarkerSymbol.Triangle };
			var seriesSell2 = new Series("Sell #2", SeriesType.Scatter, 1) { Color = Color.Red, ScatterMarkerSymbol = ScatterMarkerSymbol.TriangleDown };
			var seriesBalance = new Series("Balance", SeriesType.Line, 2) { Color = Color.Yellow };
			var seriesOsc1 = new Series("Osc #1", SeriesType.Line, 3) { Color = Color.Blue };
			var seriesOsc2 = new Series("Osc #2", SeriesType.Line, 3) { Color = Color.Red };
			var seriesSpread = new Series("Spread", SeriesType.Line, 4) { Color = Color.Lime };
			var seriesDevUp = new Series("Dev Up x 2", SeriesType.Line, 4) { Color = Color.Blue };
			var seriesDevDown = new Series("Dev Dn x 2", SeriesType.Line, 4) { Color = Color.Red };

			chart.AddSeries(seriesStock1);
			chart.AddSeries(seriesBuy1);
			chart.AddSeries(seriesSell1);
			chart.AddSeries(seriesStock2);
			chart.AddSeries(seriesBuy2);
			chart.AddSeries(seriesSell2);
			chart.AddSeries(seriesBalance);
			chart.AddSeries(seriesOsc1);
			chart.AddSeries(seriesOsc2);
			chart.AddSeries(seriesSpread);
			chart.AddSeries(seriesDevUp);
			chart.AddSeries(seriesDevDown);

            AddChart(chart);
        }
        
        public void OnData(TradeBars data) 
        {
        	if (data.Count < 2)
        	{
        		return;
        	}

        	Plot(iChartName, "Stock #1", data[iSymbol1].Price);
        	Plot(iChartName, "Stock #2", data[iSymbol2].Price);
        	Plot(iChartName, "Balance", iBalance);
        	Plot(iChartName, "Osc #1", iOsc1);
        	Plot(iChartName, "Osc #2", iOsc2);
        	Plot(iChartName, "Spread", iSpread);
        	Plot(iChartName, "Dev Up x 2", iDev * 2);
        	Plot(iChartName, "Dev Dn x 2", iDev * 2 * -1);

			var direction = CanOpen();
			var update = CanUpdate();
			var balance = iBalance / 4;

			if (update != 0) 
			{
				direction = iDirection;
			}

			var ratio = Math.Max(iDev1, 0.01m) / Math.Max(iDev2, 0.01m);
			var volume1 = balance;
			var volume2 = balance;

			volume1 = ratio > 1 ? volume1 / ratio : volume1;
			volume2 = ratio < 1 ? volume2 / ratio : volume2;

			volume1 = Convert.ToDecimal(volume1 / data[iSymbol1].Close);
			volume2 = Convert.ToDecimal(volume2 / data[iSymbol2].Close);

			if (direction > 0 && volume1 > 1 && volume2 > 1) 
            {
            	iDirection = direction;
            	Plot(iChartName, "Sell #1", Securities[iSymbol1].Close);
            	Plot(iChartName, "Buy #2", Securities[iSymbol2].Close);
            	Action(iSymbol1, volume1, -1);
            	Action(iSymbol2, volume2, 1);
                return;
            }

            if (direction < 0 && volume1 > 1 && volume2 > 1) 
            {
            	iDirection = direction;
            	Plot(iChartName, "Buy #1", Securities[iSymbol1].Close);
            	Plot(iChartName, "Sell #2", Securities[iSymbol2].Close);
            	Action(iSymbol1, volume1, 1);
            	Action(iSymbol2, volume2, -1);
                return;
            }
            
            if (CanClose() == 1) 
            {
                Liquidate();
                return;
            }
        }
        
		protected OrderTicket Action(string symbol, decimal volume, int direction)
		{
			var operation = (direction > 0 ? "Buy #" : "Sell #") + (++iOrderId);
			var ticket = MarketOrder(symbol, volume * direction, false, operation);

			iDeals[ticket.OrderId] = new iDeal { Market = ticket.OrderId };

			var process = new Thread(() => {

				Transactions.WaitForOrder(ticket.OrderId);

				if (Transactions.GetOrderById(ticket.OrderId).Status != OrderStatus.Filled) 
				{
					return;
				}

				var price = Securities[symbol].Price;
	        	//var orderSL = StopMarketOrder(symbol, -volume * direction, price - 5m * direction, "SL #" + ticket.OrderId.ToString());
	        	//var orderTP = LimitOrder(symbol, -volume * direction, price + iIncomePips * direction, "TP #" + ticket.OrderId.ToString());	

				//iDeals[ticket.OrderId].SL = orderSL.OrderId;
				//iDeals[ticket.OrderId].TP = orderTP.OrderId;
			});

			process.Start();

			return ticket;
		}

        protected int GetDirection(decimal level)
        {
        	var deviation = Math.Max(Math.Abs(iDev) * level, iMinSpread);
        	var spread = Math.Abs(iSpread);

            if (IsWarmingUp == false && iSpread.IsReady && iDev.IsReady && spread > deviation)
            {
            	if (iOsc1 > iOsc2) 
                {
                	return 1;
                }

                if (iOsc1 < iOsc2) 
                {
                	return -1;
                }
            }

            return 0;
        }

        protected int CanOpen()
        {
            if (Portfolio.Invested == false)
            {
                return GetDirection(2.0m);
            }

            return 0;
        }

		protected int CanUpdate() 
        {
        	if (Portfolio.Invested && iDirection == GetDirection(3.0m))
            {
                return iDirection;
            }

            return 0;
        }

        protected int CanClose() 
        {
        	var balance = GetBalance(0);
        	var direction = GetDirection(2.0m);
        	var isStop = Math.Abs(balance) > iBalance * iStopPercents;
			var isUp = iDirection < 0 && direction > 0;
        	var isDown = iDirection > 0 && direction < 0;

			if (isUp || isDown || isStop)
			{
				iDirection = 0;
				iBalance += Portfolio.TotalUnrealizedProfit;
				return 1;
			}

            return 0;
        }
        
        protected decimal GetBalance(decimal balance)
        {
        	return balance + 
        		Portfolio.TotalUnrealizedProfit + 
        		Portfolio.TotalProfit - 
        		Portfolio.TotalFees;
        }
    }
}