from dateutil.relativedelta import relativedelta

class FF(PythonData):
    """
    This class is used to stream Fama French data into our algorithm.
    """
    
    def GetSource(self, config, date, isLiveMode):
        """
        Return the URL string source of the file. This will be converted to a stream 
        
        Inputs:
         - config
            Configuration object
         - date
            Date of this source file
         - isLiveMode
            True if we're in live mode; False for backtesting mode
        
        Returns a SubscriptionDataSource - the source location and transport medium for a subscription.
        """
        source = "https://github.com/QuantConnect/Tutorials/raw/feature-data-directory/Data/F-F_Research_Data_Factors.csv"
        return SubscriptionDataSource(source, SubscriptionTransportMedium.RemoteFile)
    
    def Reader(self, config, line, date, isLive):
        """
        Reader converts each line of the data source into BaseData objects. Each data type creates its own 
        factory method, and returns a new instance of the object each time it is called. The returned object 
        is assumed to be time stamped in the config.ExchangeTimeZone.
        
        Inputs:
         - config
            Subscription data config setup object
         - line
            Line of the source document
         - date
            Date of the requested data
         - isLive
            True if we're in live mode; False for backtesting mode
        
        Returns a data point from the Fama French data feed.
        """
        # If first character is not digit, pass
        if not (line.strip() and line[0].isdigit()): 
            return None
    
        try:
            data = line.split(',')

            ff = FF()
            ff.Symbol = config.Symbol
            ff.Time = datetime.strptime(data[0], '%Y%m') + relativedelta(months=1)

            ff.SetProperty("hml", float(data[3]))
            ff.SetProperty("mkt", float(data[1]))
            ff.SetProperty("rf", float(data[4]))
            ff.SetProperty("smb", float(data[2]))
            
            return ff
        except ValueError:
            # Do nothing, possible error in json decoding
            return None