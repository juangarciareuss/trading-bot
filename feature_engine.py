# feature_engine.py (Versión con Escaneo Avanzado de Momentum)

import ccxt
import pandas as pd
import numpy as np

exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})

# LISTA DE MONEDAS A MONITOREAR (puedes ampliarla)
SYMBOLS_TO_SCAN = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'DOGE/USDT', 
    'AVAX/USDT', 'LINK/USDT', 'DOT/USDT', 'ADA/USDT', 'UNI/USDT', 'ICP/USDT',
    'NEAR/USDT', 'ATOM/USDT', 'OP/USDT', 'ARB/USDT', 'RNDR/USDT', 'AAVE/USDT'
]

def get_live_features(symbol):
    """
    Función centralizada y única para obtener las features de una moneda.
    """
    try:
        data = {}
        # Usamos 1w también como pediste para un análisis más completo
        timeframes = {'1w': 50, '1d': 26, '4h': 26, '1h': 26, '5m': 13}
        for tf, min_candles in timeframes.items():
            ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=50)
            if len(ohlcv) < min_candles:
                return None, None
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            data[tf] = df
        
        df = data['1h'].copy()
        precio_actual = df['close'].iloc[-1]
        
        df['change_24h'] = df['close'].pct_change(periods=24)
        df['change_1h'] = df['close'].pct_change(periods=1)
        ma_24h = df['close'].rolling(24).mean()
        df['distance_from_ma_24h'] = (df['close'] - ma_24h) / ma_24h
        
        # --- BLOQUE CORREGIDO ---
        # Las siguientes líneas ahora están correctamente indentadas dentro del bucle 'for'
        for tf_context in ['4h', '1d', '1w']:
            delta = data[tf_context]['close'].diff(1)
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            data[tf_context][f'rsi_{tf_context}'] = 100 - (100 / (1 + rs))
        
        data['5m']['volume_spike_5m'] = data['5m']['volume'] / data['5m']['volume'].rolling(window=12).mean()
        
        df = pd.merge_asof(df.sort_index(), data['4h'][['rsi_4h']].sort_index(), on='timestamp', direction='backward')
        df = pd.merge_asof(df.sort_index(), data['1d'][['rsi_1d']].sort_index(), on='timestamp', direction='backward')
        df = pd.merge_asof(df.sort_index(), data['1w'][['rsi_1w']].sort_index(), on='timestamp', direction='backward')
        df = pd.merge_asof(df.sort_index(), data['5m'][['volume_spike_5m']].sort_index(), on='timestamp', direction='backward')
        
        feature_cols = ['change_24h', 'change_1h', 'distance_from_ma_24h', 'rsi_4h', 'rsi_1d', 'rsi_1w', 'volume_spike_5m']
        return df[feature_cols].iloc[-1:], precio_actual
    except Exception as e:
        print(f"Error en get_live_features para {symbol}: {e}")
        return None, None
    
def advanced_market_scan():
    """
    Escanea una lista predefinida de símbolos, buscando momentum reciente explosivo.
    Devuelve una lista de diccionarios con el símbolo y su precio.
    """
    print(f"🔬 Realizando escaneo avanzado de momentum en {len(SYMBOLS_TO_SCAN)} monedas...")
    candidates = []
    
    # Nuevo filtro: Buscamos monedas con una subida de más del 10% en las últimas 4 horas
    MOMENTUM_THRESHOLD = 0.10 # 10%
    MOMENTUM_PERIOD = 4       # en 4 horas

    for symbol in SYMBOLS_TO_SCAN:
        try:
            # Descargamos solo las últimas velas de 1h necesarias para el cálculo
            ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=MOMENTUM_PERIOD + 2)
            if len(ohlcv) < MOMENTUM_PERIOD + 1:
                continue
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Calculamos el cambio en las últimas 4 horas
            change_4h = (df['close'].iloc[-1] - df['close'].iloc[- (MOMENTUM_PERIOD + 1)]) / df['close'].iloc[- (MOMENTUM_PERIOD + 1)]
            
            if change_4h > MOMENTUM_THRESHOLD:
                print(f"  -> ¡Candidato detectado! {symbol} con +{change_4h*100:.1f}% de subida en las últimas {MOMENTUM_PERIOD}h.")
                candidates.append({'symbol': symbol, 'price': df['close'].iloc[-1]})
        except Exception:
            continue # Si falla una moneda, continuamos con la siguiente
    
    return candidates