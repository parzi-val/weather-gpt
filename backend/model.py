import torch
import torch.nn as nn
import math
import numpy as np
from typing import List, Dict, Any
import json
from pathlib import Path
import joblib

class PositionalEncoding(nn.Module):
    def __init__(self, d_model, dropout=0.1, max_len=1000):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float32).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() *
                           (-math.log(10000.0) / d_model))

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)

        pe = pe.unsqueeze(0)
        self.register_buffer('pe', pe)

    def forward(self, x):
        x = x + self.pe[:, :x.size(1)]
        return self.dropout(x)


class MultiVariateTransformer(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.config = config

        # Input projection
        self.input_proj = nn.Linear(config['input_dim'], config['model_dim'])

        # Positional encoding
        self.pos_encoding = PositionalEncoding(config['model_dim'], config['dropout'])

        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config['model_dim'],
            nhead=config['num_heads'],
            dropout=config['dropout'],
            batch_first=True,
            activation='gelu'
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, config['num_layers'])

        # Output projection
        self.output_proj = nn.Sequential(
            nn.Linear(config['model_dim'], config['model_dim'] * 2),
            nn.GELU(),
            nn.Dropout(config['dropout']),
            nn.Linear(config['model_dim'] * 2, config['output_window'] * config['output_dim'])
        )

    def forward(self, x):
        # x: [batch, input_window, input_dim]
        x = self.input_proj(x)
        x = self.pos_encoding(x)
        x = self.transformer(x)

        # Use mean pooling over time dimension
        x = x.mean(dim=1)  # [batch, model_dim]

        # Project to output
        output = self.output_proj(x)  # [batch, output_window * output_dim]

        # Reshape to [batch, output_window, output_dim]
        output = output.view(-1, self.config['output_window'], self.config['output_dim'])

        return output


