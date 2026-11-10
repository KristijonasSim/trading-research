using System;
using System.Threading;

namespace QuantConnect.Algorithm.CSharp
{
    sealed class PollingThread
    {
        private readonly Thread _thread;
        private readonly CancellationTokenSource _cancellation;
        private readonly Action _action;
        private readonly bool _startWithWait;

        public double PollingInterval { get; set; }

        public PollingThread(bool startWithWait, Action action)
        {
            _startWithWait = startWithWait;
            _action = action;
            _cancellation = new CancellationTokenSource();
            _thread = new Thread(ThreadFunc);
        }

        public void Start()
        {
            _thread.Start();
        }

        private void ThreadFunc()
        {
            var token = _cancellation.Token;

            if (_startWithWait)
                Wait();

            while (!token.IsCancellationRequested)
            {
                _action();
                Wait();
            }
        }

        private void Wait()
        {
            var endTime = DateTime.Now + TimeSpan.FromSeconds(PollingInterval);

            while (DateTime.Now <= endTime)
            {
                var timeUntilEnd = endTime - DateTime.Now;
                Thread.Sleep(Math.Min(100, timeUntilEnd.Milliseconds));
            }
        }

        public void Cancel()
        {
            _cancellation.Cancel();
        }

        public void Join()
        {
            _thread.Join();
        }
    }
}