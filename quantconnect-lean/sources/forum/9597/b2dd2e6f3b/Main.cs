using MathNet.Numerics.LinearAlgebra;
using QuantConnect.Algorithm.Framework.Portfolio;
using QuantConnect.Data;
using QuantConnect.Scheduling;
using System;
using System.Collections.Generic;
using System.Linq;

/// <summary>
/// In and Out Strategy.
/// Originally from Quantopian:  https://www.quantopian.com/posts/new-strategy-in-and-out
/// Continued on QuantConnect:  https://www.quantconnect.com/forum/discussion/9597/the-in-amp-out-strategy-continued-from-quantopian
/// C# v1.1:  This C# version's seed is Tristan F's Python code v1.1, posted on 11/19/2020.
/// </summary>
namespace QuantConnect.Algorithm.CSharp.Jon.InAndOut
{
    public class InAndOut001Algorithm : QCAlgorithm
    {
        private readonly IEnumerable<int> _momentumPeriods = Enumerable.Range(55, 11);
        private readonly int _historyDays = 252;
        private readonly int _waitDays = 15;
        private readonly double _percentile = 0.01d;

        private int _outDays = 0;
        private bool _isIn = true;

        private string[] _keyIndicatorTickers;
        private List<Symbol> _symbols = new List<Symbol>();

        private IDictionary<string, decimal> _weights = new Dictionary<string, decimal>();
        private IDictionary<string, decimal> _inWeights = new Dictionary<string, decimal>();
        private IDictionary<string, decimal> _outWeights = new Dictionary<string, decimal>();
        private IDictionary<string, decimal> _lastWeights = new Dictionary<string, decimal>();

        public override void Initialize()
        {
            #region Backtest Parameters - these are ignored in live trading.

            SetStartDate(2008, 1, 1);
            //SetEndDate(2015, 1, 3);
            SetCash(100000);

            // Use the Alpha Streams Brokerage Model, developed in conjunction with
            // funds to model their actual fees, costs, etc.
            // Please do not add any additional reality modelling, such as Slippage, Fees, Buying Power, etc.
            //SetBrokerageModel(new AlphaStreamsBrokerageModel());

            #endregion

            #region Assets

            var benchmarkTickers = new[] { "SPY" };
            var inTickers = new[] { "QQQ" };
            var outTickers = new[] { "TLT", "IEF" };

            _keyIndicatorTickers = new[] { "DBB", "IGE", "SHY", "XLI" };

            var modIndicatorTickers = new[] { "UUP", "SLV", "GLD", "XLU", "FXA", "FXF" };

            var tickers = benchmarkTickers.Union(inTickers).Union(outTickers).Union(_keyIndicatorTickers).Union(modIndicatorTickers);
            foreach (var ticker in tickers)
            {
                _symbols.Add(AddEquity(ticker, Resolution.Minute).Symbol);
            }

            #endregion

            #region Initialize Weights

            var inOutTickers = inTickers.Union(outTickers);
            foreach (var inOutTicker in inOutTickers)
            {
                _weights[inOutTicker] = 0.0m;
                _inWeights[inOutTicker] = 0.0m;
                _outWeights[inOutTicker] = 0.0m;
            }

            foreach (var inTicker in inTickers)
            {
                _inWeights[inTicker] = 1.0m / inTickers.Count();
            }

            foreach (var outTicker in outTickers)
            {
                _outWeights[outTicker] = 1.0m / outTickers.Count();
            }

            _lastWeights = _weights;

            #endregion

            #region Schedule Functions

            var benchmark = _symbols.First();

            Schedule.On(DateRules.EveryDay(benchmark), TimeRules.AfterMarketOpen(benchmark, 90), () =>
            {
                RebalanceOut();
            });

            Schedule.On(DateRules.WeekEnd(benchmark), TimeRules.AfterMarketOpen(benchmark, 90), () =>
            {
                RebalanceIn();
            });

            #endregion
        }

        private void RebalanceOut()
        {
            var history = History(_symbols, _historyDays, Resolution.Daily);

            var historicalMatrix = GetHistoricalMatrix(history);
            var shiftedMatrix = GetShiftedMatrix(historicalMatrix);
            var returnMatrix = historicalMatrix.PointwiseDivide(shiftedMatrix).Subtract(1);
            var keyMatrix = GetKeyMatrix(returnMatrix);

            var isExtreme = IsExtremeCondition(keyMatrix);
            var adjustedWaitDays = _waitDays;

            if (isExtreme)
            {
                _outDays = 0;
                _isIn = false;
                _weights = _outWeights;
            }

            if (_outDays >= adjustedWaitDays)
            {
                _isIn = true;
            }

            _outDays++;
        }

        private void RebalanceIn()
        {
            if (_isIn)
            {
                _weights = _inWeights;
            }
        }

