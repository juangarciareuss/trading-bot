import ccxt
import pandas as pd
import time
from datetime import datetime, timezone, timedelta
import warnings

# --- CONFIGURACIÓN ---
warnings.simplefilter(action='ignore', category=FutureWarning)
pd.options.mode.chained_assignment = None

# --- Parámetros del Radar de Momentum (FASE 1) ---
MIN_24H_VOLUME_USD = 5_000_000
WATCHLIST_SIZE = 10
REFRESH_SECONDS = 300
MOMENTUM_ACCEL_FACTOR = 2.5 #

# --- Parámetros del Radar Rápido (El Vigilante) ---
FAST_RADAR_LOOKBACK_MINUTES = 60 # Mirar la volatilidad de la última hora
FAST_RADAR_WATCHLIST_SIZE = 10   # Tomar el Top 10 de este radar

# --- Parámetros del Radar Profundo (Los Exploradores) ---
DEEP_RADAR_INTERVAL_MINUTES = 30 # Ejecutar este radar lento cada 30 minutos
DEEP_RADAR_WATCHLIST_SIZE = 5    # Tomar el Top 5 de este radar


# --- Parámetros de Análisis Profundo (FASE 2) ---
TIMEFRAME_ACCEL = '5m'
TIMEFRAME_REVERSAL = '15m'
OHLCV_LIMIT = 100

# Parámetros para el Ranking de Aceleración
ACCEL_LOOKBACK_CANDLES = 3
ACCEL_VOLUME_MULT = 2.0
ACCEL_CHANGE_PCT = 1.5

# Parámetros para el Ranking de Reversión
REVERSAL_LOOKBACK_MINS = 30
REVERSAL_VOLUME_MULT = 2.5
REVERSAL_WICK_MULT = 1.5

# --- Inicialización del Exchange ---
exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})

