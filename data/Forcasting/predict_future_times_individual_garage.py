import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from predict_future_times import plot_prediction
from keras_model_file import build_model
from short_term_model import train_short_model
from long_term_model import train_long_model


garage_names = ["south","west","north","south_campus"]
model_folder = "data/Forcasting/keras_models"
logs_directory = "data/Records"

# control flags  [True,True,True,True] [False,False,False,False] (for easy copy paste)
long_training_mask      = [False,False,False,False]
short_training_mask     = [False,False,False,False]
enable_time_encoding    =  True
enable_instr_day        =  True
enable_instr_next_day   =  True

# Load and preprocess log.csv data
data = pd.read_csv(f"{logs_directory}/log.csv")
data = data[-1000:] # WHY IS THIS NESSESSARY TO WORK, I DON'T KNOW
data = data.drop(columns=["Unnamed: 0", "south density", "west density", "north density", "south compus density"])
extra_long_data = 0

# Keep a copy of the raw density data (without date)
short_data = data.drop(columns=["date"]).copy()

# Load the instruction days CSV and prepare it
if enable_instr_day:
    instruction_days_df = pd.read_csv(f"{logs_directory}/sjsu_instruction_days.csv")
    instruction_days_df["Date"] = pd.to_datetime(instruction_days_df["Date"]).dt.date
    instruction_days_df.rename(columns={"Instruction_Day": "instruction_day"}, inplace=True)
    # Prepare the log data
    data['date'] = pd.to_datetime(data['date'])
    data['date_only'] = data['date'].dt.date

    # Merge original instruction day flag
    data = pd.merge(data, instruction_days_df, how="left", left_on="date_only", right_on="Date")
    data["instruction_day"] = data["instruction_day"].fillna(False)

    if enable_instr_next_day: 
        # Add a column for the previous day that maps to the next day's instruction flag
        next_day_instr_df = instruction_days_df.copy()
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


#cyclical time encodings
if enable_time_encoding:
    ts = data['date']
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
    extra_long_data += 10

# Prepare data for long-term model (includes time encoding features)
long_data = data.drop(columns=["date"]).copy()

# Define parameters for long model
long_seq = 8
long_future_steps = 128
long_feature_shape = short_data.shape[1] + extra_long_data

# Define parameters for short model
short_seq = 16
short_future_steps = 16
short_feature_shape = short_data.shape[1]

long_garage_models = []
short_garage_models = []

# remember the models will not load correctly if you changes this and don't re-train
for garage_no, garage in enumerate(garage_names,start=0):
# long model hyperparameters 
    long_garage_models.append(build_model(
    lstm_neurons_list=[192,32,192],
    dropout=0.1,
    learning_rate=2e-5,
    seq_size=long_seq,
    activation='linear',
    n_feature=long_feature_shape,
    future_steps=long_future_steps,
    garage_no=garage_no))

# short model hyperparameters 
    short_garage_models.append(build_model(
    lstm_neurons_list=[64,16,64],
    dropout=0.1,
    learning_rate=1e-4,
    seq_size=short_seq,
    activation='celu',
    n_feature=short_feature_shape,
    future_steps=short_future_steps,
    garage_no=garage_no))

def main():
    # not parrallelizable, not threadsafe :C thanks keras 
    for index, garage in enumerate(garage_names,start=0):
        print(f"training long model: {garage}")
        if long_training_mask[index]:
            train_long_model(
            model=long_garage_models[index],
            training_epochs=35,
            batch_size=512,
            future_steps=long_future_steps,
            test_split=0.8,
            seq_size=long_seq,
            name=f"long_model_{garage}")
        print(f"training short model: {garage}")
        if short_training_mask[index]:
            train_short_model(
            model=short_garage_models[index],
            training_epochs=25,
            batch_size=32,
            future_steps=short_future_steps,
            test_split=0.8,
            seq_size=short_seq,
            name=f"short_model_{garage}")


    prediction = make_prediction()
    plot_prediction(prediction)

# returns a [long_prediction,no_garages] sized 2d array, currently it only predicts from the most recent CSV data
def make_prediction():
    # Scale the data for long model
    scaler_long = MinMaxScaler()
    scaler_long.fit(long_data)
    scaled_long = pd.DataFrame(scaler_long.transform(long_data), columns=long_data.columns)

    # Scale the data for short model
    scaler_short = MinMaxScaler()
    scaler_short.fit(short_data)
    scaled_short = pd.DataFrame(scaler_short.transform(short_data), columns=short_data.columns)
    
    # Load weights if available
    try: 
        for index,garage in enumerate(garage_names,start=0):
            long_garage_models[index].load_weights(f"{model_folder}/long_model_{garage}.weights.h5")
            short_garage_models[index].load_weights(f"{model_folder}/short_model_{garage}.weights.h5")
    except Exception as e:
        print("Could not load weights, please verify you have existing weight files, exiting.")
        exit(-1)

    # Prepare prediction batches
    short_sample_batch = scaled_short.values[-short_seq:].reshape(1, short_seq, short_feature_shape)
    long_sample_batch  = scaled_long.values[-long_seq:].reshape(1, long_seq, long_feature_shape)

    long_preds = []
    short_preds = []

    # Predict using the models, and unscale them
    for index,garage in enumerate(garage_names,start=0):
        long_pred = long_garage_models[index].predict(long_sample_batch, verbose=2)[0]
        short_pred = short_garage_models[index].predict(short_sample_batch, verbose=2)[0]
        long_unscaled_pred   = np.clip(scaler_long.inverse_transform(long_pred)[:, index], 0, 1)
        short_unscaled_pred = np.clip(scaler_short.inverse_transform(short_pred)[:, index], 0, 1)
        long_preds.append(long_unscaled_pred)
        short_preds.append(short_unscaled_pred)


    # Combine short & long predictions with raised-cosine fade 
    future_length = len(long_preds[0])
    short_length  = len(short_preds[0])
    t       = np.arange(short_length)
    w_short = 0.5 * (1 + np.cos(np.pi * t / (short_length - 1)))
    w_long  = 1.0 - w_short
    combined = np.zeros((future_length, 4))

    # for each of the first 4 features
    for i in range(4):
        combined[:short_length, i] = (w_short * short_preds[i] + w_long  * long_preds[i][:short_length])
        combined[short_length:, i] = long_preds[i][short_length:]

    return combined

if __name__ == "__main__":
    main()
