//Copyright Warren Harding 2016, granted to the public domain.
//Use entirely at your own risk.
//Custom algorithm development: warrencharding@yahoo.com.
//Do not remove this copyright notice.
namespace QuantConnect 
{   
    public class TQQQSQQQ : QCAlgorithm
    {
    	StandardDeviation std;
    	int indicatorPeriod=390;
    	Resolution resolution=Resolution.Minute;
        public override void Initialize() 
        {
        	// backtest parameters
            SetStartDate(2012, 8, 11);         
            SetEndDate(2017, 8, 11);
            
            // cash allocation
            SetCash(25000);
            
            AddEquity("QQQ", resolution);
            AddEquity("PSQ", resolution);
            
            std = STD("QQQ", indicatorPeriod, resolution);
        	var history = History("QQQ", indicatorPeriod, resolution);
            foreach (var tradeBar in history)
            {
            	std.Update(tradeBar.EndTime, tradeBar.Close);
            }
        }

        public override void OnData(Slice data) 
        {
        	if (std<1.2m)
        	{
    			SetHoldings("PSQ", 0);
    			SetHoldings("QQQ", 1.0);
        	}
        	else
        	{
    			SetHoldings("QQQ", 0);
    			SetHoldings("PSQ", 1.0);
        	}
        }
    }
}