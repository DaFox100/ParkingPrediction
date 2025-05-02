import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from typing import List, Tuple, Any, Dict, Optional, Union
from keras import Model
from pathlib import Path

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
    SHORT_FUTURE_STEPS
)

# control flags  [True,True,True,True] [False,False,False,False] (for easy copy paste)
LONG_TRAINING_MASK: List[bool]      = [False,False,False,False]
SHORT_TRAINING_MASK: List[bool]     = [False,False,False,False]
ENABLE_TIME_ENCODING: bool          = True
ENABLE_INSTR_DAY: bool              = True
ENABLE_INSTR_NEXT_DAY: bool         = True

# counting the extra features added to the long model
extra_long_data: int = 0

# Load and preprocess log.csv data
def load_data() -> pd.DataFrame:
    data: pd.DataFrame = pd.read_csv(LOGS_DIRECTORY / "log.csv")
    data = data[-1000:] # WHY IS THIS NESSESSARY TO WORK, I DON'T KNOW
    data = data.drop(columns=["Unnamed: 0", "south density", "west density", "north density", "south compus density"])
    return data

# Load the instruction days CSV and prepare it
def load_instruction_days(data: pd.DataFrame) -> pd.DataFrame:
    global extra_long_data
    instruction_days_df: pd.DataFrame = pd.read_csv(f"{LOGS_DIRECTORY}/sjsu_instruction_days.csv")
    instruction_days_df["Date"] = pd.to_datetime(instruction_days_df["Date"]).dt.date
    instruction_days_df.rename(columns={"Instruction_Day": "instruction_day"}, inplace=True)
    # Prepare the log data
    data['date'] = pd.to_datetime(data['date'])
    data['date_only'] = data['date'].dt.date
    # Merge original instruction day flag
    data = pd.merge(data, instruction_days_df, how="left", left_on="date_only", right_on="Date")
    data["instruction_day"] = data["instruction_day"].fillna(False)
    
    if ENABLE_INSTR_NEXT_DAY: 
        # Add a column for the previous day that maps to the next day's instruction flag
        next_day_instr_df: pd.DataFrame = instruction_days_df.copy()
        next_day_instr_df["Date"] = next_day_instr_df["Date"] - pd.Timedelta(days=1)
        next_day_instr_df.rename(columns={"instruction_day": "next_day_instruction"}, inplace=True)
         # Merge next-day instruction flag
        data = pd.merge(data, next_day_instr_df, how="left", left_on="date_only", right_on="Date")
        data["next_day_instruction"] = data["next_day_instruction"].fillna(False)
        data.drop(columns=["Date_x", "Date_y", "date_only"], inplace=True)
        extra_long_data += 1
    else: # Drop temporary columns
        data.drop(columns=["Date", "date_only"], inplace=True)
        
    extra_long_data += 1
        
    return data

#cyclical time encodings
# Prepare data for long-term model (includes time encoding features)
def cyclical_time_encoding(data: pd.DataFrame) -> pd.DataFrame:
    ts: pd.Series = data['date']
    data['month_sin']       = np.sin(2 * np.pi * ((ts.dt.month - 1) / 12))
    data['month_cos']       = np.cos(2 * np.pi * ((ts.dt.month - 1) / 12))
    data['day_sin']         = np.sin(2 * np.pi * (ts.dt.day / 31))
    data['day_cos']         = np.cos(2 * np.pi * (ts.dt.day / 31))
    data['day_of_week_sin'] = np.sin(2 * np.pi * (ts.dt.dayofweek / 7))
    data['day_of_week_cos'] = np.cos(2 * np.pi * (ts.dt.dayofweek / 7))
    data['hour_sin']        = np.sin(2 * np.pi * (ts.dt.hour / 24))
    data['hour_cos']        = np.cos(2 * np.pi * (ts.dt.hour / 24))
    data['minute_sin']      = np.sin(2 * np.pi * (ts.dt.minute / 60))
    data['minute_cos']      = np.cos(2 * np.pi * (ts.dt.minute / 60))
    global extra_long_data
    extra_long_data += 10
    
    return data.copy()

# long model hyperparameters
def _build_long_model(garage_no: int, shape: int) -> Model:
    return build_model(
    lstm_neurons_list=[192,32,192],
    dropout=0.1,
    learning_rate=2e-5,
    seq_size=LONG_SEQ,
    activation='linear',
    n_feature=shape,
    future_steps=LONG_FUTURE_STEPS,
    garage_no=garage_no)
    
