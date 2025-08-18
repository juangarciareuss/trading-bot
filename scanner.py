# scanner.py (Versión Final - Motor Central de Análisis)

import ccxt
import pandas as pd
import numpy as np
import joblib
import warnings

# --- CONFIGURACIÓN Y OBJETOS GLOBALES ---
warnings.simplefilter(action='ignore', category=FutureWarning)
try:
    antifomo_model = joblib.load("antifomo_model.pkl")
except FileNotFoundError as e:
    print(f"❌ Error: No se encontró 'antifomo_model.pkl'.")
    exit()

exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})

# Umbrales
ANTIFOMO_PROB_THRESHOLD = 0.85
MIN_CHANGE_24H_UP = 15.0
MAX_NEGATIVE_FUNDING_RATE = -0.0050
RSI_EXTREMO = 80.0
VOLUMEN_SPIKE = 3.0
DISTANCIA_MEDIA_EXTREMA = 0.20

# --- FUNCIONES DE ANÁLISIS (Herramientas para todo el sistema) ---
def get_live_features(symbol):
    try:
        data = {}
        timeframes = {'1d': 26, '4h': 26, '1h': 26, '5m': 13}
        for tf, min_candles in timeframes.items():
            ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=50)
            if len(ohlcv) < min_candles: return None, None
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms'); df.set_index('timestamp', inplace=True); data[tf] = df
        
        df = data['1h'].copy()
        precio_actual = df['close'].iloc[-1]
        
        df['change_24h'] = df['close'].pct_change(periods=24); df['change_1h'] = df['close'].pct_change(periods=1)
        ma_24h = df['close'].rolling(24).mean(); df['distance_from_ma_24h'] = (df['close'] - ma_24h) / ma_24h

        for tf_context in ['4h', '1d']:
            delta = data[tf_context]['close'].diff(1); gain = delta.where(delta > 0, 0); loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14).mean(); avg_loss = loss.rolling(window=14).mean(); rs = avg_gain / avg_loss
            data[tf_context][f'rsi_{tf_context}'] = 100 - (100 / (1 + rs))
        data['5m']['volume_spike_5m'] = data['5m']['volume'] / data['5m']['volume'].rolling(window=12).mean()
        df = pd.merge_asof(df.sort_index(), data['4h'][['rsi_4h']].sort_index(), on='timestamp', direction='backward')
        df = pd.merge_asof(df.sort_index(), data['1d'][['rsi_1d']].sort_index(), on='timestamp', direction='backward')
        df = pd.merge_asof(df.sort_index(), data['5m'][['volume_spike_5m']].sort_index(), on='timestamp', direction='backward')
        
        feature_cols = ['change_24h', 'change_1h', 'distance_from_ma_24h', 'rsi_4h', 'rsi_1d', 'volume_spike_5m']
        return df[feature_cols].iloc[-1:], precio_actual
    except Exception:
        return None, None

def get_atr_value(symbol):
    ATR_TIMEFRAME = '4h'; ATR_PERIOD = 14
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, ATR_TIMEFRAME, limit=ATR_PERIOD + 2)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        high_low = df['high'] - df['low']; high_close = np.abs(df['high'] - df['close'].shift()); low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr_value = true_range.ewm(alpha=1/ATR_PERIOD, adjust=False).mean().iloc[-1]
        return atr_value
    except Exception: return None

def get_bet_size(probabilidad_ia, atr_normalizado):
    if atr_normalizado == 0: return 150
    quality_score = probabilidad_ia / atr_normalizado
    if quality_score >= 40: return 350
    elif quality_score >= 30: return 300
    elif quality_score >= 20: return 250
    elif quality_score >= 10: return 200
    else: return 150

def get_short_opportunity_analysis(features, prob):
    rsi_4h = features['rsi_4h'].iloc[-1]; dist_ma = features['distance_from_ma_24h'].iloc[-1]; vol_spike = features['volume_spike_5m'].iloc[-1]
    if prob >= ANTIFOMO_PROB_THRESHOLD:
        return "🟢 BUENO PARA ENTRAR (SEÑAL ACTIVA)", "Todos los indicadores de agotamiento están alineados."
    if prob < 0.40 and rsi_4h > RSI_EXTREMO:
        return "❌ DEMASIADO TARDE", "El pico de euforia parece haber pasado y el momentum de reversión se debilita."
    diagnosis = []
    if rsi_4h < RSI_EXTREMO: diagnosis.append(f"RSI 4H ({rsi_4h:.1f}) no es extremo")
    if vol_spike < VOLUMEN_SPIKE: diagnosis.append(f"Volumen 5m ({vol_spike:.1f}x) es bajo")
    if dist_ma < DISTANCIA_MEDIA_EXTREMA: diagnosis.append("Precio no está sobreextendido")
    if not diagnosis: diagnosis.append("Patrón general no es claro")
    return "🟡 ANTICIPADO (EN DESARROLLO)", "Falta confirmación: " + ", ".join(diagnosis) + "."

def scan_for_shorts():
    """Escanea los mercados buscando únicamente señales de VENTA (Anti-FOMO)."""
    print("🔎 Escaneando mercados para señales Anti-FOMO (Shorts)...")
    short_signals = []
    try:
        tickers = exchange.fetch_tickers()
        print(f"📊 Analizando {len(tickers)} mercados...")
        
        for symbol_full, ticker in tickers.items():
            if not symbol_full.endswith('/USDT:USDT') or not ticker.get('percentage'):
                continue

            symbol = symbol_full.replace(':USDT','')
            change_24h = ticker['percentage']
            funding_rate = float(ticker.get('info', {}).get('fundingRate', 0))

            if change_24h > MIN_CHANGE_24H_UP:
                features, precio = get_live_features(symbol)
                if features is not None and not features.isnull().values.any():
                    prob = antifomo_model.predict_proba(features)[0][1]
                    if prob > ANTIFOMO_PROB_THRESHOLD:
                        if funding_rate < MAX_NEGATIVE_FUNDING_RATE:
                            print(f"  ❌ Señal para {symbol} DESCARTADA por Tasa de Financiación extrema.")
                            continue
                        
                        atr = get_atr_value(symbol)
                        if atr:
                            atr_normalizado = atr / precio
                            bet_size = get_bet_size(prob, atr_normalizado)
                            
                            # SEÑAL SIMPLIFICADA: Sin TP ni SL
                            short_signals.append({
                                'symbol': symbol,
                                'precio_entrada': float(precio),
                                'probabilidad_ia': float(prob),
                                'apuesta_sugerida': bet_size,
                                'atr_value': float(atr),
                                'tipo': 'short'
                            })
    except Exception as e:
        print(f"❌ Error en el scanner: {e}")
        
    return short_signals