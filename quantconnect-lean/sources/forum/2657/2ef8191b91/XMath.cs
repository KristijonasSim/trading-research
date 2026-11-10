using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace QuantConnect.Algorithm.CSharp
{
    public static class XMath
    {
        public static bool IsPowerOfTwo(ulong x)
        {
            return (x & (x - 1)) == 0;
        }

        public static int Log2(int v)
        {
            int r = 0xFFFF - v >> 31 & 0x10;
            v >>= r;
            int shift = 0xFF - v >> 31 & 0x8;
            v >>= shift;
            r |= shift;
            shift = 0xF - v >> 31 & 0x4;
            v >>= shift;
            r |= shift;
            shift = 0x3 - v >> 31 & 0x2;
            v >>= shift;
            r |= shift;
            r |= (v >> 1);
            return r;
        }

        public static void Clamp<T>(ref T val, T min, T max) where T : IComparable
        {
            if (min.CompareTo(val) > 0)
                val = min;
            else if (max.CompareTo(val) < 0)
                val = max;
        }
    }
}