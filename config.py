# /config.py

# --- Parámetros Generales ---
REFRESH_SECONDS = 150
MIN_24H_VOLUME_USD = 5_000_000 # <-- Esta es la variable del error
TIMEFRAME_ANALYSIS = '5m'
WATCHLIST_SIZE = 10 # <-- El Top 10 de sospechosos

# --- Parámetros de Análisis Profundo (FASE 2) ---
REVERSAL_TIMEFRAME = '15m'
OHLCV_LIMIT = 100
ACCEL_LOOKBACK_CANDLES = 3
ACCEL_VOLUME_MULT = 2.0
ACCEL_CHANGE_PCT = 1.5
REVERSAL_LOOKBACK_MINS = 30
REVERSAL_VOLUME_MULT = 2.5
REVERSAL_WICK_MULT = 1.5
TELEGRAM_SCORE_THRESHOLD = 0.2
AI_CONFIDENCE_THRESHOLD = 0.1


# --- Parámetros para SL y TP basados en ATR ---
ATR_PERIOD = 14      # Período para calcular el ATR en velas de 1h
TAKE_PROFIT_RR = 1.5 # Ratio de Ganancia (1.5R)
STOP_LOSS_RR = 1.0   # Ratio de Pérdida (1R)

# --- CONFIGURACIÓN DE TELEGRAM ---
TELEGRAM_TOKEN = "7732548537:AAEJvyfq9ErspOa-insph0NULb_7FUeI91g"
TELEGRAM_CHAT_ID = "714501781"