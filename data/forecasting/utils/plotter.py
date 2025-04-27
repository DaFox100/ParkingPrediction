import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def plot_prediction(prediction: np.ndarray, short_data: pd.DataFrame, data: pd.DataFrame):
    
    # data = pd.DataFrame(data)
    # data['date'] = pd.to_datetime(data['date'])
    
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