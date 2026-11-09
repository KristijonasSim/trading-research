# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean Algorithmic Trading Engine v2.0. Copyright 2020 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import tensorflow as tf
from tensorflow.keras.layers import Input, Conv1D, Dense, Lambda, Flatten, Concatenate
from tensorflow.keras import Model
from tensorflow.keras import metrics
from tensorflow.keras.losses import CategoricalCrossentropy
from tensorflow.keras import utils
from sklearn.preprocessing import StandardScaler
import numpy as np
import math

# varibles (aka features in ML lingo) used to make predictions
input_vars = ['open', 'high', 'low', 'close', 'volume']  

class Direction:
    '''Constants used for labeling price movements'''
    # labels must be integers because Keras (and most ML Libraries) 
    #   only work with numbers
    
    UP = 0
    DOWN = 1
    STATIONARY = 2

class MyTemporalCNN:
    '''Temporal Convolutional Neural Network Model built upon Keras'''
    
    # the name describes the architecture of the Neural Network model
    #   Temporal refers to the fact the layers are separated temporally into three regions
    #   Convolutional refers to the fact Convolutional layers are used to extract features

    def __init__(self, n_tsteps = 15):
        # n_tsteps = number of time steps in time series for one input/prediction
        self.n_tsteps = n_tsteps
        
        self.scaler = StandardScaler()  # used for Feature Scaling
        
        self.__CreateModel()
        
    def __CreateModel(self):
        '''Creates the neural network model'''
        
        inputs = Input(shape=(self.n_tsteps, len(input_vars)))
        
        # extract our features using a Convolutional layers, hence "CNN"
        feature_extraction = Conv1D(30, 4, activation='relu')(inputs)
        
        # split layer into three regions based on time, hence "Temporal"
        long_term = Lambda( lambda x: tf.split(x, num_or_size_splits=3, axis=1)[0])(feature_extraction)
        mid_term = Lambda( lambda x: tf.split(x, num_or_size_splits=3, axis=1)[1])(feature_extraction)
        short_term = Lambda( lambda x: tf.split(x, num_or_size_splits=3, axis=1)[2])(feature_extraction)
        
        long_term_conv = Conv1D(1, 1, activation='relu')(long_term)
        mid_term_conv = Conv1D(1, 1, activation='relu')(mid_term)
        short_term_conv = Conv1D(1, 1, activation='relu')(short_term)
        
        # combine three layers back into one
        combined = Concatenate(axis=1)([long_term_conv, mid_term_conv, short_term_conv])
        
        # flattening is required since our input is a 2D matrix
        flattened = Flatten()(combined)
        
        # 1 output neuron for each class (Up, Stationary, Down --- see Direction class)
        outputs = Dense(3, activation='softmax')(flattened)
        
        # specify input and output layers of our model
        self.model = Model(inputs=inputs, outputs=outputs)
        
        # compile our model
        self.model.compile(optimizer='adam',
                      loss=CategoricalCrossentropy(from_logits=True))
    
    def __PrepareData(self, data, rolling_avg_window_size=5, stationary_threshold=.0001):
        '''Prepares the data for a format friendly for our model'''
        
        # rolling_avg_window_size = window size for the future mid prices to average, 
        #   this average is what the model wants to predict
        # stationary_threshold = maximum change of movement to be considered stationary 
        #   for the average mid price stated above 
        
        df = data[input_vars]
        shift = -(rolling_avg_window_size-1)
    
        # function we will use to label our data (used in line )
        def label_data(row):
            if row['close_avg_change_pct'] > stationary_threshold:
                return Direction.UP
            elif row['close_avg_change_pct'] < -stationary_threshold:
                return Direction.DOWN
            else:
                return Direction.STATIONARY
            
        # compute the % change in the average of the close of the future 5 time steps
        #   at each time step
        df['close_avg'] = df['close'].rolling(window=rolling_avg_window_size).mean().shift(shift) 
        df['close_avg_change_pct'] = (df['close_avg'] - df['close']) / df['close']
         
        # label data based on direction,
        # axis=1 signifies a row-wise operation (axis=0 is col-wise)
        df['movement_labels'] = df.apply(label_data, axis=1)
        
        # lists to store each 2D input matrix and the corresponding label
        data = []
        labels = []
        
        for i in range(len(df)-self.n_tsteps+1+shift):
            label = df['movement_labels'].iloc[i+self.n_tsteps-1]
            data.append(df[input_vars].iloc[i:i+self.n_tsteps].values)
            labels.append(label)
        
        data = np.array(data)
        
        # temporarily reshape data to 2D,
        #   necessary because sklearn only works wtih 2D data
        dim1, dim2, dim3 = data.shape
        data = data.reshape(dim1*dim2, dim3)
        
        # fit our scaler and transform our data in one method call
        data = self.scaler.fit_transform(data)
        
        # return data to original shape
        data = data.reshape(dim1, dim2, dim3)
        
        # Keras needs dummy matrices for classification problems, 
        #   hence the need for to_categorical()
        #   num classes ensures our dummy matrix has 3 columns, 
        #   one for each label (Up, Down, Stationary)
        return data, utils.to_categorical(labels, num_classes=3)

    def Train(self, data):
        '''Trains the model'''
        
        data, labels = self.__PrepareData(data)
        self.model.fit(data, labels, epochs=20)
        
    def Predict(self, input_data):
        '''Makes a prediction on the direction of the future stock price'''
        
        input_data = self.scaler.transform(input_data.fillna(method='ffill').values)
        prediction = self.model.predict(input_data[np.newaxis, :])[0]
        direction = np.argmax(prediction)
        confidence = prediction[direction]
        return direction, confidence