class WeatherPredictor:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Load config
        config_path = Path(__file__).parent / "model_config.json"
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        # Initialize model
        self.model = MultiVariateTransformer(self.config)

        # Load weights
        weights_path = Path(__file__).parent / "multivariate_model_weights.pth"
        if weights_path.exists():
            self.model.load_state_dict(torch.load(weights_path, map_location=self.device))
            self.model.to(self.device)
            self.model.eval()
            self.model_loaded = True
        else:
            self.model_loaded = False
            print(f"Warning: Model weights not found at {weights_path}")

        # Load scaler for proper normalization
        scaler_path = Path(__file__).parent / "scaler.pkl"
        if scaler_path.exists():
            self.scaler = joblib.load(scaler_path)
            print("Scaler loaded successfully")
        else:
            self.scaler = None
            print(f"Warning: Scaler not found at {scaler_path}")

    def prepare_input(self, weather_data: Dict[str, Any]) -> torch.Tensor:
        """
        Prepare weather data for model input
        Model expects 7 input features as per config:
        - temperature, relative_humidity, dew_point, wind_speed_10m,
        - pressure_msl, cloud_cover, vapour_pressure_deficit
        """
        # Get hourly data
        hourly = weather_data.get('hourly', {})

        # Prepare input array - use all 7 features the model was trained on
        input_data = []

        # Get the last 168 hours of data
        num_hours = min(168, len(hourly.get('time', [])))

        for i in range(num_hours):
            features = []

            # 1. Temperature (temperature_2m from API)
            temp = hourly.get('temperature_2m', [None] * num_hours)[i]
            if temp is None:
                temp = 20.0
            features.append(float(temp))

            # 2. Relative Humidity (relative_humidity_2m from API)
            humidity = hourly.get('relative_humidity_2m', [None] * num_hours)[i]
            if humidity is None:
                humidity = 50.0
            features.append(float(humidity))

            # 3. Dew Point (apparent_temperature from API as approximation)
            dew_point = hourly.get('apparent_temperature', [None] * num_hours)[i]
            if dew_point is None:
                # Calculate approximate dew point from temp and humidity
                dew_point = temp - ((100 - humidity) / 5.0) if temp and humidity else 15.0
            features.append(float(dew_point))

            # 4. Wind Speed (wind_speed_10m from API)
            wind = hourly.get('wind_speed_10m', [None] * num_hours)[i]
            if wind is None:
                wind = 10.0
            features.append(float(wind))

            # 5. Pressure MSL (pressure_msl from API)
            pressure = hourly.get('pressure_msl', [None] * num_hours)[i]
            if pressure is None:
                pressure = 1013.0  # Standard pressure
            features.append(float(pressure))

            # 6. Cloud Cover (cloud_cover from API)
            cloud = hourly.get('cloud_cover', [None] * num_hours)[i]
            if cloud is None:
                cloud = 50.0
            features.append(float(cloud))

            # 7. Vapour Pressure Deficit (calculate from temp and humidity)
            # VPD = SVP - AVP where SVP = saturation vapor pressure, AVP = actual vapor pressure
            if temp is not None and humidity is not None:
                svp = 0.611 * np.exp((17.27 * temp) / (temp + 237.3))  # kPa
                avp = (humidity / 100.0) * svp
                vpd = svp - avp
            else:
                vpd = 0.5  # Default VPD
            features.append(float(vpd))

            input_data.append(features)

        # Pad if we have less than 168 hours - pad with the first available values
        if len(input_data) > 0:
            pad_value = input_data[0]
        else:
            pad_value = [20.0, 50.0, 15.0, 10.0, 1013.0, 50.0, 0.5]  # Default values for all 7 features

        while len(input_data) < 168:
            input_data.insert(0, pad_value.copy())

        # Convert to numpy array
        input_array = np.array(input_data, dtype=np.float32)

        # Normalize each feature based on typical ranges (since we don't have the input scaler)
        input_normalized = np.zeros_like(input_array)

        # Temperature: typical range [-20, 50]
        input_normalized[:, 0] = (input_array[:, 0] - (-20)) / (50 - (-20))

        # Relative Humidity: [0, 100]
        input_normalized[:, 1] = input_array[:, 1] / 100.0

        # Dew Point: typical range [-30, 35]
        input_normalized[:, 2] = (input_array[:, 2] - (-30)) / (35 - (-30))

        # Wind Speed: [0, 50]
        input_normalized[:, 3] = input_array[:, 3] / 50.0

        # Pressure: typical range [950, 1050]
        input_normalized[:, 4] = (input_array[:, 4] - 950) / (1050 - 950)

        # Cloud Cover: [0, 100]
        input_normalized[:, 5] = input_array[:, 5] / 100.0

        # VPD: typical range [0, 4]
        input_normalized[:, 6] = input_array[:, 6] / 4.0

        # Clip to [0, 1] range
        input_normalized = np.clip(input_normalized, 0, 1)

        # Convert to tensor
        input_tensor = torch.tensor(input_normalized, dtype=torch.float32)

        # Add batch dimension
        input_tensor = input_tensor.unsqueeze(0)

        return input_tensor

    def predict(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make predictions based on weather data
        Returns predictions for temperature, humidity, and wind speed for next 72 hours
        """
        if not self.model_loaded:
            return {
                "status": "error",
                "message": "Model not loaded"
            }

        try:
            # Prepare input
            input_tensor = self.prepare_input(weather_data)
            input_tensor = input_tensor.to(self.device)

            # Make prediction
            with torch.no_grad():
                output = self.model(input_tensor)

            # Convert output to numpy
            predictions = output.cpu().numpy()[0]  # Remove batch dimension

            # Denormalize predictions using the same scaler
            if self.scaler is not None:
                # Use inverse_transform for proper denormalization
                predictions_denorm = self.scaler.inverse_transform(predictions)
            else:
                # Fallback to manual denormalization with training ranges
                predictions_denorm = np.zeros_like(predictions)
                # Temperature: [7.10, 41.70]
                predictions_denorm[:, 0] = predictions[:, 0] * (41.70 - 7.10) + 7.10
                # Relative Humidity: [6.00, 100.00]
                predictions_denorm[:, 1] = predictions[:, 1] * (100.00 - 6.00) + 6.00
                # Wind Speed: [0.00, 43.30]
                predictions_denorm[:, 2] = predictions[:, 2] * (43.30 - 0.00) + 0.00

            # Ensure values stay in valid ranges
            predictions_denorm[:, 0] = np.clip(predictions_denorm[:, 0], -50, 50)  # Temperature range
            predictions_denorm[:, 1] = np.clip(predictions_denorm[:, 1], 0, 100)  # Humidity percentage
            predictions_denorm[:, 2] = np.clip(predictions_denorm[:, 2], 0, 100)  # Wind speed

            predictions = predictions_denorm

            # Create hourly predictions
            hourly_predictions = []
            for i in range(self.config['output_window']):
                hourly_predictions.append({
                    "hour": i + 1,
                    "temperature": float(predictions[i, 0]),
                    "relative_humidity": float(predictions[i, 1]),
                    "wind_speed": float(predictions[i, 2])
                })

            return {
                "status": "success",
                "predictions": {
                    "hourly": hourly_predictions,
                    "summary": {
                        "avg_temperature": float(predictions[:, 0].mean()),
                        "max_temperature": float(predictions[:, 0].max()),
                        "min_temperature": float(predictions[:, 0].min()),
                        "avg_humidity": float(predictions[:, 1].mean()),
                        "avg_wind_speed": float(predictions[:, 2].mean())
                    }
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

# Global predictor instance
predictor = None

def get_predictor():
    global predictor
    if predictor is None:
        predictor = WeatherPredictor()
    return predictor