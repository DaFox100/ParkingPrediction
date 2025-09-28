import numpy as np
import pandas as pd
import tensorflow as tf
from datetime import datetime
from data_functions import load_data_from_mongodb, add_cyclical_time_encoding, add_event_impact_features, add_instruction_days
from constants import (
    GARAGE_NAMES,
    LONG_SEQ,
    LONG_FUTURE_STEPS,
    ENABLE_TIME_ENCODING,
    ENABLE_INSTR_DAY,
    ENABLE_EVENT_ENCODING
)
from keras_model_file import build_model
from keras_tuner.tuners import Hyperband

# Load and preprocess data
def get_preprocessed_data():
    data = load_data_from_mongodb(datetime.now())
    if ENABLE_INSTR_DAY:
        data = add_instruction_days(data)
    if ENABLE_TIME_ENCODING:
        data = add_cyclical_time_encoding(data)
    if ENABLE_EVENT_ENCODING:
        data = add_event_impact_features(data)
    data = data.drop(columns=["date"], errors="ignore")
    return data

def model_builder(hp):
    # Hyperparameter search space
    lstm_layers = hp.Int('lstm_layers', min_value=1, max_value=5, step=1)
    lstm_neurons_list = [hp.Int(f'lstm_neurons_{i}', min_value=16, max_value=512, step=16) for i in range(lstm_layers)]
    dropout = hp.Float('dropout', min_value=0.05, max_value=0.75, step=0.05)
    learning_rate = hp.Float('learning_rate', min_value=1e-4, max_value=5e-3, sampling='log')
    activation = hp.Choice('activation', ["celu", "elu", "gelu", "hard_sigmoid", "hard_tanh", "hard_silu","leaky_relu", "linear", "mish", "relu", "silu"])
    optimizer_name = hp.Choice('optimizer', ["nadam", "adam", "rmsprop", "lion", "adamax", "adamw"])
    batch_size = hp.Choice('batch_size', [256, 512, 1024])

    # Select optimizer
    optimizer = None
    if optimizer_name == "adam":
        optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)
    elif optimizer_name == "adamw":
        optimizer = tf.keras.optimizers.AdamW(learning_rate=learning_rate)
    elif optimizer_name == "nadam":
        optimizer = tf.keras.optimizers.Nadam(learning_rate=learning_rate)
    elif optimizer_name == "rmsprop":
        optimizer = tf.keras.optimizers.RMSprop(learning_rate=learning_rate)
    elif optimizer_name == "lion":
        optimizer = tf.keras.optimizers.Lion(learning_rate=learning_rate)
    elif optimizer_name == "adamax":
        optimizer = tf.keras.optimizers.Adamax(learning_rate=learning_rate)
    else:
        optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)

    # Use the build_model function from keras_model_file
    model = build_model(
        lstm_neurons_list=lstm_neurons_list,
        dropout=dropout,
        seq_size=LONG_SEQ,
        n_feature=4 + (2 if ENABLE_INSTR_DAY else 0) + (10 if ENABLE_TIME_ENCODING else 0) + (4 if ENABLE_EVENT_ENCODING else 0),
        future_steps=LONG_FUTURE_STEPS,
        activation=activation,
        garage_no=0,  # You can loop over garages for full search
        optimizer=optimizer
    )
    return model

def run_hyperband():
    data = get_preprocessed_data()
    # Prepare sequences for LSTM
    def create_sequences(data, seq_size, future_steps):
        X, y = [], []
        for i in range(len(data) - seq_size - future_steps + 1):
            X.append(data.iloc[i:i + seq_size].values)
            y.append(data.iloc[i + seq_size:i + seq_size + future_steps].values)
        return np.array(X), np.array(y)

    X, Y = create_sequences(data, LONG_SEQ, LONG_FUTURE_STEPS)
    train_size = int(len(X) * 0.8)
    X_train, Y_train = X[:train_size], Y[:train_size]
    X_val, Y_val = X[train_size:], Y[train_size:]

    tuner = Hyperband(
        model_builder,
        objective='val_loss',
        max_epochs=20,
        factor=3,
        directory='hyperband_results',
        project_name='parking_forecast'
    )

    tuner.search(X_train, Y_train, epochs=20, validation_data=(X_val, Y_val))
    best_hps = tuner.get_best_hyperparameters(num_trials=1)[0]
    print("Best hyperparameters:", best_hps.values)
    return best_hps

if __name__ == "__main__":
    run_hyperband()