# -----------------------------------------------------------------------------
# --- FUNCIONES AUXILIARES ---
# -----------------------------------------------------------------------------
def resample_dataframe(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Convierte un DataFrame de OHLCV a un timeframe mayor."""
    df_resampled = df.resample(timeframe).agg({
        'o': 'first', 'h': 'max', 'l': 'min', 'c': 'last', 'v': 'sum'
    })
    df_resampled.dropna(inplace=True)
    return df_resampled

# -----------------------------------------------------------------------------
# --- FUNCIÓN DE FASE 1: RADAR INSTANTÁNEO ---
# -----------------------------------------------------------------------------
# REEMPLAZA TU FUNCIÓN run_phase_1_radar ENTERA POR ESTA
def run_phase_1_radar(candle_history: dict) -> tuple[list, dict]:
    """
    Escanea la aceleración de momentum en todos los activos líquidos.
    """
    print("Fase 1: Escaneando aceleración de momentum en activos líquidos...")
    now = datetime.now(timezone.utc)

    # Paso A: Obtener todos los activos con liquidez
    all_tickers = exchange.fetch_tickers()
    liquid_symbols = [
        symbol for symbol, ticker in all_tickers.items()
        if symbol.endswith('/USDT:USDT') and ticker.get('quoteVolume', 0) > MIN_24H_VOLUME_USD
    ]

    if not liquid_symbols:
        print("  -> No se encontraron activos con liquidez suficiente.")
        return [], candle_history

    # Paso B: Actualizar el historial de velas
    for i, symbol in enumerate(liquid_symbols):
        print(f"  -> Actualizando historial {i+1}/{len(liquid_symbols)}: {symbol}", end='\r')
        try:
            # Pedimos 5 velas para asegurar que tenemos las últimas 4 cerradas
            ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME_ACCEL, limit=5)
            if len(ohlcv) < 5: continue

            # Guardamos las últimas 4 velas cerradas
            closed_candles = ohlcv[-5:-1]
            candle_history[symbol] = closed_candles
        except Exception:
            continue

    print("\n  -> Historial de velas actualizado.")

    # Paso C: Calcular la aceleración para los activos con historial completo
    acceleration_candidates = []
    for symbol, history in candle_history.items():
        if len(history) == 4: # Necesitamos 4 velas
            try:
                newest_candle = history[3]
                previous_candles = history[0:3]

                if newest_candle[1] > 0: # Open price > 0
                    new_momentum = ((newest_candle[4] - newest_candle[1]) / newest_candle[1]) * 100
                else: continue

                previous_momentums = []
                for c in previous_candles:
                    if c[1] > 0:
                        previous_momentums.append(((c[4] - c[1]) / c[1]) * 100)

                if not previous_momentums: continue
                avg_momentum = sum(previous_momentums) / len(previous_momentums)

                if avg_momentum != 0 and abs(new_momentum) > abs(avg_momentum) * MOMENTUM_ACCEL_FACTOR:
                     acceleration_candidates.append({'symbol': symbol, 'acceleration': new_momentum})
            except Exception:
                continue

    if not acceleration_candidates:
        print(f"  -> Construyendo historial... ({len(candle_history)}/{len(liquid_symbols)} activos con datos). Se necesitan ~20 min para el historial completo.")
        return [], candle_history

    # Crear watchlist con el Top 10
    sorted_by_accel = sorted(acceleration_candidates, key=lambda x: abs(x['acceleration']), reverse=True)
    watchlist = [cand['symbol'] for cand in sorted_by_accel[:WATCHLIST_SIZE]]

    if watchlist:
        print(f"  -> {len(watchlist)} 'sospechosos' con alta aceleración identificados.")
        for cand in sorted_by_accel[:3]:
            print(f"    - {cand['symbol']}: Aceleración de Momentum: {cand['acceleration']:+.2f}%")

    return watchlist, candle_history

# -----------------------------------------------------------------------------
# --- FUNCIÓN DE FASE 2: ANÁLISIS PROFUNDO ---
# -----------------------------------------------------------------------------
def run_phase_2_analysis(watchlist: list) -> tuple[list, list]:
    """
    Analiza la watchlist para encontrar señales de aceleración y reversión.
    """
    acceleration_candidates = []
    reversal_signals = []
    now = datetime.now(timezone.utc)

    for symbol in watchlist:
        try:
            ohlcv_5m = exchange.fetch_ohlcv(symbol, TIMEFRAME_ACCEL, limit=OHLCV_LIMIT)
            df_5m = pd.DataFrame(ohlcv_5m, columns=['ts','o','h','l','c','v'])
            if df_5m.empty: continue
            
            df_5m['ts'] = pd.to_datetime(df_5m['ts'], unit='ms', utc=True)
            df_5m.set_index('ts', inplace=True)
            df_5m_closed = df_5m.iloc[:-1].copy()

            # --- 2.1 ANÁLISIS DE ACELERACIÓN ---
            if len(df_5m_closed) > ACCEL_LOOKBACK_CANDLES:
                lookback_candles = df_5m_closed.tail(ACCEL_LOOKBACK_CANDLES)
                historical_candles = df_5m_closed.head(-ACCEL_LOOKBACK_CANDLES)
                avg_volume_5m = historical_candles['v'].mean()
                if avg_volume_5m > 0:
                    change_15m = (lookback_candles['c'].iloc[-1] - lookback_candles['o'].iloc[0]) / lookback_candles['o'].iloc[0]
                    volume_mult = lookback_candles['v'].mean() / avg_volume_5m
                    score = abs(change_15m) * volume_mult
                    is_strong_signal = volume_mult > ACCEL_VOLUME_MULT and abs(change_15m) * 100 > ACCEL_CHANGE_PCT
                    acceleration_candidates.append({
                        'symbol': symbol, 'score': score, 'change_15m': change_15m,
                        'vol_mult': volume_mult, 'is_strong': is_strong_signal
                    })

            # --- 2.2 ANÁLISIS DE REVERSIÓN ---
            df_15m_closed = resample_dataframe(df_5m_closed, TIMEFRAME_REVERSAL)
            cutoff_time = now - timedelta(minutes=REVERSAL_LOOKBACK_MINS)
            recent_candles_15m = df_15m_closed[df_15m_closed.index > cutoff_time]
            if not recent_candles_15m.empty:
                historical_volume_15m = df_15m_closed[df_15m_closed.index <= cutoff_time]['v'].mean()
                for i in range(1, len(recent_candles_15m)):
                    candle, prev_candle = recent_candles_15m.iloc[i], recent_candles_15m.iloc[i-1]
                    if historical_volume_15m > 0 and candle['v'] > historical_volume_15m * REVERSAL_VOLUME_MULT:
                        if candle['c'] < prev_candle['o'] and candle['o'] > prev_candle['c'] and prev_candle['c'] > prev_candle['o']:
                            reversal_signals.append({'symbol': symbol, 'time': candle.name, 'pattern': 'Envolvente Bajista 📉'})
                        elif candle['c'] > prev_candle['o'] and candle['o'] < prev_candle['c'] and prev_candle['c'] < prev_candle['o']:
                            reversal_signals.append({'symbol': symbol, 'time': candle.name, 'pattern': 'Envolvente Alcista 📈'})
                        body_size = abs(candle['c'] - candle['o'])
                        if body_size > 1e-9:
                            upper_wick, lower_wick = candle['h'] - max(candle['o'], candle['c']), min(candle['o'], candle['c']) - candle['l']
                            if upper_wick > body_size * REVERSAL_WICK_MULT: reversal_signals.append({'symbol': symbol, 'time': candle.name, 'pattern': 'Mecha de Rechazo Bajista 📍'})
                            elif lower_wick > body_size * REVERSAL_WICK_MULT: reversal_signals.append({'symbol': symbol, 'time': candle.name, 'pattern': 'Mecha de Rechazo Alcista 🔨'})
        except Exception:
            continue
    return acceleration_candidates, reversal_signals

# -----------------------------------------------------------------------------
# --- FUNCIÓN DE REPORTE ---
# -----------------------------------------------------------------------------
def print_report(acceleration_candidates: list, reversal_signals: list):
    """Imprime los rankings de aceleración y reversión."""
    now = datetime.now(timezone.utc)
    
    print("\n== 🚀 RANKING DE ACELERACIÓN (PREVIO A CLÍMAX) ==")
    if acceleration_candidates:
        sorted_accel = sorted(acceleration_candidates, key=lambda x: x['score'], reverse=True)
        for i, cand in enumerate(sorted_accel[:5]):
            signal_marker = "🔥" if cand['is_strong'] else " "
            direction = "ALCISTA 🟢" if cand['change_15m'] > 0 else "BAJISTA 🔴"
            print(f"{signal_marker} {i+1}. {cand['symbol']}: {direction} | Score: {cand['score']:.2f} | Acel. 15m: {cand['change_15m']*100:+.2f}% | Vol: {cand['vol_mult']:.1f}x prom.")
    else:
        print("(No se han podido analizar candidatos de la watchlist)")

    print("\n== 🚨 RANKING DE REVERSIONES (CLÍMAX RECIENTE) ==")
    if reversal_signals:
        unique_signals = {f"{s['symbol']}_{s['pattern']}_{s['time'].isoformat()}": s for s in sorted(reversal_signals, key=lambda x: x['time'], reverse=True)}.values()
        for signal in list(unique_signals)[:5]:
            time_ago = (now - signal['time']).total_seconds() / 60
            print(f"- {signal['pattern']} en {signal['symbol']} (hace {time_ago:.0f} min)")
    else:
        print("(No se han detectado patrones de reversión en la watchlist)")

# -----------------------------------------------------------------------------
# --- BUCLE PRINCIPAL DEL CAZADOR ---
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"--- 🔥 Cazador de Clímax (Radar de Aceleración de Momentum) ---")
    candle_history = {} # <-- Se crea la "memoria" aquí

    while True:
        try:
            start_time = time.monotonic()
            now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n--- Análisis a las {now_str} UTC ---")

            # La función ahora usa y devuelve 'candle_history'
            watchlist, candle_history = run_phase_1_radar(candle_history)

            if watchlist:
                acceleration, reversals = run_phase_2_analysis(watchlist)
                print_report(acceleration, reversals)

            print(f"\nEsperando {REFRESH_SECONDS} segundos ({REFRESH_SECONDS//60} minutos) para el siguiente análisis...")
            
            # --- CÁLCULO DE TIEMPO DE CICLO EXACTO ---
            end_time = time.monotonic()
            duration = end_time - start_time
            sleep_time = REFRESH_SECONDS - duration

            if sleep_time > 0:
                print(f"\nAnálisis completado en {duration:.1f} segundos. Esperando {sleep_time:.1f} segundos...")
                time.sleep(sleep_time)
            else:
                print(f"\nADVERTENCIA: El análisis tardó {duration:.1f} segundos, más que el ciclo de {REFRESH_SECONDS} segundos.")
            # --- FIN DEL BLOQUE ---


        except KeyboardInterrupt:
            print("\nCazador detenido."); break
        except Exception as e:
            print(f"Error en el bule principal: {e}"); time.sleep(60)