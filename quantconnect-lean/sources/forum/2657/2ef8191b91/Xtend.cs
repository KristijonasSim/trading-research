using System;
using System.Collections.Generic;
using System.Reflection;

namespace QuantConnect.Algorithm.CSharp
{
    public static class Xtend
    {
        public static FieldInfo GetPrivateField(Type type, string name)
        {
            return type.GetField(name, BindingFlags.NonPublic | BindingFlags.Instance);
        }

        public static FieldInfo GetPrivateField<MyType>(this MyType dummy, string name)
        {
            return GetPrivateField(typeof(MyType), name);
        }

        public static object GetPrivateFieldValue(Type type, object instance, string name)
        {
            var fieldInfo = GetPrivateField(type, name);
            if (fieldInfo == null)
                throw new InvalidOperationException("Unable to find field with name " + name);
            return fieldInfo.GetValue(instance);
        }

        public static object GetPrivateFieldValue<MyType>(this MyType instance, string name)
        {
            return GetPrivateFieldValue(typeof(MyType), instance, name);
        }

        public static T Clamp<T>(this T val, T min, T max) where T : IComparable
        {
            XMath.Clamp(ref val, min, max);
            return val;
        }

        public static void Shuffle<T>(this IList<T> list, Random rng)
        {
            int n = list.Count;
            while (n > 1)
            {
                n--;
                int k = rng.Next(n + 1);
                T value = list[k];
                list[k] = list[n];
                list[n] = value;
            }
        }

        public static int Argmax(this IList<int> list)
        {
            int maxIndex = list.Count - 1;
            var max = list[maxIndex];
            for (int index = list.Count - 2; index >= 0; --index)
            {
                var x = list[index];
                if (x > max)
                {
                    maxIndex = index;
                    max = x;
                }
            }

            return maxIndex;
        }

        public static int Argmin(this IList<int> list)
        {
            int minIndex = list.Count - 1;
            var min = list[minIndex];
            for (int index = list.Count - 2; index >= 0; --index)
            {
                var x = list[index];
                if (x < min)
                {
                    minIndex = index;
                    min = x;
                }
            }

            return minIndex;
        }

        public static int Argmax(this IList<double> list)
        {
            int maxIndex = list.Count - 1;
            var max = list[maxIndex];
            for (int index = list.Count - 2; index >= 0; --index)
            {
                var x = list[index];
                if (x > max)
                {
                    maxIndex = index;
                    max = x;
                }
            }

            return maxIndex;
        }

        public static int Argmin(this IList<double> list)
        {
            int minIndex = list.Count - 1;
            var min = list[minIndex];
            for (int index = list.Count - 2; index >= 0; --index)
            {
                var x = list[index];
                if (x < min)
                {
                    minIndex = index;
                    min = x;
                }
            }

            return minIndex;
        }
    }
}