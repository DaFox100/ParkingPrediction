import os
import sys
import joblib
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from typing import List, Tuple, Any, Dict, Optional, Union
from keras import Model
from datetime import datetime


# Try to import using the full path first, fall back to local imports if that fails
try:
    from data.forecasting.keras_model_file import build_model
    from data.forecasting.short_term_model import train_short_model
    from data.forecasting.long_term_model import train_long_model
    from data.forecasting.data_functions import add_cyclical_time_encoding, add_event_impact_features,add_instruction_days, load_data_from_mongodb
    from data.forecasting import utils
    from data.forecasting.constants import (
        MODEL_DIRECTORY,
        GARAGE_NAMES,
        LONG_SEQ,
        LONG_FUTURE_STEPS,
        SHORT_SEQ,
        SHORT_FUTURE_STEPS,
        ENABLE_TIME_ENCODING,
        ENABLE_INSTR_DAY,
        ENABLE_EVENT_ENCODING
    )
except ImportError:
    # Fall back to local imports if the full path imports fail
    from keras_model_file import build_model
    from short_term_model import train_short_model
    from long_term_model import train_long_model
    import utils
    from constants import (
        MODEL_DIRECTORY,
        LOGS_DIRECTORY,
        GARAGE_NAMES,
        LONG_SEQ,
        LONG_FUTURE_STEPS,
        SHORT_SEQ,
        SHORT_FUTURE_STEPS,
        ENABLE_TIME_ENCODING,
        ENABLE_INSTR_DAY,
        ENABLE_EVENT_ENCODING
    )
# control flags  [True,True,True,True] [False,False,False,False] (for easy copy paste)
LONG_TRAINING_MASK: List[bool]      = [False,False,False,False]
SHORT_TRAINING_MASK: List[bool]     = [False,False,False,False]

LONG_HYPER_PARAMS: Dict[str, Dict[str, Any]] = {
    "south": {
        "lstm_neurons_list": [192, 32, 192],
        "dropout": 0.1,
        "learning_rate": 2e-5,
        "activation": "linear",},
    "west": {
        "lstm_neurons_list": [192, 32, 192],
        "dropout": 0.1,
        "learning_rate": 2e-5,
        "activation": "linear",},
    "north": {
        "lstm_neurons_list": [192, 32, 192],
        "dropout": 0.1,
        "learning_rate": 2e-5,
        "activation": "linear",},
    "south_campus": {
        "lstm_neurons_list": [512, 64, 512],
        "dropout": 0.1,
        "learning_rate": 1e-5,
        "activation": "linear",}
}

SHORT_HYPER_PARAMS: Dict[str, Dict[str, Any]] = {
    "south": {
        "lstm_neurons_list": [64, 16, 64],
        "dropout": 0.10,
        "learning_rate": 1e-4,
        "activation": "celu",},
    "west": {
        "lstm_neurons_list": [64, 16, 64],
        "dropout": 0.10,
        "learning_rate": 1e-4,
        "activation": "celu",},
    "north": {
        "lstm_neurons_list": [64, 16, 64],
        "dropout": 0.10,
        "learning_rate": 1e-4,
        "activation": "celu",},
    "south_campus": {
        "lstm_neurons_list": [64, 16, 64],
        "dropout": 0.10,
        "learning_rate": 1e-4,
        "activation": "celu",}
}

# long model hyperparameters
def _build_long_model(garage: str, feature_dim: int) -> Model:
    # look up this garage's hyperparams, fall back to first dict entry if missing
    params = LONG_HYPER_PARAMS.get(
        garage,
        next(iter(LONG_HYPER_PARAMS.values()))
    )
    return build_model(
        lstm_neurons_list = params["lstm_neurons_list"],
        dropout           = params["dropout"],
        learning_rate     = params["learning_rate"],
        seq_size          = LONG_SEQ,
        activation        = params.get("activation", "linear"),
        n_feature         = feature_dim,
        future_steps      = LONG_FUTURE_STEPS,
        garage_no         = garage
    )
    
# short model hyperparameters 
def _build_short_model(garage: str, feature_dim: int) -> Model:
    params = SHORT_HYPER_PARAMS.get(
        garage,
        next(iter(SHORT_HYPER_PARAMS.values()))
    )
    return build_model(
        lstm_neurons_list = params["lstm_neurons_list"],
        dropout           = params["dropout"],
        learning_rate     = params["learning_rate"],
        seq_size          = SHORT_SEQ,
        activation        = params.get("activation", "celu"),
        n_feature         = feature_dim,
        future_steps      = SHORT_FUTURE_STEPS,
        garage_no         = garage
    )
    
def _train_long(garage: str, model: Model) -> None:
    print(f"training long model: {garage}")
    train_long_model(
        model=model,
        training_epochs=10,
        batch_size=32,
        future_steps=LONG_FUTURE_STEPS,
        test_split=0.80,
        seq_size=LONG_SEQ,
        name=f"long_model_{garage}"
    )


def _train_short(garage: str, model: Model) -> None:
    print(f"training short model: {garage}")
    train_short_model(
        model=model,
        training_epochs=25,
        batch_size=32,
        future_steps=SHORT_FUTURE_STEPS,
        test_split=0.8,
        seq_size=SHORT_SEQ,
        name=f"short_model_{garage}"
    )
 
