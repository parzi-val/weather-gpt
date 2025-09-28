# WeatherGPT - AI-Powered Weather Intelligence

A modern weather forecasting platform combining transformer-based predictions with conversational AI.

## Features

- 🤖 **WeatherGPT Chat** - Natural language weather queries powered by Google Gemini
- 🌡️ **Real-time Weather Data** - Live weather from Open-Meteo API
- 🔮 **AI Predictions** - Transformer model for 72-hour forecasts (when trained)
- 🚀 **Developer API** - RESTful API for programmatic access
- 🌙 **Dark Mode UI** - Beautiful shadcn/ui components
- 📍 **Location Aware** - Automatic geolocation support

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Google Gemini API key (optional, for chat features)

### Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Set your Gemini API key (optional)
export GEMINI_API_KEY="your-key-here"

# Run the server
python main.py
```

The backend will be available at `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`

## API Endpoints

- `POST /api/weather` - Get weather for a location
- `POST /api/chat` - Chat with WeatherGPT
- `POST /api/generate-key` - Generate API key (demo)
- `GET /api/health` - Health check

## Project Structure

```
forecast-fusion/
├── backend/
│   ├── main.py           # FastAPI server
│   └── requirements.txt   # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.tsx        # Main React component
│   │   └── components/    # UI components
│   └── package.json       # Node dependencies
└── README.md
```

## Environment Variables

### Backend
- `GEMINI_API_KEY` - Google Gemini API key for chat features

## Development

The project uses:
- **Backend**: FastAPI, Google Generative AI, Open-Meteo API
- **Frontend**: React, Vite, TypeScript, Tailwind CSS, shadcn/ui
- **AI Model**: PyTorch Transformer (training separately)

## Features Roadmap

- [ ] Integrate trained transformer model
- [ ] Add weather visualizations
- [ ] Implement real API authentication
- [ ] Add more weather providers
- [ ] Deploy to cloud platform

## License

MIT