using QuantConnect.Interfaces;
using QuantConnect.Securities;
using System;
using System.Linq;
using System.Reflection;

namespace QuantConnect.Algorithm.CSharp
{
    public static class PrivateAPI
    {
        private static IBrokerage _brokerage;

        public static IBrokerage GetBrokerage(QCAlgorithm algo)
        {
            if (_brokerage != null)
                return _brokerage;

            var orderProcessor = (IOrderProcessor)GetPrivateFieldValue(algo.Transactions, "_orderProcessor");
            if (orderProcessor == null)
                throw new Exception("Cannot find _orderProcessor in SecurityTransactionManager");

            var assemblies = AppDomain.CurrentDomain.GetAssemblies();
            var allTypes = assemblies.SelectMany(a => a.GetTypes());
            var choices = allTypes.Where(t => t.FullName.EndsWith(".BrokerageTransactionHandler")).ToArray();
            if (choices.Length > 1)
            {
                throw new Exception("More than one: " + string.Join(" ", choices.Select(x => x.FullName).ToArray()));
            }
            var brokerageTransactionHandlerType = choices.Single();
            _brokerage = (IBrokerage)GetPrivateFieldValue(brokerageTransactionHandlerType, orderProcessor, "_brokerage");

            if (_brokerage == null)
                throw new Exception("Brokerage cannot be accessed via reflection");
            return _brokerage;
        }

        private static FieldInfo GetPrivateField(Type type, string name)
        {
            return type.GetField(name, BindingFlags.NonPublic | BindingFlags.Instance);
        }

        private static FieldInfo GetPrivateField<MyType>(MyType dummy, string name)
        {
            return GetPrivateField(typeof(MyType), name);
        }

        private static object GetPrivateFieldValue(Type type, object instance, string name)
        {
            var fieldInfo = GetPrivateField(type, name);
            return fieldInfo.GetValue(instance);
        }

        private static object GetPrivateFieldValue<MyType>(MyType instance, string name)
        {
            return GetPrivateFieldValue(typeof(MyType), instance, name);
        }
    }
}