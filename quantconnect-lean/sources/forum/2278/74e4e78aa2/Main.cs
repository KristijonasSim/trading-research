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
            
            AddEquity("TQQQ", resolution);
            AddEquity("SQQQ", resolution);
            
            std = STD("TQQQ", indicatorPeriod, resolution);
        	var history = History("TQQQ", indicatorPeriod, resolution);
            foreach (var tradeBar in history)
            {
            	std.Update(tradeBar.EndTime, tradeBar.Close);
            }
        }

        public override void OnData(Slice data) 
        {
        	if (std<1.2m)
        	{
    			SetHoldings("SQQQ", 0);
    			SetHoldings("TQQQ", 1.0);
        	}
        	else
        	{
    			SetHoldings("TQQQ", 0);
    			SetHoldings("SQQQ", 1.0);
        	}
        }
    }
}