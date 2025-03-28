# code is mostely from this: https://www.youtube.com/watch?v=S8tpSG6Q2H0
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
import keras as k

from keras.api.layers import Dense, LSTM
from keras.api.models import Sequential


# read the csv using panda
df = pd.read_csv('log.csv',index_col='date',parse_dates=True)
df = df.drop(columns =['Unnamed: 0','south','west','south campus','south density','west density','north density','south compus density'])
# we find the length of the data frame and use the first 156 items for training and the rest of the items (12 months) for testing
log_len = len(df)
df = df[:5000]
# ratio of testing data to verifying data
test_ratio = int(len(df) * 0.9975)
train = df.iloc[:test_ratio] # data we will train from
test = df.iloc[test_ratio:] # data we will test from 

from sklearn.preprocessing import MinMaxScaler

# scale the data we will use from 0 to 1 for RNN, this is different from normalization 
scaler = MinMaxScaler()
scaler.fit(train)
scaled_train = scaler.transform(train)
scaled_test = scaler.transform(test)

from keras_preprocessing.sequence import TimeseriesGenerator
n_input = 32 # previous data inputs are used in next prediction
n_features = 1 # number of data outputs forecast 
generator = TimeseriesGenerator(scaled_train, scaled_train, length=n_input, batch_size=1)

X,y = generator[0]
print(f'Given the Array: \n{X.flatten()}')
print(f'Predict this y: \n {y}')

# define model
model = Sequential()
model.add(LSTM(64, activation = 'relu', input_shape=(n_input,n_features)))
model.add(Dense(1))
model.compile(optimizer='adam',loss = 'mse')

model.fit(generator, epochs = 1)

loss_per_epoch = model.history.history['loss']
plt.plot(range(len(loss_per_epoch)),loss_per_epoch)

import pylab
pylab.show()

last_train_batch = scaled_train[-n_input:]
last_train_batch = last_train_batch.reshape((1, n_input, n_features))

test_predictions = []

first_eval_batch = scaled_train[-n_input:]
current_batch = first_eval_batch.reshape((1, n_input, n_features))

for i in range(len(test)):
    
    # get the prediction value for the first batch
    current_pred = model.predict(current_batch)[0]
    
    # append the prediction into the array
    test_predictions.append(current_pred) 
    
    # use the prediction to update the batch and remove the first value
    current_batch = np.append(current_batch[:,1:,:],[[current_pred]],axis=1)

true_predictions = scaler.inverse_transform(test_predictions)

test['Predictions'] = true_predictions

test.plot(figsize=(14,5))
pylab.show()
from sklearn.metrics import mean_squared_error
from math import sqrt
rmse=sqrt(mean_squared_error(test['north'],test['Predictions']))
print(rmse)

input("Press Enter to continue...")