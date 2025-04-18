import numpy as np
import pandas as pd
from keras_model_file import train_model
from sklearn.preprocessing import MinMaxScaler

enable_instr_day = True
enable_instr_next_day = True

def train_long_model(model, batch_size, future_steps, test_split, seq_size, name, training_epochs):
    
    # Load and preprocess log.csv data
    data = pd.read_csv("log.csv")
    data = data.drop(columns=["Unnamed: 0", "south density", "west density", "north density", "south compus density"])

    # Load the instruction days CSV and prepare it
    if enable_instr_day:
        instruction_days_df = pd.read_csv("sjsu_instruction_days.csv")
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
        else: # Drop temporary columns
            data.drop(columns=["Date", "date_only"], inplace=True)



    # === Feature engineering: cyclical encodings ===
    ts = data['date']
    data['month_sin']       = np.sin(2 * np.pi * ts.dt.month-1     / 12)
    data['month_cos']       = np.cos(2 * np.pi * ts.dt.month-1     / 12)
    data['day_sin']         = np.sin(2 * np.pi * ts.dt.day       / 31)
    data['day_cos']         = np.cos(2 * np.pi * ts.dt.day       / 31)
    data['day_of_week_sin'] = np.sin(2 * np.pi * ts.dt.dayofweek / 7)
    data['day_of_week_cos'] = np.cos(2 * np.pi * ts.dt.dayofweek / 7)
    data['hour_sin']        = np.sin(2 * np.pi * ts.dt.hour      / 24)
    data['hour_cos']        = np.cos(2 * np.pi * ts.dt.hour      / 24)
    data['minute_sin']      = np.sin(2 * np.pi * ts.dt.minute    / 60)
    data['minute_cos']      = np.cos(2 * np.pi * ts.dt.minute    / 60)

    # Prepare data for long-term model (includes positional encoding features)
    data = data.drop(columns=["date"]).copy()
    
    # Train-test split
    train_size = int(len(data) * test_split)
    train_data = data.iloc[:train_size]
    test_data = data.iloc[train_size:]

    scaler = MinMaxScaler() # Scalers are used to normalize the data, this makes it easier for the model to learn the data
    scaler.fit(test_data) # Fit the scaler to the training data

    # Transform the data using the scaler
    train_scaled = pd.DataFrame(scaler.transform(train_data), columns=train_data.columns)
    test_scaled = pd.DataFrame(scaler.transform(test_data), columns=test_data.columns)

    # Sequence Settings, the sequence length is the size of the rolling window that we use to make predictions
    n_feature = data.shape[1] # n_features is the number of inputs to the model, if we want to give the model more context we can increase this value

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
    train_model(model, X_train, Y_train, X_test, Y_test, batch_size, training_epochs,name)