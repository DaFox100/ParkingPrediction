import os
import numpy as np
import pandas as pd
from keras_model_file import  train_model
from sklearn.preprocessing import MinMaxScaler

def train_short_model(model, batch_size, future_steps, test_split, seq_size, name, training_epochs):

    # Create directory for saving graphs
    output_dir = "epoch_results"
    os.makedirs(output_dir, exist_ok=True)

    # Load Data
    data = pd.read_csv("log.csv") 

    # Drop unnecessary columns
    data = data.drop(columns=["Unnamed: 0", 'south density', 'west density', 'north density', 'south compus density'])
    
    # Drop original time columns
    data = data.drop(columns=[data.columns[0]])

    # Train-test split
    train_size = int(len(data) * test_split)
    train_data = data.iloc[:train_size]
    test_data = data.iloc[train_size:]

    scaler = MinMaxScaler() # Scalers are used to normalize the data, this makes it easier for the model to learn the data
    scaler.fit(train_data) # Fit the scaler to the training data

    # Transform the data using the scaler
    train_scaled = pd.DataFrame(scaler.transform(train_data), columns=train_data.columns)
    test_scaled = pd.DataFrame(scaler.transform(test_data), columns=test_data.columns)

    # Sequence Settings, the sequence length is the size of the rolling window that we use to make predictions
    n_feature = data.shape[1] # n_features is the number of inputs to the model, if we want to give the model more context we can increase this value

    # Function to create sequences for multi-step forecasting
    def create_sequences(data, seq_size, future_steps):
        X, y = [], []
        for i in range(len(data) - seq_size - future_steps + 1):
            X.append(data[i:i + seq_size])
            y.append(data[i + seq_size:i + seq_size + future_steps])
        return np.array(X), np.array(y)

    # Create sequences for training and testing
    X_train, Y_train = create_sequences(train_scaled.values, seq_size, future_steps)
    X_test, Y_test = create_sequences(test_scaled.values, seq_size, future_steps)
    train_model(model, X_train, Y_train, X_test, Y_test, batch_size, training_epochs, name)