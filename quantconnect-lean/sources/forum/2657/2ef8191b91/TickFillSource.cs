using QuantConnect.Data.Market;
using QuantConnect.Orders;
using System.Collections.Generic;
using System.Linq;

namespace QuantConnect.Algorithm.CSharp
{
    public sealed class TickFillSource
    {
        private readonly Symbol _symbol; //just to check for validity
        private List<Tick> _ticksToFill = new List<Tick>();

        public IEnumerable<Tick> Ticks { get; private set; }

        //public int DataVersion { get; private set; } //needed so we can't fill new order with ticks given at same iteration

        public TickFillSource(Symbol symbol)
        {
            _symbol = symbol;
        }

        public void SetTicks(IEnumerable<Tick> ticks)
        {
            Ticks = ticks.ToArray();
            //DataVersion += 1;
            _ticksToFill.Clear();
            //Reverse() because we want to remove newest at tail a lot of the time
            var range = ticks.Reverse().Where(x => x.TickType == TickType.Trade && x.Symbol == _symbol);
            //_ticksToFill.AddRange(range);
            _ticksToFill = range.ToList(); //AddRange having problem with enumerator...
        }

        public int GetFirstTickIndex()
        {
            return _ticksToFill.Count - 1;
        }

        public int GetPreviousTickIndex(int index)
        {
            return index + 1;
        }

        private Tick PeekOrDequeueTickIfAny(ref int index, bool remove, decimal limit, OrderDirection direction)
        {
            //a more accurate model that takes into account volume is most likely not needed
            //thus this (more) simple and fast implementation

            while (index >= 0)
            {
                var tick = _ticksToFill[index];
                bool match = false;
                if (direction == OrderDirection.Buy)
                {
                    if (tick.Price < limit)
                        match = true;
                }
                else if (direction == OrderDirection.Sell)
                {
                    if (tick.Price > limit)
                        match = true;
                }

                if (remove)
                    _ticksToFill.RemoveAt(index);

                index -= 1;

                if (match)
                    return tick;
            }

            return null;
        }

        public Tick DequeueNextTickIfAny(ref int index, decimal limit, OrderDirection direction)
        {
            return PeekOrDequeueTickIfAny(ref index, true, limit, direction);
        }

        public Tick PeekNextTickIfAny(ref int index, decimal limit, OrderDirection direction)
        {
            return PeekOrDequeueTickIfAny(ref index, false, limit, direction);
        }
    }
}