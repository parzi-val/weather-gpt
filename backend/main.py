from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from google import genai
from google.genai import types
import requests
import os
from datetime import datetime
import json
from dotenv import load_dotenv
from pathlib import Path
from model import get_predictor

# Load environment variables from .env file
# Get the directory where this script is located
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / '.env'

# Load with explicit path and verbose output
load_result = load_dotenv(dotenv_path=env_path, verbose=True)
print(f"Loaded .env from {env_path}: {load_result}")
print(f".env file exists: {env_path.exists()}")

app = FastAPI(title="WeatherGPT API", version="1.0.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini API (you'll need to set this environment variable)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
print(f"GEMINI_API_KEY loaded: {'Yes' if GEMINI_API_KEY else 'No'}")
print(f"Key length: {len(GEMINI_API_KEY)} characters")

# Initialize the client with the new google-genai library
client = None
if GEMINI_API_KEY and len(GEMINI_API_KEY) > 0:
    client = genai.Client(api_key=GEMINI_API_KEY)

# Request models
class LocationRequest(BaseModel):
    latitude: float
    longitude: float
    city: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    latitude: float
    longitude: float
    weather_context: Optional[Dict[str, Any]] = None

class ApiKeyRequest(BaseModel):
    email: str
    name: str

# Weather fetching function using Open-Meteo (free, no API key needed)
def fetch_weather_data(latitude: float, longitude: float) -> Dict[str, Any]:
    """Fetch weather data from Open-Meteo API"""
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={latitude}&longitude={longitude}"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,showers,snowfall,weather_code,cloud_cover,pressure_msl,surface_pressure,wind_speed_10m,wind_direction_10m,wind_gusts_10m"
        f"&hourly=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation_probability,precipitation,rain,showers,snowfall,snow_depth,weather_code,pressure_msl,surface_pressure,cloud_cover,visibility,wind_speed_10m,wind_direction_10m,uv_index"
        f"&daily=weather_code,temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,sunrise,sunset,uv_index_max,precipitation_sum,rain_sum,showers_sum,snowfall_sum,precipitation_hours,precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max"
        f"&timezone=auto&forecast_days=7"
    )

    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch weather data: {str(e)}")

def format_weather_for_chat(weather_data: Dict[str, Any]) -> str:
    """Format weather data into a concise string for chat context"""
    current = weather_data.get("current", {})
    daily = weather_data.get("daily", {})

    context = f"""Current Weather:
- Temperature: {current.get('temperature_2m', 'N/A')}°C
- Feels like: {current.get('apparent_temperature', 'N/A')}°C
- Humidity: {current.get('relative_humidity_2m', 'N/A')}%
- Wind: {current.get('wind_speed_10m', 'N/A')} km/h
- Precipitation: {current.get('precipitation', 0)} mm
- Cloud cover: {current.get('cloud_cover', 'N/A')}%
- Pressure: {current.get('pressure_msl', 'N/A')} hPa

7-Day Forecast Summary:
"""

    if daily:
        for i in range(min(7, len(daily.get('time', [])))):
            date = daily['time'][i]
            max_temp = daily['temperature_2m_max'][i]
            min_temp = daily['temperature_2m_min'][i]
            precip = daily['precipitation_sum'][i]
            context += f"- {date}: {min_temp}°C to {max_temp}°C, Precipitation: {precip}mm\n"

    return context

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "WeatherGPT API",
        "endpoints": {
            "weather": "/api/weather",
            "chat": "/api/chat",
            "generate_key": "/api/generate-key"
        }
    }

@app.post("/api/weather")
async def get_weather(location: LocationRequest):
    """Get weather data for a specific location"""
    weather_data = fetch_weather_data(location.latitude, location.longitude)

    return {
        "success": True,
        "location": {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "city": location.city
        },
        "current": weather_data.get("current", {}),
        "hourly": weather_data.get("hourly", {})[:24],  # Next 24 hours
        "daily": weather_data.get("daily", {}),
        "timezone": weather_data.get("timezone", ""),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/chat")
async def chat_with_weather(request: ChatRequest):
    """Chat endpoint that combines weather data with Gemini AI"""

    if not client:
        # Fallback response if no API key
        return {
            "success": False,
            "message": "Gemini API key not configured. Please set GEMINI_API_KEY environment variable.",
            "response": "I'm sorry, but I need a Gemini API key to provide intelligent weather insights. For now, you can use the weather API directly."
        }

    # Fetch current weather if not provided
    if not request.weather_context:
        weather_data = fetch_weather_data(request.latitude, request.longitude)
        weather_context = format_weather_for_chat(weather_data)
    else:
        weather_context = json.dumps(request.weather_context, indent=2)

    # Create prompt for Gemini
    prompt = f"""You are WeatherGPT, an intelligent weather assistant. You have access to current weather data and forecasts.

Weather Data for location ({request.latitude}, {request.longitude}):
{weather_context}

User Question: {request.message}

Please provide a helpful, conversational response about the weather. Be specific and practical. If the user asks about activities, clothing, or planning, give personalized advice based on the weather data."""

    try:
        # Generate response with the new google-genai library
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',  # Using the latest model
            contents=prompt
        )

        return {
            "success": True,
            "response": response.text,
            "weather_context": weather_context,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "response": f"I encountered an error: {str(e)}. Please try again.",
            "timestamp": datetime.now().isoformat()
        }

@app.post("/api/generate-key")
async def generate_api_key(request: ApiKeyRequest):
    """Generate a placeholder API key (for demo purposes)"""
    import hashlib
    import time

    # Generate a fake API key
    hash_input = f"{request.email}{request.name}{time.time()}"
    api_key = f"wgpt_{hashlib.sha256(hash_input.encode()).hexdigest()[:32]}"

    return {
        "success": True,
        "api_key": api_key,
        "message": "API key generated successfully (demo only)",
        "usage": {
            "endpoint": "https://api.weathergpt.ai/v1/forecast",
            "headers": {
                "X-API-Key": api_key
            },
            "example_curl": f"""curl -X POST https://api.weathergpt.ai/v1/forecast \\
  -H "X-API-Key: {api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{{"latitude": 40.7128, "longitude": -74.0060}}'"""
        }
    }

@app.post("/api/predict")
async def predict_with_transformer(location: LocationRequest):
    """Get AI predictions using our trained transformer model"""
    try:
        # Get current weather data
        weather_data = fetch_weather_data(location.latitude, location.longitude)

        # Get predictor instance
        predictor = get_predictor()

        # Make predictions
        predictions = predictor.predict(weather_data)

        # Add location info
        predictions["location"] = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "city": location.city
        }
        predictions["timestamp"] = datetime.now().isoformat()

        # Add current weather for comparison
        if "current" in weather_data:
            predictions["current_weather"] = {
                "temperature": weather_data["current"].get("temperature_2m"),
                "humidity": weather_data["current"].get("relative_humidity_2m"),
                "wind_speed": weather_data["current"].get("wind_speed_10m")
            }

        return predictions

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""

    # Check if model is loaded
    try:
        predictor = get_predictor()
        model_loaded = predictor.model_loaded
    except:
        model_loaded = False

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "gemini_configured": bool(GEMINI_API_KEY),
        "model_loaded": model_loaded
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)