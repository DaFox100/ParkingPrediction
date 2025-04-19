import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler

from keras_model_file import build_model
from short_term_model import train_short_model
from long_term_model import train_long_model

# Flags to control training
enable_train_short = True
enable_train_long = True
enable_time_encoding = True
enable_instr_day = True
enable_instr_next_day = True

garage_names = ["south","west","north","south_campus"]
model_folder = "keras_models"
logs_directory = "data/Records"

extra_long_data = 0
# Load and preprocess log.csv data
data = pd.read_csv(f"{logs_directory}/log.csv")
data = data[-1000:] # WHY IS THIS NESSESSARY TO WORK, I DON'T KNOW
data = data.drop(columns=["Unnamed: 0", "south density", "west density", "north density", "south compus density"])

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

# Define hyper-parameters for long model
long_seq = 8
long_future_steps = 128
long_feature_shape = short_data.shape[1] + extra_long_data
long_garage_model = build_model(
    lstm_neurons_list=[192,32,192],
    dropout=0.1,
    learning_rate=2e-5,
    seq_size=long_seq,
    activation='linear',
    n_feature=long_feature_shape,
    future_steps=long_future_steps)

# Define hyper-parameters for short model
short_seq = 16
short_future_steps = 32
short_feature_shape = short_data.shape[1]
short_garage_model = build_model(
    lstm_neurons_list=[64,16,64],
    dropout=0.1,
    learning_rate=1e-4,
    seq_size=short_seq,
    activation='celu',
    n_feature=short_feature_shape,
    future_steps=short_future_steps)

def main():
    if enable_train_long:
        train_long_model(
            model=long_garage_model,
            training_epochs=50,
            batch_size=32,
            future_steps=long_future_steps,
            test_split=0.8,
            seq_size=long_seq,
            name="long_model")

    if enable_train_short:
        train_short_model(
            model=short_garage_model,
            training_epochs=50,
            batch_size=32,
            future_steps=short_future_steps,
            test_split=0.8,
            seq_size=short_seq,
            name="short_model")

    prediction = make_prediction()
    plot_prediction(prediction)

# returns a [long_prediction,no_garages] sized 2d array, currently it only predicts from the most recent times from the CSV data
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
        long_garage_model.load_weights(f"{model_folder}/long_model.weights.h5")
        short_garage_model.load_weights(f"{model_folder}/short_model.weights.h5")
    except Exception as e:
        print("Could not load weights, please verify you have existing weight files, exiting.")
        exit(-1)

    # Prepare prediction batches
    short_sample_batch = scaled_short.values[-short_seq:].reshape(1, short_seq, short_feature_shape)
    long_sample_batch  = scaled_long.values[-long_seq:].reshape(1, long_seq, long_feature_shape)

    # Perform the actual predictions 
    long_preds = long_garage_model.predict(long_sample_batch, verbose=2)[0]
    short_preds = short_garage_model.predict(short_sample_batch, verbose=2)[0]

    # Inverse scale and clip predictions using the existing (fitted) scalers
    long_unscaled  = scaler_long.inverse_transform(long_preds)[:, :long_feature_shape]
    short_unscaled = scaler_short.inverse_transform(short_preds)[:, :short_feature_shape]
    long_unscaled  = np.clip(long_unscaled, 0, 1)
    short_unscaled = np.clip(short_unscaled, 0, 1)
    
    #Combine short & long predictions with raised-cosine fade,
    #this smooths out the transition from real data to predicted data

    future_length = long_unscaled.shape[0]
    short_length  = short_unscaled.shape[0]
    t = np.arange(short_length)
    w_short = 0.5 * (1 + np.cos(np.pi * t / (short_length - 1)))
    w_long  = 1.0 - w_short

    combined = np.zeros((future_length, 4))
    combined[:short_length, :] = (
        w_short[:, None] * short_unscaled[:short_length, :4] +
        w_long[:, None]  * long_unscaled[:short_length, :4])
    
    combined[short_length:, :] = long_unscaled[short_length:, :4]
    return combined
   
def plot_prediction(prediction):
    future_length = len(prediction)
    lead_steps = 4
    transition_length = lead_steps
    visible_real = short_data.values[-future_length - lead_steps : -lead_steps, :4]
    visible_time = pd.to_datetime(data[-future_length - lead_steps : -lead_steps]["date"]).tolist()

    # Instead of forcing the first prediction to equal the last real value, we let it be predicted.
    # Build future timestamps starting from last visible real time + an appropriate increment:
    last_visible_time = visible_time[-1]
    if last_visible_time.hour >= 21 or last_visible_time.hour < 6:
        initial_increment = pd.Timedelta(hours=1)
    else:
        initial_increment = pd.Timedelta(minutes=10)
    date_pred_x = [last_visible_time + initial_increment]
    for _ in range(1, future_length):
        last = date_pred_x[-1]
        if last.hour >= 21 or last.hour < 6:
            next_time = last + pd.Timedelta(hours=1)
        else:
            next_time = last + pd.Timedelta(minutes=10)
        date_pred_x.append(next_time)

    # Apply a smoother transition (real → predicted) on the blend window
    actual_blend    = short_data.values[-lead_steps:, :4]  # real values for blending
    predicted_blend = prediction[:transition_length, :]

    t2 = np.arange(transition_length)
    w_real = 0.5 * (1 + np.cos(np.pi * t2 / (transition_length - 1)))  # weight for real data (from 1→0)
    w_pred = 1.0 - w_real                                               # weight for predicted data (from 0→1)

    prediction[:transition_length, :] = (
        w_real[:, None] * actual_blend +
        w_pred[:, None] * predicted_blend
    )

    # Final Plot
    plt.figure(figsize=(12, 6))
    for i in range(4):
        actual_y = visible_real[:, i]
        plt.plot(visible_time, actual_y, label=f'Actual Feature {i+1}')
        plt.plot(date_pred_x, prediction[:, i], '--', label=f'Predicted Feature {i+1}')

    plt.xlabel("Time")
    plt.ylabel("Value")
    plt.title("Actual vs. Smoothed Forecast with Adjusted Scaler Usage")
    plt.legend()
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    main()