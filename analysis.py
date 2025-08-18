import pandas as pd
from datetime import datetime, timezone
import config
from utils import exchange, resample_dataframe

def run_phase_2_analysis(watchlist: list) -> tuple[list, list]:
    """
    Analiza la watchlist para encontrar señales de aceleración y reversión.
    """
    acceleration_candidates = []
    reversal_signals = []
    now = datetime.now(timezone.utc)

    for symbol in watchlist:
        try:
            ohlcv_5m = exchange.fetch_ohlcv(symbol, config.TIMEFRAME_ANALYSIS, limit=config.OHLCV_LIMIT)
            df_5m = pd.DataFrame(ohlcv_5m, columns=['ts','o','h','l','c','v'])
            if df_5m.empty: continue
            
            df_5m['ts'] = pd.to_datetime(df_5m['ts'], unit='ms', utc=True)
            df_5m.set_index('ts', inplace=True)
            df_5m_closed = df_5m.iloc[:-1].copy()

            if len(df_5m_closed) > config.ACCEL_LOOKBACK_CANDLES:
                lookback_candles = df_5m_closed.tail(config.ACCEL_LOOKBACK_CANDLES)
                historical_candles = df_5m_closed.head(-config.ACCEL_LOOKBACK_CANDLES)
                avg_volume_5m = historical_candles['v'].mean()
                if avg_volume_5m > 0:
                    change_15m = (lookback_candles['c'].iloc[-1] - lookback_candles['o'].iloc[0]) / lookback_candles['o'].iloc[0]
                    volume_mult = lookback_candles['v'].mean() / avg_volume_5m
                    score = abs(change_15m) * volume_mult
                    is_strong_signal = volume_mult > config.ACCEL_VOLUME_MULT and abs(change_15m) * 100 > config.ACCEL_CHANGE_PCT
                    acceleration_candidates.append({
                        'symbol': symbol, 'score': score, 'change_15m': change_15m,
                        'vol_mult': volume_mult, 'is_strong': is_strong_signal
                    })

            df_15m_closed = resample_dataframe(df_5m_closed, config.REVERSAL_TIMEFRAME)
            cutoff_time = now - pd.Timedelta(minutes=config.REVERSAL_LOOKBACK_MINS)
            recent_candles_15m = df_15m_closed[df_15m_closed.index > cutoff_time]
            if not recent_candles_15m.empty:
                historical_volume_15m = df_15m_closed[df_15m_closed.index <= cutoff_time]['v'].mean()
                if not pd.isna(historical_volume_15m) and historical_volume_15m > 0:
                    for i in range(1, len(recent_candles_15m)):
                        candle, prev_candle = recent_candles_15m.iloc[i], recent_candles_15m.iloc[i-1]
                        if candle['v'] > historical_volume_15m * config.REVERSAL_VOLUME_MULT:
                            if candle['c'] < prev_candle['o'] and candle['o'] > prev_candle['c'] and prev_candle['c'] > prev_candle['o']:
                                reversal_signals.append({'symbol': symbol, 'time': candle.name, 'pattern': 'Envolvente Bajista 📉'})
                            elif candle['c'] > prev_candle['o'] and candle['o'] < prev_candle['c'] and prev_candle['c'] < prev_candle['o']:
                                reversal_signals.append({'symbol': symbol, 'time': candle.name, 'pattern': 'Envolvente Alcista 📈'})
                            body_size = abs(candle['c'] - candle['o'])
                            if body_size > 1e-9:
                                upper_wick, lower_wick = candle['h'] - max(candle['o'], candle['c']), min(candle['o'], candle['c']) - candle['l']
                                if upper_wick > body_size * config.REVERSAL_WICK_MULT: reversal_signals.append({'symbol': symbol, 'time': candle.name, 'pattern': 'Mecha de Rechazo Bajista 📍'})
                                elif lower_wick > body_size * config.REVERSAL_WICK_MULT: reversal_signals.append({'symbol': symbol, 'time': candle.name, 'pattern': 'Mecha de Rechazo Alcista 🔨'})
        except Exception:
            continue
    return acceleration_candidates, reversal_signals