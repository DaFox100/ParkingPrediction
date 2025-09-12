import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.losses import Loss
from keras.callbacks import ModelCheckpoint
import warnings
from keras.mixed_precision import set_global_policy
set_global_policy('mixed_float16')

from data.forecasting.constants import (
    MODEL_DIRECTORY
)

warnings.filterwarnings("ignore", category=UserWarning, module="keras.saving")

# Enable mixed precision

# ── CUSTOM LOSS CLASS ───────────────────────────────────────────────────────────
class _CustomMSESingleGarage(Loss):
    def __init__(self, garage_no, name="custom_mse_first_four"):
        super().__init__(name=name)
        self.garage_no = garage_no

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

def _CustomMSEFour(y_true,y_pred):
    y_true_slice = y_true[:, :, :4]
    y_pred_slice = y_pred[:, :, :4]
    return tf.reduce_mean(tf.square(y_true_slice - y_pred_slice))

class CustomLossMultiPoint(Loss):
    def __init__(self, weight_decay=0.1, name="custom_loss_multi_point"):
        super().__init__(name=name)
        self.weight_decay = weight_decay

    def call(self, y_true, y_pred):
        # Calculate the squared error for each time step
        squared_errors = tf.square(y_true - y_pred)

        # Apply a weighting factor that increases with the time step index
        time_weights = tf.range(1, tf.shape(squared_errors)[1] + 1, dtype=tf.float32)
        time_weights = tf.expand_dims(time_weights, axis=0)  # Match batch dimension
        time_weights = tf.expand_dims(time_weights, axis=-1)  # Match feature dimension

        # Weighted mean squared error
        weighted_squared_errors = squared_errors * time_weights
        return tf.reduce_mean(weighted_squared_errors)

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

    for units in lstm_neurons_list:
        x = keras.layers.LSTM(units, return_sequences=True)(x)
        x = keras.layers.BatchNormalization()(x)
        x = keras.layers.Dropout(dropout)(x)

    x = keras.layers.Flatten()(x)
    outputs = keras.layers.Dense(future_steps * n_feature, activation=activation)(x)
    outputs = keras.layers.Reshape((future_steps, n_feature))(outputs)

    model = keras.Model(inputs=inputs, outputs=outputs)

    #Choose loss function based on whether garage_no is specified
    if garage_no is not None:
        loss_fn = _CustomMSESingleGarage(garage_no)
    else:
        loss_fn = _CustomMSEFour
    # Use Huber loss
    # loss_fn = tf.keras.losses.Huber()
    model.compile(
        loss=loss_fn,
        optimizer=optimizer,
        metrics=[tf.keras.metrics.MeanSquaredError()])

    return model

# ── TRAINING FUNCTION ────────────────────────────────────────────────────────────
def train_model(
    model,
    X_train, Y_train,
    X_test,  Y_test,
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

    reduce_lr = keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.75, patience=3, min_lr=1e-7, verbose=1)

    early_stopping = keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=6,
        restore_best_weights=True,
        verbose=1
    )

    # Train the model with the callback
    model.fit(
        X_train, Y_train,
        validation_data=(X_test, Y_test),
        epochs=training_epochs,
        batch_size=batch_size,
        callbacks=[reduce_lr, checkpoint_callback, early_stopping])

    # Load the best model weights before returning
    model.load_weights(checkpoint_path)
    return model
