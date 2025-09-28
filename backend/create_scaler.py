"""
Quick script to create and save a scaler based on the weather data
This should match what was used during training
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import joblib
import json

# Load the data
df = pd.read_csv('../backup/Weather_Data_1980_2024(hourly).csv')

# Use the same features as in training
features = ['temperature', 'relative_humidity', 'wind_speed_10m (km/h)']

# Clean data
df_clean = df[features].dropna()

# Print statistics
print("Data statistics before scaling:")
for feature in features:
    print(f"{feature}:")
    print(f"  Min: {df_clean[feature].min():.2f}")
    print(f"  Max: {df_clean[feature].max():.2f}")
    print(f"  Mean: {df_clean[feature].mean():.2f}")
    print()

# Create and fit scaler
scaler = MinMaxScaler()
scaler.fit(df_clean[features])

# Save scaler
joblib.dump(scaler, 'scaler.pkl')
print("Scaler saved to scaler.pkl")

# Save scaling parameters as JSON for reference
scaling_params = {
    'features': features,
    'min_values': scaler.data_min_.tolist(),
    'max_values': scaler.data_max_.tolist(),
    'ranges': scaler.data_range_.tolist()
}

with open('scaling_params.json', 'w') as f:
    json.dump(scaling_params, f, indent=2)

print("\nScaling parameters:")
for i, feature in enumerate(features):
    print(f"{feature}: [{scaler.data_min_[i]:.2f}, {scaler.data_max_[i]:.2f}]")