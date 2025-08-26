# /live_ia_engine.py
import pandas as pd
import joblib
import warnings
from utils import exchange
import config

warnings.simplefilter(action='ignore', category=FutureWarning)
pd.options.mode.chained_assignment = None
MODEL_FILE = "topfinder_model.joblib"

try:
    model = joblib.load(MODEL_FILE)
    print(f"✅ Modelo de IA '{MODEL_FILE}' cargado.")
except FileNotFoundError:
    print(f"❌ ERROR CRÍTICO: No se encontró '{MODEL_FILE}'.")
    model = None

def calculate_rsi(series, length=14):
    delta = series.diff(1)
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(com=length - 1, min_periods=length).mean()
    avg_loss = loss.ewm(com=length - 1, min_periods=length).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def fetch_live_data(symbol):
    timeframes = ['1w', '1d', '4h', '1h', '5m']
    data = {}
    try:
        for tf in timeframes:
            ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=200)
            if not ohlcv: return None
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            data[tf] = df
        return data
    except Exception:
        return None

def create_live_features(altcoin_data, btc_data, eth_data):
    df = altcoin_data['1h'].copy()
    df['change_1h'] = df['close'].pct_change(periods=1)
    df['change_4h'] = df['close'].pct_change(periods=4)
    df['change_12h'] = df['close'].pct_change(periods=12)
    df['change_24h'] = df['close'].pct_change(periods=24)
    df['distance_from_ma_24h'] = (df['close'] - df['close'].rolling(24).mean()) / df['close']
    for tf_context in ['1w', '1d', '4h']:
        if tf_context in altcoin_data:
            altcoin_data[tf_context][f'rsi_{tf_context}'] = calculate_rsi(altcoin_data[tf_context]['close'], length=14)
    altcoin_data['5m']['volume_spike_5m'] = altcoin_data['5m']['volume'] / altcoin_data['5m']['volume'].rolling(window=12).mean()
    df['btc_change_24h'] = btc_data['1h']['close'].pct_change(periods=24)
    df['eth_change_24h'] = eth_data['1h']['close'].pct_change(periods=24)
    for tf_context in ['1w', '1d', '4h']:
        if tf_context in altcoin_data:
            df = pd.merge_asof(df.sort_index(), altcoin_data[tf_context][[f'rsi_{tf_context}']].sort_index(), on='timestamp', direction='backward')
    df = pd.merge_asof(df.sort_index(), altcoin_data['5m'][['volume_spike_5m']].sort_index(), on='timestamp', direction='backward')
    return df.iloc[-1:]

# REEMPLAZA LA FUNCIÓN get_ai_prediction ENTERA POR ESTA

def get_ai_prediction(symbol, btc_data, eth_data):
    """
    Orquesta el proceso y devuelve un diccionario con la predicción de la IA,
    el precio de entrada, y los niveles de SL y TP sugeridos.
    """
    if not model: return None

    altcoin_data = fetch_live_data(symbol)
    if altcoin_data is None: return None

    live_features_row = create_live_features(altcoin_data, btc_data, eth_data)

    # --- CÁLCULO DE SL/TP ---
    # Usamos el ATR de 1h para medir la volatilidad
    atr_series = calculate_atr(altcoin_data['1h']['high'], altcoin_data['1h']['low'], altcoin_data['1h']['close'], length=config.ATR_PERIOD)
    current_atr = atr_series.iloc[-1]
    entry_price = altcoin_data['1h']['close'].iloc[-1]

    # Asumimos una operación SHORT basada en la estrategia
    stop_loss_price = entry_price + (current_atr * config.STOP_LOSS_RR)
    take_profit_price = entry_price - (current_atr * config.TAKE_PROFIT_RR)
    # --- FIN DE CÁLCULO ---

    features_for_prediction = [col for col in model.feature_name_ if col in live_features_row.columns]
    live_features_row = live_features_row[features_for_prediction]

    if live_features_row.isnull().values.any(): return None

    prediction_prob = model.predict_proba(live_features_row)[0]
    probability_of_win = prediction_prob[1]

    # Devolvemos un diccionario con toda la información
    return {
        "win_probability": probability_of_win,
        "entry_price": entry_price,
        "stop_loss": stop_loss_price,
        "take_profit": take_profit_price
    }

def calculate_atr(high, low, close, length=14):
    """Calcula el ATR manualmente."""
    import numpy as np
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    tr = pd.DataFrame({'hl': high_low, 'hc': high_close, 'lc': low_close}).max(axis=1)
    return tr.ewm(com=length - 1, min_periods=length).mean()