        public override void OnData(Slice slice)
        {
            var weightsEqual = _weights.Count == _lastWeights.Count && !_weights.Except(_lastWeights).Any();
            if (!weightsEqual)
            {
                var targets = new List<PortfolioTarget>();
                foreach (var weight in _weights)
                {
                    var symbol = _symbols.Find(s => s.Value == weight.Key);
                    var target = new PortfolioTarget(symbol, weight.Value);
                    targets.Add(target);
                }

                SetHoldings(targets);
                _lastWeights = _weights;
            }
        }

        private Matrix<double> GetHistoricalMatrix(IEnumerable<Slice> history)
        {
            var result = Matrix<double>.Build.Dense(_historyDays, _symbols.Count(), double.NaN);
            var rowIndex = 0;
            foreach (var slice in history)
            {
                var vector = new List<double>();
                foreach (var symbol in _symbols)
                {
                    if (slice.ContainsKey(symbol))
                    {
                        vector.Add(decimal.ToDouble(slice[symbol].Close));
                    }
                    else
                    {
                        vector.Add(double.NaN);
                    }
                }
                result.SetRow(rowIndex++, vector.ToArray());
            }
            return RemoveNans(result);
        }

        private Matrix<double> GetShiftedMatrix(Matrix<double> matrix)
        {
            var result = Matrix<double>.Build.Dense(matrix.RowCount, _symbols.Count());
            foreach (var period in _momentumPeriods)
            {
                result = result.Add(Shift(matrix, period));
            }
            return result.Map(m => m / _momentumPeriods.Count());
        }

        private Matrix<double> GetKeyMatrix(Matrix<double> matrix)
        {
            var result = Matrix<double>.Build.Dense(matrix.RowCount, 1);
            foreach (var ticker in _keyIndicatorTickers)
            {
                var subMatrix = GetSubmatrix(matrix, ticker);
                result = result.Append(subMatrix);
            }

            var uup = GetSubmatrix(matrix, "UUP");
            uup = uup.Map(m => -m);
            result = result.Append(uup);

            var slv = GetSubmatrix(matrix, "SLV");
            var gld = GetSubmatrix(matrix, "GLD");
            result = result.Append(slv.Subtract(gld));

            var xli = GetSubmatrix(matrix, "XLI");
            var xlu = GetSubmatrix(matrix, "XLU");
            result = result.Append(xli.Subtract(xlu));

            var fxa = GetSubmatrix(matrix, "FXA");
            var fxf = GetSubmatrix(matrix, "FXF");
            result = result.Append(fxa.Subtract(fxf));

            return RemoveNans(result.RemoveColumn(0));
        }

        private bool IsExtremeCondition(Matrix<double> matrix)
        {
            var lastRow = matrix.SubMatrix(matrix.RowCount - 1, 1, 0, matrix.ColumnCount);

            var list = new List<double>();
            foreach (var column in matrix.EnumerateColumns())
            {
                list.Add(GetPercentile(column.ToArray(), _percentile));
            }

            var percentiles = Matrix<double>.Build.Dense(1, matrix.ColumnCount, list.ToArray());

            // todo_jon:  Here the percentiles are off by a bit.
            // Is it because the GetPercentile function is not the same as python's nanpercentile?
            // Is it due to differences in datatype rounding decimal vs double?
            // 3rd item (SHY):  py = 0.00243602,  c# = 0.00236798
            // 5th item (UUP):  py = -0.01071986, c# = -0.0108586
            // To reproduce, use:
            //     StartDate:  01/01/2008
            //     EndDate:  01/02/2008
            // Debug(percentiles.ToString());

            return percentiles.Subtract(lastRow).Exists(m => m > 0);
        }

        private Matrix<double> RemoveNans(Matrix<double> matrix)
        {
            if (matrix == null)
            {
                return null;
            }

            while (matrix.Find(n => n.Equals(double.NaN)) != null)
            {
                var v = matrix.Find(n => n.Equals(double.NaN));
                matrix = matrix.RemoveRow(v.Item1);
            }
            return matrix;
        }

        private Matrix<double> Shift(Matrix<double> matrix, int shift)
        {
            matrix = matrix.SubMatrix(0, matrix.RowCount - shift, 0, matrix.ColumnCount);
            for (int i = 0; i < shift; i++)
            {
                matrix = matrix.InsertRow(i, Vector<double>.Build.Dense(matrix.ColumnCount, double.NaN));
            }
            return matrix;
        }

        private Matrix<double> GetSubmatrix(Matrix<double> matrix, string ticker)
        {
            var symbol = _symbols.Find(s => s.Value == ticker);
            var index = _symbols.IndexOf(symbol);
            return matrix.SubMatrix(0, matrix.RowCount, index, 1);
        }

        private double GetPercentile(double[] sequence, double percentile)
        {
            Array.Sort(sequence);
            int count = sequence.Length;

            double n = (count - 1) * percentile + 1;
            // Another method: double n = (count + 1) * percentile;

            if (n == 1.0d)
            {
                return sequence[0];
            }
            else if (n == count)
            {
                return sequence[count - 1];
            }
            else
            {
                int k = (int)n;
                double d = n - k;
                return sequence[k - 1] + d * (sequence[k] - sequence[k - 1]);
            }
        }
    }
}