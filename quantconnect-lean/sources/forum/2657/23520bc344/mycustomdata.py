# Your New Python File
from QuantConnect.Python import PythonQuandl # quandl data not CLOSE
from QuantConnect.Python import PythonData # custom data
from QuantConnect.Data import SubscriptionDataSource

from datetime import datetime, timedelta
import decimal

class CboeVix(PythonData):
    '''CBOE Vix Download Custom Data Class'''
    def GetSource(self, config, date, isLiveMode):
        url_vix = "http://www.cboe.com/publish/scheduledtask/mktdata/datahouse/vixcurrent.csv"
        return SubscriptionDataSource(url_vix, 
                                      SubscriptionTransportMedium.RemoteFile)
    def Reader(self, config, line, date, isLiveMode):
        if not (line.strip() and line[0].isdigit()): return None
        # New CboeVix object
        index = CboeVix();
        index.Symbol = config.Symbol
        try:
            # Example File Format:
            # Date          VIX Open    VIX High VIX Low    VIX Close
            # 01/02/2004    17.96    18.68     17.54        18.22
            #print line
            data = line.split(',')
            date = data[0].split('/')
            index.Time = datetime(int(date[2]), int(date[0]), int(date[1]))
            index.Value = decimal.Decimal(data[4])
            index["Open"] = float(data[1])
            index["High"] = float(data[2])
            index["Low"] = float(data[3])
            index["Close"] = float(data[4])
        except ValueError:
            # Do nothing
            return None
#       except KeyError, e:
#          print 'I got a KeyError - reason "%s"' % str(e)
        return index


# NB: CboeVxV class ==  CboeVix class, except for the URL
class CboeVxV(PythonData):
    '''CBOE VXV Download Custom Data Class'''
    
    def GetSource(self, config, date, isLiveMode):
        url_vxv = "http://www.cboe.com/publish/scheduledtask/mktdata/datahouse/vix3mdailyprices.csv"
        return SubscriptionDataSource(url_vxv, 
                                      SubscriptionTransportMedium.RemoteFile)
    def Reader(self, config, line, date, isLiveMode):
        if not (line.strip() and line[0].isdigit()): return None
        index = CboeVxV();
        index.Symbol = config.Symbol
        try:
        # Example File Format:
        #                 OPEN    HIGH    LOW        CLOSE
        # 12/04/2007    24.8    25.01    24.15    24.65
            data = line.split(',')
            date = data[0].split('/')
            index.Time = datetime(int(date[2]), int(date[0]), int(date[1]))
            index.Value = decimal.Decimal(data[4])
            index["Open"] = float(data[1])
            index["High"] = float(data[2])
            index["Low"] = float(data[3])
            index["Close"] = float(data[4])
        except ValueError:
                # Do nothing
                return None
        return index

# for using VIX futures settle in calc. ratios like VIX/VIX1
class QuandlFuture(PythonQuandl):
    '''Custom quandl data type for setting customized value column name. 
       Value column is used for the primary trading calculations and charting.'''
    def __init__(self):
        # Define ValueColumnName: cannot be None, Empty or non-existant column name
        # If ValueColumnName is "Close", do not use PythonQuandl, use Quandl:
        # self.AddData[QuandlFuture](self.VIX1, Resolution.Daily)
        self.ValueColumnName = "Settle"