import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.losses import Loss

garage_names = ["south", "west", "north", "south campus"]

# ── CUSTOM LOSS CLASS ───────────────────────────────────────────────────────────
class CustomMSESingleGarage(Loss):
    def __init__(self, garage_no, name="custom_mse_first_four"):
        super().__init__(name=name)
        self.garage_no = garage_no

    def call(self, y_true, y_pred):
        y_true_slice = y_true[:, :, self.garage_no]
        y_pred_slice = y_pred[:, :, self.garage_no]
        return tf.reduce_mean(tf.square(y_true_slice - y_pred_slice))

reduce_lr = keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=5, min_lr=1e-7, verbose=1)

def CustomMSEFour(y_true,y_pred):
    y_true_slice = y_true[:, :, :4]
    y_pred_slice = y_pred[:, :, :4]
    return tf.reduce_mean(tf.square(y_true_slice - y_pred_slice))

def build_model(
    lstm_neurons_list,
    dropout,
    learning_rate,
    seq_size,
    n_feature,
    future_steps,
    activation,
    garage_no=None):
    
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

    # Choose loss function based on whether garage_no is specified
    if garage_no is not None:
        loss_fn = CustomMSESingleGarage(garage_no)
    else:
        loss_fn = CustomMSEFour

    model.compile(
        loss=loss_fn,
        optimizer=keras.optimizers.Lion(learning_rate=learning_rate),
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
    model.fit(
        X_train, Y_train,
        validation_data=(X_test, Y_test),
        epochs=training_epochs,
        batch_size=batch_size,
        callbacks=[reduce_lr])
    model.save_weights(f"keras_models/{name}.weights.h5")
