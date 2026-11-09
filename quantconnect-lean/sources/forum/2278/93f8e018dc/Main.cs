//Copyright Warren Harding 2016, granted to the public domain.
//Use entirely at your own risk.
//Custom algorithm development: warrencharding@yahoo.com.
//
// Modified by John Roc to trade multiple pairs equally weighted in portfolio
//  Changes:
//  	1. Upto 10 ETF pairs in order
//		2. Independent Standard Deviation parameters for each pairs
//		3. DataNormalizationMode set to raw to get unadjusted prices
//
//Do not remove this copyright notice.
namespace QuantConnect 
{   
    public class LevETFs : QCAlgorithm
    {
    	//StandardDeviation std1, std2, std3, std4, std5;
    	
    	int indicatorPeriod=360;
    	double portfolio_weight=1.0;
    	Resolution resolution=Resolution.Minute;
    	string[] etf = { "TQQQ", "UPRO" };
    	string[] invetf = { "SQQQ", "SPXU" };
    	
    	//string[] etf = {"TQQQ"};
    	//string[] invetf = {"SQQQ"};
    	
    	
    	//decimal myStdDevConst = 1.75m;
    	decimal[] myStdDevConst = new decimal[] {1.2m,1.75m};
    	
    	// Note that the size of the array is limited to handle 10 pairs
    	StandardDeviation[] std = new StandardDeviation[10];
    	
        public override void Initialize() 
        {

        	IEnumerable<TradeBar>[] history = new IEnumerable<TradeBar>[10];
      
        	// distribute weight queally among ETF pairs
        	portfolio_weight = 1.0/(etf.Length);
        	
        	// backtest parameters
            //SetStartDate(2009, 10, 05);         
            SetStartDate(2010, 3, 5);
            //SetEndDate(2017, 03, 31);
            
            // cash allocation
            SetCash(1000000);
            
            for (int i=0 ; i< etf.Length; i++) {
            
	            AddEquity(etf[i], resolution,Market.USA,true,1m,false);
	            AddEquity(invetf[i], resolution,Market.USA,true,1m,false);
	           	
	           	// need to use raw normalized mode to avoid look ahead bias and prices before inverse splits
	           	Securities[etf[i]].SetDataNormalizationMode(DataNormalizationMode.Raw);
	            Securities[invetf[i]].SetDataNormalizationMode(DataNormalizationMode.Raw);
	            
	            std[i] = STD(etf[i], indicatorPeriod, resolution);
        		history[i] = History(etf[i], indicatorPeriod, resolution);
	            foreach (var tradeBar in history[i])
	            {
	            	std[i].Update(tradeBar.EndTime, tradeBar.Close);
	            }
	            
            }
            
           
        }


        public override void OnData(Slice data) 
        {
        	
        	for(int x=0; x < etf.Length; x++ ){
	        	if (std[x] < myStdDevConst[x])
	        	{
	    			//SetHoldings(invetf[x], 0);
	    			if(Securities[invetf[x]].Invested)
	    				SetHoldings(invetf[x], 0);
	    				//Liquidate(invetf[x]);
	    			if(Securities[etf[x]].Invested == false)
	    				SetHoldings(etf[x], portfolio_weight);
	    			Error(Time.ToString() + "|" + myStdDevConst[x].ToString() + "|" + std[x].ToString() + "|" + etf[x] + "|" + portfolio_weight.ToString());
	        	}
	        	else
	        	{
	    			//SetHoldings(etf[x], 0);
	    			if(Securities[etf[x]].Invested)
	    				SetHoldings(etf[x], 0);
	    				//Liquidate(etf[x]);
	    			if(Securities[invetf[x]].Invested == false)
	    				SetHoldings(invetf[x], portfolio_weight);
	    			Error(Time.ToString() + "|" + myStdDevConst[x].ToString() + "|" + std[x].ToString() + "|" + invetf[x] + "|" + portfolio_weight.ToString());
	        	}

        	}
 	
        }
    }
}