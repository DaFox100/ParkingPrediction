import numpy as np
import pandas as pd
import tensorflow as tf
from datetime import datetime
import gc
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from data.forecasting.data_functions import add_cyclical_time_encoding, add_event_impact_features, add_instruction_days, load_data_from_mongodb
from keras.callbacks import ModelCheckpoint

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow C++ logs (including register spill warnings)

from data.forecasting.constants import (
    ENABLE_TIME_ENCODING,
    ENABLE_INSTR_DAY,
    ENABLE_EVENT_ENCODING,
    MODEL_DIRECTORY,
    LOGS_DIRECTORY,
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
    plt.show()

def train_long_model_with_generator(model, batch_size, future_steps, test_split, seq_size, name, training_epochs, data):
    # Process the data
    if ENABLE_INSTR_DAY:
        data = add_instruction_days(data)
    if ENABLE_TIME_ENCODING:
        data = add_cyclical_time_encoding(data)
    if ENABLE_EVENT_ENCODING:
        data = add_event_impact_features(data)

    data = data.drop(columns=["date"]).copy()

    # Train-test split
    train_size = int(len(data) * test_split)
    train_data = data.iloc[:train_size]
    test_data = data.iloc[train_size:]

    scaler = MinMaxScaler()
    scaler.fit(train_data)

    train_scaled = scaler.transform(train_data)
    test_scaled = scaler.transform(test_data)

    # Create data generators
    train_generator = DataGenerator(train_scaled, train_scaled, batch_size, seq_size, future_steps)
    test_generator = DataGenerator(test_scaled, test_scaled, batch_size, seq_size, future_steps)

    # Add TensorFlow Profiler callback
    # log_dir = "logs/profile/" + datetime.now().strftime("%Y%m%d-%H%M%S")
    # profiler_callback = tf.keras.callbacks.TensorBoard(
    #     log_dir=log_dir,
    #     histogram_freq=1,
    #     profile_batch="90,100",  # Profile batches 50 to 100
    #     update_freq="batch"  # Update logs after every batch
    # )

    callbacks = [
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.75, patience=5, min_lr=1e-7, verbose=1),
        tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=12, restore_best_weights=True, verbose=1),
        # profiler_callback
    ]

    try:
        # Train the model
        model.fit(
            train_generator,
            validation_data=test_generator,
            epochs=training_epochs,
            callbacks=callbacks
        )

        # Evaluate the model
        loss = model.evaluate(test_generator, verbose=0)
    finally:
        # Clean up
        del model, train_generator, test_generator, callbacks, data, train_data, test_data, train_scaled, test_scaled
        tf.keras.backend.clear_session()
        gc.collect()

    return loss

def train_long_model(model, batch_size, future_steps, test_split, seq_size, name, training_epochs, data):
    # Process the data
    if ENABLE_INSTR_DAY:
        data = add_instruction_days(data)
    if ENABLE_TIME_ENCODING:
        data = add_cyclical_time_encoding(data)
    if ENABLE_EVENT_ENCODING:
        data = add_event_impact_features(data)
    plot_encoded_data(data)
    data = data.drop(columns=["date"]).copy()

    # Train-test split
    train_size = int(len(data) * test_split)
    train_data = data.iloc[:train_size]
    test_data = data.iloc[train_size:]

    scaler = MinMaxScaler()
    scaler.fit(train_data)

    train_scaled = scaler.transform(train_data)
    test_scaled = scaler.transform(test_data)

    # Create data generators
    train_generator = DataGenerator(train_scaled, train_scaled, batch_size, seq_size, future_steps)
    test_generator = DataGenerator(test_scaled, test_scaled, batch_size, seq_size, future_steps)

    # log_dir = "logs/profile/" + datetime.now().strftime("%Y%m%d-%H%M%S")
    # profiler_callback = tf.keras.callbacks.TensorBoard(
    #     log_dir=log_dir,
    #     histogram_freq=1,
    #     profile_batch="90,100",  # Profile batches 50 to 100
    #     update_freq="batch"  # Update logs after every batch
    # )

    checkpoint_path = f"{MODEL_DIRECTORY}/{name}_best.keras"
    checkpoint_callback = ModelCheckpoint(
        filepath=checkpoint_path,
        monitor="val_loss",
        save_best_only=True,
        mode="min",
        verbose=0
    )

    callbacks = [
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.75, patience=5, min_lr=1e-7, verbose=0),
        tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=6, restore_best_weights=True, verbose=0),
        # profiler_callback
        checkpoint_callback
    ]

    try:
        # Train the model
        model.fit(
            train_generator,
            validation_data=test_generator,
            epochs=training_epochs,
            callbacks=callbacks
        )

        # Evaluate the model
        loss = model.evaluate(test_generator, verbose=0)
    finally:
        # Clean up
        del model, train_generator, test_generator, callbacks, data, train_data, test_data, train_scaled, test_scaled
        tf.keras.backend.clear_session()
        gc.collect()
    # Define a callback to save the model with the best validation loss
    return loss

class DataGenerator(tf.keras.utils.Sequence):
    def __init__(self, data, labels, batch_size, seq_size, future_steps):
        self.data = data
        self.labels = labels
        self.batch_size = batch_size
        self.seq_size = seq_size
        self.future_steps = future_steps
        self.indices = np.arange(len(data) - seq_size - future_steps + 1)

    def __len__(self):
        # Number of batches per epoch
        return int(np.ceil(len(self.indices) / self.batch_size))

    def __getitem__(self, index):
        # Generate one batch of data
        batch_indices = self.indices[index * self.batch_size:(index + 1) * self.batch_size]
        X, y = [], []
        for i in batch_indices:
            X.append(self.data[i:i + self.seq_size])
            y.append(self.labels[i + self.seq_size:i + self.seq_size + self.future_steps])
        return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)

    def on_epoch_end(self):
        # Shuffle indices after each epoch
        np.random.shuffle(self.indices)

def plot_encoded_data(data: pd.DataFrame):
    """
    Display a graph of the dataset with encodings over time.

    Parameters:
        data (pd.DataFrame): The dataset with added encodings.
    """
    if data.empty:
        print("The dataset is empty. No data to display.")
        return

    # Plot each column in the dataset over time
    plt.figure(figsize=(15, 8))
    for column in data.columns:
        if column != 'date':  # Exclude the date column from being plotted as a series
            plt.plot(data['date'], data[column], label=column)

    plt.xlabel('Date')
    plt.ylabel('Values')
    plt.title('Encoded Data Over Time')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"{LOGS_DIRECTORY}/encoded_data_over_time.svg")