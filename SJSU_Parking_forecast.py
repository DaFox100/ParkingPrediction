import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load and preprocess data
data = pd.read_csv("log.csv")
data = data.drop(columns=["Unnamed: 0", 'south density', 'west density', 'north density', 'south compus density'])

dataset = data.values
timestamps = pd.to_datetime(dataset[:, 0])
time_deltas = (timestamps - timestamps[0]).total_seconds() / 60
dataset[:, 0] = time_deltas
dataset = dataset.astype('float64')
scaler = MinMaxScaler(feature_range=(0, 1))
dataset = scaler.fit_transform(dataset)

train_size = int(len(dataset) * 0.99944)
test_size = len(dataset) - train_size
train, test = dataset[0:train_size, :], dataset[train_size:len(dataset), :]

seq_size = test_size - 1
n_feature = 5

# Dataset class
class TimeSeriesDataset(Dataset):
    def __init__(self, data, seq_size):
        self.data = data
        self.seq_size = seq_size
    
    def __len__(self):
        return len(self.data) - self.seq_size - 1
    
    def __getitem__(self, idx):
        x = self.data[idx:idx + self.seq_size, :]
        y = self.data[idx + self.seq_size, :]
        return torch.tensor(x, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)

train_dataset = TimeSeriesDataset(train, seq_size)
test_dataset = TimeSeriesDataset(test, seq_size)

train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=16, shuffle=False)

# Define LSTM model
class LSTMModel(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, output_size):
        super(LSTMModel, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)
    
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        out = self.fc(lstm_out[:, -1, :])
        return out

# Hyperparameters
hidden_size = 32
num_layers = 2
learning_rate = 0.001
epochs = 50

# Model, Loss, Optimizer
model = LSTMModel(input_size=n_feature, hidden_size=hidden_size, num_layers=num_layers, output_size=n_feature)
criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=learning_rate)

# Training loop
for epoch in range(epochs):
    model.train()
    train_loss = 0
    for x_batch, y_batch in train_loader:
        optimizer.zero_grad()
        y_pred = model(x_batch)
        loss = criterion(y_pred, y_batch)
        loss.backward()
        optimizer.step()
        train_loss += loss.item()
    
    print(f"Epoch {epoch+1}/{epochs}, Loss: {train_loss/len(train_loader):.4f}")

# Prediction
model.eval()
predictions = []
x_test = torch.tensor(test[:-seq_size, :], dtype=torch.float32).unsqueeze(0)

with torch.no_grad():
    for i in range(len(test) + 7):
        y_pred = model(x_test[:, -seq_size:, :])
        predictions.append(y_pred.squeeze(0).numpy())
        x_test = torch.cat((x_test[:, 1:, :], y_pred.unsqueeze(0)), dim=1)

predictions = np.array(predictions)
rescaled_prediction = scaler.inverse_transform(predictions)

# Compare predictions
def compare_predictions(rescaled_prediction, test):
    test_values = test[:, 1:]
    pred_values = rescaled_prediction[:, 1:]
    pred_values_trimmed = pred_values[:len(test_values)]
    mse = mean_squared_error(test_values, pred_values_trimmed)
    print(f"Mean Squared Error (MSE): {mse:.4f}")
    plt.figure(figsize=(12, 6))
    for i in range(test_values.shape[1]):
        plt.plot(test_values[:, i], label=f"Actual Feature {i+1}")
        plt.plot(pred_values_trimmed[:, i], linestyle='dashed', label=f"Predicted Feature {i+1}")
    plt.xlabel("Time Steps")
    plt.ylabel("Values")
    plt.title("Actual vs Predicted Values")
    plt.legend()
    plt.show()

compare_predictions(rescaled_prediction, test)
