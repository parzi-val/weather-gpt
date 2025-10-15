# Weather Forecasting Model Training & Comparison

This directory contains 4 Jupyter notebooks for training and comparing different weather forecasting models.

## 📊 Models

1. **Transformer** - Multi-head attention (already trained)
2. **ARIMA** - Classical univariate time series
3. **VARIMA/VAR** - Multivariate time series
4. **LSTM** - Recurrent neural network

## 🚀 Workflow

### Step 1: Train ARIMA (Local - CPU Friendly)
```bash
jupyter notebook train_arima.ipynb
```
- **Time**: ~10-20 minutes on CPU
- **Output**: `models/arima_*.pkl` (3 files)
- Run all cells to train 3 ARIMA models (one per target variable)

### Step 2: Train VARIMA (Local - CPU Friendly)
```bash
jupyter notebook train_varima.ipynb
```
- **Time**: ~20-40 minutes on CPU
- **Output**: `models/varima_model.pkl`, `models/varima_scaler.pkl`
- Single multivariate model capturing variable relationships

### Step 3: Train LSTM (Colab - GPU Recommended)
```bash
# Upload train_lstm.ipynb to Google Colab
# Enable GPU: Runtime → Change runtime type → GPU (T4)
```
- **Time**: ~30-45 minutes on GPU (2-6 hours on CPU)
- **Output**: `models/lstm_best_model.pth`, `models/lstm_model_weights.pth`, `models/lstm_scaler.pkl`
- After training, download model files and place in local `models/` directory

### Step 4: Compare All Models (Local - CPU Friendly)
```bash
jupyter notebook model_comparison.ipynb
```
- **Prerequisites**: All models trained and saved in `models/`
- **Output**: Comprehensive comparison with metrics, plots, and recommendations

## 📁 Directory Structure

```
notebooks/
├── train_arima.ipynb          # ARIMA training
├── train_varima.ipynb         # VARIMA training
├── train_lstm.ipynb           # LSTM training (for Colab)
├── model_comparison.ipynb     # Comparative analysis
├── train_arima.py             # Jupytext source (ARIMA)
├── train_varima.py            # Jupytext source (VARIMA)
├── train_lstm.py              # Jupytext source (LSTM)
├── model_comparison.py        # Jupytext source (Comparison)
└── README.md                  # This file

models/
├── multivariate_model_weights.pth  # Transformer (already trained)
├── model_config.json               # Transformer config
├── scaler.pkl                      # Transformer scaler
├── arima_*.pkl                     # ARIMA models (after Step 1)
├── varima_model.pkl                # VARIMA model (after Step 2)
├── lstm_model_weights.pth          # LSTM model (after Step 3)
└── model_comparison_results.json   # Comparison results (after Step 4)

data/
└── Weather_Data_1980_2024(hourly).csv  # Dataset
```

## 🔧 Requirements

Install dependencies:
```bash
pip install torch pandas numpy matplotlib seaborn scikit-learn statsmodels pmdarima joblib tqdm tabulate jupytext
```

## 📊 Expected Results

### Performance (Approximate)
| Model       | MSE       | Training Time | Hardware   |
|-------------|-----------|---------------|------------|
| Transformer | ~0.002    | 2 hours       | GPU        |
| ARIMA       | ~0.005-01 | 15 mins       | CPU        |
| VARIMA      | ~0.004-08 | 30 mins       | CPU        |
| LSTM        | ~0.002-03 | 40 mins (GPU) | GPU/CPU    |

### Outputs After Comparison
- Metrics tables (MSE, MAE, RMSE, MAPE)
- Per-variable performance breakdown
- Side-by-side prediction plots
- Forecast horizon degradation analysis
- Inference time comparison
- Model recommendations

## 💡 Tips

1. **ARIMA & VARIMA**: Safe to run locally on CPU
2. **LSTM**: Strongly recommended to use Google Colab with GPU
3. **Comparison**: Only run after all models are trained
4. **Jupytext**: `.py` files are source, `.ipynb` are generated (you can edit either)

## 🐛 Troubleshooting

### LSTM Training on Colab
If uploading dataset to Colab, modify `config['data_path']`:
```python
'data_path': '/content/Weather_Data_1980_2024(hourly).csv'
```

### Missing Models Error
Ensure all required model files exist in `models/` before running comparison:
- `multivariate_model_weights.pth` (Transformer)
- `arima_*.pkl` (3 files)
- `varima_model.pkl`
- `lstm_model_weights.pth`

### Out of Memory
Reduce batch size in LSTM config:
```python
'batch_size': 32  # or lower
```

## 📧 Questions?

Review the inline documentation in each notebook for detailed explanations of:
- Model architectures
- Training procedures
- Evaluation metrics
- Visualization outputs