# short model hyperparameters 
def _build_short_model(garage_no: int, shape: int) -> Model:
    return build_model(
    lstm_neurons_list=[64,16,64],
    dropout=0.1,
    learning_rate=1e-4,
    seq_size=SHORT_SEQ,
    activation='celu',
    n_feature=shape,
    future_steps=SHORT_FUTURE_STEPS,
    garage_no=garage_no)
    
def _train_long(garage: str, long_garage_model: Model) -> None:
    print(f"training long model: {garage}")
    train_long_model(
    model=long_garage_model,
    training_epochs=35,
    batch_size=512,
    future_steps=LONG_FUTURE_STEPS,
    test_split=0.8,
    seq_size=LONG_SEQ,
    name=f"long_model_{garage}")

def _train_short(garage: str, short_garage_model: Model) -> None:
    print(f"training short model: {garage}")
    train_short_model(
    model=short_garage_model,
    training_epochs=25,
    batch_size=32,
    future_steps=SHORT_FUTURE_STEPS,
    test_split=0.8,
    seq_size=SHORT_SEQ,
    name=f"short_model_{garage}")
 
# returns a [long_prediction,no_garages] sized 2d array, currently it only predicts from the most recent CSV data
def _make_prediction( data: pd.DataFrame, short_data: pd.DataFrame, 
                    long_garage_models: List[Model], short_garage_models: List[Model], 
                    short_feature_shape: int, long_feature_shape: int
                    ) -> np.ndarray:
    
    # Scale the data for long model
    scaler_long: MinMaxScaler = MinMaxScaler()
    scaler_long.fit(data)
    scaled_long: pd.DataFrame = pd.DataFrame(scaler_long.transform(data), columns=data.columns)

    # Scale the data for short model
    scaler_short: MinMaxScaler = MinMaxScaler()
    scaler_short.fit(short_data)
    scaled_short: pd.DataFrame = pd.DataFrame(scaler_short.transform(short_data), columns=short_data.columns)
    
    # Load weights if available
    try: 
        for index, garage in enumerate(GARAGE_NAMES, start=0):
            # Using Path object for better readability and cross-platform compatibility
            long_garage_models[index].load_weights(MODEL_DIRECTORY / f"long_model_{garage}.weights.h5")
            short_garage_models[index].load_weights(MODEL_DIRECTORY / f"short_model_{garage}.weights.h5")
    except Exception as e:
        print("Could not load weights, please verify you have existing weight files, exiting.")
        exit(-1)

    # Prepare prediction batches
    short_sample_batch: np.ndarray = scaled_short.values[-SHORT_SEQ:].reshape(1, SHORT_SEQ, short_feature_shape)
    long_sample_batch: np.ndarray = scaled_long.values[-LONG_SEQ:].reshape(1, LONG_SEQ, long_feature_shape)

    long_preds: List[np.ndarray] = []
    short_preds: List[np.ndarray] = []

    # Predict using the models, and unscale them
    for index, garage in enumerate(GARAGE_NAMES, start=0):
        long_pred: np.ndarray = long_garage_models[index].predict(long_sample_batch, verbose=2)[0]
        short_pred: np.ndarray = short_garage_models[index].predict(short_sample_batch, verbose=2)[0]
        long_unscaled_pred: np.ndarray = np.clip(scaler_long.inverse_transform(long_pred)[:, index], 0, 1)
        short_unscaled_pred: np.ndarray = np.clip(scaler_short.inverse_transform(short_pred)[:, index], 0, 1)
        long_preds.append(long_unscaled_pred)
        short_preds.append(short_unscaled_pred)


    # Combine short & long predictions with raised-cosine fade 
    future_length: int = len(long_preds[0])
    short_length: int = len(short_preds[0])
    t: np.ndarray = np.arange(short_length)
    w_short: np.ndarray = 0.5 * (1 + np.cos(np.pi * t / (short_length - 1)))
    w_long: np.ndarray = 1.0 - w_short
    combined: np.ndarray = np.zeros((future_length, 4))

    # for each of the first 4 features
    for i in range(4):
        combined[:short_length, i] = (w_short * short_preds[i] + w_long  * long_preds[i][:short_length])
        combined[short_length:, i] = long_preds[i][short_length:]

    return combined
   
def main():
    global extra_long_data
    data: pd.DataFrame = load_data()
    short_data: pd.DataFrame = data.drop(columns=["date"]).copy() # Keep a copy of the raw density data (without date)
    long_garage_models: List[Model] = []
    short_garage_models: List[Model] = []
    
    # Process the data
    if ENABLE_INSTR_DAY:
        data = load_instruction_days(data)
    if ENABLE_TIME_ENCODING:
        data = cyclical_time_encoding(data)
        
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
    utils.plot_prediction(prediction, short_data, data)


if __name__ == "__main__":
    main()