def load_or_fit_scaler(scaler_path, data: pd.DataFrame) -> MinMaxScaler:
    """
    Loads a persisted MinMaxScaler from scaler_path if available,
    otherwise fits a new scaler on the provided data and persists it.
    """
    if scaler_path.exists():
        scaler = joblib.load(scaler_path)
    else:
        scaler = MinMaxScaler().fit(data)
        joblib.dump(scaler, scaler_path)
    return scaler


def _make_prediction(
    data: pd.DataFrame, short_data: pd.DataFrame,
    long_models: List[Model], short_models: List[Model],
    short_dim: int, long_dim: int
) -> np.ndarray:

    # Use persisted scalers instead of fitting new ones every time;
    # these files should have been created during model training.
    scaler_long_path = MODEL_DIRECTORY / "scaler_long.pkl"
    scaler_short_path = MODEL_DIRECTORY / "scaler_short.pkl"
    scaler_long = load_or_fit_scaler(scaler_long_path, data)
    scaler_short = load_or_fit_scaler(scaler_short_path, short_data)

    scaled_long = pd.DataFrame(
        scaler_long.transform(data),
        columns=data.columns
    )
    scaled_short = pd.DataFrame(
        scaler_short.transform(short_data),
        columns=short_data.columns
    )

    try:
        for i, garage in enumerate(GARAGE_NAMES):
            long_models[i].load_weights(
                MODEL_DIRECTORY / f"long_model_{garage}.weights.h5"
            )
            short_models[i].load_weights(
                MODEL_DIRECTORY / f"short_model_{garage}.weights.h5"
            )
    except Exception:
        print("Could not load weights, please verify you have existing weight files, exiting.")
        exit(-1)

    # prepare batches
    short_batch = scaled_short.values[-SHORT_SEQ:].reshape(1, SHORT_SEQ, short_dim)
    long_batch  = scaled_long.values[-LONG_SEQ:].reshape(1, LONG_SEQ, long_dim)

    long_preds = []
    short_preds = []
    for i, garage in enumerate(GARAGE_NAMES):
        lp = long_models[i].predict(long_batch, verbose=0)[0]
        sp = short_models[i].predict(short_batch, verbose=0)[0]
        long_preds.append(np.clip(scaler_long.inverse_transform(lp)[:, i], 0, 1))
        short_preds.append(np.clip(scaler_short.inverse_transform(sp)[:, i], 0, 1))

    # combine predictions from both models
    fut_len = len(long_preds[0])
    sh_len = len(short_preds[0])
    t = np.arange(sh_len)
    w_short = 0.5 * (1 + np.cos(np.pi * t / (sh_len - 1)))
    w_long = 1.0 - w_short

    combined = np.zeros((fut_len, len(GARAGE_NAMES)))
    for i in range(len(GARAGE_NAMES)):
        combined[:sh_len, i] = w_short * short_preds[i] + w_long * long_preds[i][:sh_len]
        combined[sh_len:, i] = long_preds[i][sh_len:]
    return combined


def calculate_prediction(forecast_start: datetime, hours: int = 24) -> List[float]:
    extra_long_data = 0

    data: pd.DataFrame = load_data_from_mongodb(forecast_start)
    short_data: pd.DataFrame = data.drop(columns=["date"]).copy() # Keep a copy of the raw density data (without date)
    
    # Process the data
    if ENABLE_INSTR_DAY:
        data = add_instruction_days(data)
        extra_long_data += 2
    if ENABLE_TIME_ENCODING:
        data = add_cyclical_time_encoding(data)
        extra_long_data += 10
    if ENABLE_EVENT_ENCODING:
        data = add_event_impact_features(data)
        extra_long_data += 4
        

    # data: pd.DataFrame = load_data()
    long_garage_models: List[Model] = []
    short_garage_models: List[Model] = []
    
    long_data: pd.DataFrame = data.drop(columns=['date']).copy()
        
    # Define parameters for long and short models
    long_feature_shape: int = short_data.shape[1] + extra_long_data
    short_feature_shape: int = short_data.shape[1]
    
    # remember the models will not load correctly if you changes this and don't re-train
    for garage_no in range(len(GARAGE_NAMES)):
        long_garage_models.append(_build_long_model(garage_no, long_feature_shape))
        short_garage_models.append(_build_short_model(garage_no, short_feature_shape))
    
    # Train models if the flag is true
    for garage_no, garage in enumerate(GARAGE_NAMES, start=0):
        if LONG_TRAINING_MASK[garage_no]:
            _train_long(garage, long_garage_models[garage_no])
        if SHORT_TRAINING_MASK[garage_no]:
            _train_short(garage, short_garage_models[garage_no])
    
    prediction: np.ndarray = _make_prediction(long_data, short_data, long_garage_models, short_garage_models, short_feature_shape, long_feature_shape)
    start_time: pd.Timestamp = pd.Timestamp(forecast_start)
    end_time: pd.Timestamp = pd.Timestamp(forecast_start + pd.Timedelta(hours=hours))
    values = utils.plot_prediction(prediction, short_data, data, start_time, end_time)
    return values

if __name__ == "__main__":
    values = calculate_prediction(datetime(2025, 5, 3, 0, 0))
    print_string = ""
    for list in values:
        print_string += "\nGarage " + str(values.index(list)) + ": "
        for i in range(len(list)):
            if i % 24 == 0:
                print_string += "\n Day " + str(int((i / 24)) + 1) + ": "
            print_string += str(list[i]) + " "
    print(print_string)
