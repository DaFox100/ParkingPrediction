import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from data.forecasting.keras_model_file import train_model
from sklearn.preprocessing import MinMaxScaler
from data.forecasting.data_functions import add_cyclical_time_encoding, add_event_impact_features,add_instruction_days, load_data_from_mongodb

from data.forecasting.constants import (
    ENABLE_TIME_ENCODING,
    ENABLE_INSTR_DAY,
    ENABLE_EVENT_ENCODING
)



def plot_mongo_data(df):
    """
    Plots the garage occupancy data loaded from MongoDB.
    Expects columns: 'date', 'south', 'west', 'north', 'south campus'
    """
    plt.figure(figsize=(15, 6))
    for col in ['south', 'west', 'north', 'south campus']:
        plt.plot(df['date'], df[col], label=col)
    plt.xlabel('Date')
    plt.ylabel('Occupancy (normalized)')
    plt.title('Garage Occupancy Over Time')
    plt.legend()
    plt.tight_layout()
    # plt.show()

def train_long_model(model, batch_size, future_steps, test_split, seq_size, name, training_epochs, data):
    # plot_mongo_data(data)
    # Process the data
    if ENABLE_INSTR_DAY:
        data = add_instruction_days(data)
    if ENABLE_TIME_ENCODING:
        data = add_cyclical_time_encoding(data)
    if ENABLE_EVENT_ENCODING:
        data = add_event_impact_features(data)
    # Prepare data for long-term model (includes positional encoding features)
    data = data.drop(columns=["date"]).copy()
    
    # Train-test split
    train_size = int(len(data) * test_split)
    train_data = data.iloc[:train_size]
    test_data = data.iloc[train_size:]

    scaler = MinMaxScaler()
    scaler.fit(train_data)  # Fit on training data only

    # Transform both train and test using the same scaler
    train_scaled = pd.DataFrame(scaler.transform(train_data), columns=train_data.columns)
    test_scaled = pd.DataFrame(scaler.transform(test_data), columns=test_data.columns)

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

    # Train the model
    train_model(model, X_train, Y_train, X_test, Y_test, batch_size, training_epochs, name)

    # Evaluate the model on the test set to get validation loss
    loss = model.evaluate(X_test, Y_test, batch_size=batch_size, verbose=0)
    return loss 