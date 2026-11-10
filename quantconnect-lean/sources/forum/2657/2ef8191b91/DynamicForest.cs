// Accord Machine Learning Library
// The Accord.NET Framework
// http://accord-framework.net
//
// Copyright © Alex Risman, 2016
// https://github.com/mthmn20
//
// Copyright © César Souza, 2009-2017
// cesarsouza at gmail.com
//
//    This library is free software; you can redistribute it and/or
//    modify it under the terms of the GNU Lesser General Public
//    License as published by the Free Software Foundation; either
//    version 2.1 of the License, or (at your option) any later version.
//
//    This library is distributed in the hope that it will be useful,
//    but WITHOUT ANY WARRANTY; without even the implied warranty of
//    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
//    Lesser General Public License for more details.
//
//    You should have received a copy of the GNU Lesser General Public
//    License along with this library; if not, write to the Free Software
//    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
//

namespace QuantConnect.Algorithm.CSharp
{
    using System;
    using System.Collections.Generic;
    using System.Threading.Tasks;
    using System.Runtime.Serialization;
    using Accord.Math;
    using System.Threading;
    using Accord.MachineLearning;
    using Accord.MachineLearning.DecisionTrees;
    /// <summary>
    ///   Random Forest.
    /// </summary>
    /// 
    /// <remarks>
    /// <para>
    ///   Represents a random forest of <see cref="DecisionTree"/>s. For 
    ///   sample usage and example of learning, please see the documentation
    ///   page for <see cref="RandomForestLearning"/>.</para>
    /// </remarks>
    /// 
    /// <example>
    /// <para>
    ///   This example shows the simplest way to induce a decision tree with continuous variables.</para>
    /// <code source="Unit Tests\Accord.Tests.MachineLearning\DecisionTrees\RandomForestTest.cs" region="doc_iris" />
    /// <para>
    ///   The next example shows how to induce a decision tree with continuous variables using a 
    ///   <see cref="Accord.Statistics.Filters.Codification">codebook</see> to manage how input 
    ///   variables should be encoded.</para>
    /// <code source="Unit Tests\Accord.Tests.MachineLearning\DecisionTrees\RandomForestTest.cs" region="doc_nursery" />
    /// </example>
    /// 
    /// <seealso cref="DecisionTree"/>
    /// <seealso cref="RandomForestLearning"/>
    /// 
    [Serializable]
    public class DynamicForest : MulticlassClassifierBase, IParallel
    {
        [NonSerialized]
        private ParallelOptions parallelOptions;


        /// <summary>
        ///   Gets the trees in the random forest.
        /// </summary>
        /// 
        public readonly List<MulticlassClassifierBase<double[]>> Trees = new List<MulticlassClassifierBase<double[]>>();

        /// <summary>
        ///   Gets the number of classes that can be recognized
        ///   by this random forest.
        /// </summary>
        /// 
        [Obsolete("Please use NumberOfOutputs instead.")]
        public int Classes { get { return NumberOfOutputs; } }

        /// <summary>
        ///   Gets or sets the parallelization options for this algorithm.
        /// </summary>
        /// 
        public ParallelOptions ParallelOptions
        {
            get { return parallelOptions; }
            set { parallelOptions = value; }
        }

        /// <summary>
        /// Gets or sets a cancellation token that can be used
        /// to cancel the algorithm while it is running.
        /// </summary>
        /// 
        public CancellationToken Token
        {
            get { return ParallelOptions.CancellationToken; }
            set { ParallelOptions.CancellationToken = value; }
        }

        /// <summary>
        ///   Creates a new random forest.
        /// </summary>
        /// 
        /// <param name="trees">The number of trees in the forest.</param>
        /// <param name="classes">The number of classes in the classification problem.</param>
        /// 
        public DynamicForest(int classes)
        {
            this.NumberOfOutputs = classes;
            this.ParallelOptions = new ParallelOptions();
        }

        /// <summary>
        ///   Computes the decision output for a given input vector.
        /// </summary>
        /// 
        /// <param name="data">The input vector.</param>
        /// 
        /// <returns>The forest decision for the given vector.</returns>
        /// 
        [Obsolete("Please use Decide() instead.")]
        public int Compute(double[] data)
        {
            return Decide(data);
        }


        /// <summary>
        /// Computes a class-label decision for a given <paramref name="input" />.
        /// </summary>
        /// <param name="input">The input vector that should be classified into
        /// one of the <see cref="ITransform.NumberOfOutputs" /> possible classes.</param>
        /// <returns>A class-label that best described <paramref name="input" /> according
        /// to this classifier.</returns>
        public override int Decide(double[] input)
        {
            int[] responses = new int[NumberOfOutputs];
            Parallel.For(0, Trees.Count, ParallelOptions, i =>
            {
                int j = Trees[i].Decide(input);
                Interlocked.Increment(ref responses[j]);
            });

            return responses.ArgMax();
        }

        public int Decide(double[] input, Func<int, double> treeWeightFunc)
        {
            double[] responses = new double[NumberOfOutputs];
            Parallel.For(0, Trees.Count, ParallelOptions, i =>
            {
                try
                {
                    int j = Trees[i].Decide(input);
                    Add(ref responses[j], treeWeightFunc(i));
                }
                catch (Exception)
                {
                    //quick fix
                }
            });

            return responses.ArgMax();
        }

        private static double Add(ref double location1, double value)
        {
            double newCurrentValue = location1; // non-volatile read, so may be stale
            while (true)
            {
                double currentValue = newCurrentValue;
                double newValue = currentValue + value;
                newCurrentValue = Interlocked.CompareExchange(ref location1, newValue, currentValue);
                if (newCurrentValue == currentValue)
                    return newValue;
            }
        }

        /// <summary>
        ///   Called when the object is being deserialized.
        /// </summary>
        /// 
        [OnDeserializing]
        protected void OnDeserializingMethod(StreamingContext context)
        {
            this.parallelOptions = new ParallelOptions();
        }
    }
}