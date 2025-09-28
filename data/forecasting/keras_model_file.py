import gc
import numpy as np
import tensorflow as tf
from datetime import datetime
from tensorflow import keras
from keras.losses import Loss
from keras.callbacks import ModelCheckpoint

import pandas as pd

from data.forecasting.constants import MODEL_DIRECTORY

physical_devices = tf.config.list_physical_devices('GPU')
if physical_devices:
    # Set memory growth to avoid allocation issues
    policy = tf.keras.mixed_precision.Policy('mixed_float16')
    tf.keras.mixed_precision.set_global_policy(policy)
    tf.config.experimental.set_memory_growth(physical_devices[0], True)
    tf.config.experimental.enable_op_determinism()
    tf.random.set_seed(1)

    # Enable XLA JIT compilation for improved GPU performance
    tf.config.optimizer.set_jit(True)
else:
    print("No GPU found, using CPU")

# ── CUSTOM LOSS CLASS ───────────────────────────────────────────────────────────
class _CustomMSESingleGarage(Loss):
    def __init__(self, garage_no, name="custom_mse_first_four"):
        super().__init__(name=name)
        self.garage_no = garage_no

    @tf.function
    def call(self, y_true, y_pred):
        y_true_slice = y_true[:, :, self.garage_no]
        y_pred_slice = y_pred[:, :, self.garage_no]

        # Apply a soft penalty for predictions above 1.0 (100%)
        over_100_mask = tf.greater(y_pred_slice, 1.0)
        under_100_mask = tf.logical_not(over_100_mask)

        # Penalize predictions above 100% less severely
        error_under_100 = tf.square(y_true_slice - y_pred_slice) * tf.cast(under_100_mask, tf.float32)
        error_over_100 = tf.square(y_true_slice - y_pred_slice) * 0.25 * tf.cast(over_100_mask, tf.float32)

        # Combine the errors
        total_error = error_under_100 + error_over_100
        return tf.reduce_mean(total_error)


def build_model(
    lstm_neurons_list,
    dropout,
    seq_size,
    n_feature,
    future_steps,
    activation,
    garage_no=None,
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.001)):

    inputs = keras.layers.Input(shape=(seq_size, n_feature))
    x = inputs

    attention = keras.layers.Attention()([inputs, inputs])
    x = keras.layers.Concatenate()([inputs, attention])

    for units in lstm_neurons_list:
        shortcut = x  # Store the input as a shortcut for residual connection
        x = keras.layers.LSTM(units, return_sequences=True)(x)
        x = keras.layers.BatchNormalization()(x)
        x = keras.layers.Dropout(dropout)(x)

        # Add residual connection (project shortcut if dimensions differ)
        if shortcut.shape[-1] != x.shape[-1]:
            shortcut = keras.layers.Dense(x.shape[-1])(shortcut)
        x = keras.layers.Add()([x, shortcut])

    # Added a TimeDistributed dense layer for additional feature extraction per timestep
    x = keras.layers.TimeDistributed(keras.layers.Dense(32, activation='relu'))(x)

    x = keras.layers.Flatten()(x)
    outputs = keras.layers.Dense(future_steps * n_feature, activation=activation)(x)
    outputs = keras.layers.Reshape((future_steps, n_feature))(outputs)

    model = keras.Model(inputs=inputs, outputs=outputs)

    # Choose loss function based on whether garage_no is specified
    loss_fn = _CustomMSESingleGarage(garage_no)
    model.compile(
        loss=loss_fn,
        optimizer=optimizer,
        metrics=[tf.keras.metrics.MeanSquaredError()]
    )

    return model

# ── TRAINING FUNCTION ────────────────────────────────────────────────────────────
def train_model(
    model,
    X_train,
    Y_train,
    X_test,
    Y_test,
    batch_size,
    training_epochs,
    name):

    # Define a callback to save the model with the best validation loss
    checkpoint_path = f"{MODEL_DIRECTORY}/{name}_best.keras"
    checkpoint_callback = ModelCheckpoint(
        filepath=checkpoint_path,
        monitor="val_loss",
        save_best_only=True,
        mode="min",
        verbose=0
    )

    reduce_lr = keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.75, patience=5, min_lr=1e-7, verbose=1)

    early_stopping = keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=12,
        restore_best_weights=True,
        verbose=1
    )

    # Add TensorFlow Profiler callback
    log_dir = "logs/profile/" + datetime.now().strftime("%Y%m%d-%H%M%S")
    profiler_callback = tf.keras.callbacks.TensorBoard(
        log_dir=log_dir,
        histogram_freq=1,
        profile_batch="50,60",  # Profile batches 50 to 100
        update_freq="batch"  # Update logs after every batch
    )

    # Convert arrays to np.float32 for efficient transfer
    X_train = np.array(X_train, dtype=np.float32)
    Y_train = np.array(Y_train, dtype=np.float32)
    X_test = np.array(X_test, dtype=np.float32)
    Y_test = np.array(Y_test, dtype=np.float32)

    # Train the model with the callback
    model.fit(
        X_train,
        Y_train,
        validation_data=(X_test, Y_test),
        epochs=training_epochs,
        batch_size=batch_size,
        callbacks=[reduce_lr, checkpoint_callback, early_stopping]
    )

    # Load the best model weights before returning
    model.load_weights(checkpoint_path)

    # Aggressively clean up callbacks and optimizer
    del checkpoint_callback, reduce_lr, early_stopping, profiler_callback
    del X_train, Y_train, X_test, Y_test
    tf.keras.backend.clear_session()
    gc.collect()
    return model
