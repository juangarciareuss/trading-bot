import ccxt
import pandas as pd
import numpy as np
import joblib
import os
import time
from datetime import datetime, timezone
import warnings
import traceback

# --- CONFIGURACIÓN ---
warnings.simplefilter(action='ignore', category=FutureWarning)
try:
    antifomo_model = joblib.load("antifomo_model.pkl")
except FileNotFoundError:
    print("❌ Error: No se encontró el archivo 'antifomo_model.pkl'. Asegúrate de que exista.")
    exit()

REFRESH_SECONDS = 300  # 5 minutos
TOP_N_TO_ANALYZE = 15  # Analizar los 15 principales ganadores
PROB_THRESHOLD_ALERTA = 0.85 # Umbral para considerar una señal como "activa"

# Umbrales para el diagnóstico
RSI_EXTREMO = 80.0
VOLUMEN_SPIKE = 3.0
DISTANCIA_MEDIA_EXTREMA = 0.20 # 20% por encima de la media

exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})

# --- FUNCIONES ---
def get_live_features(symbol):
    try:
        data = {}
        timeframes = {'1d': 26, '4h': 26, '1h': 26, '5m': 13}
        for tf, min_candles in timeframes.items():
            ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=50)
            if len(ohlcv) < min_candles: return None
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms'); df.set_index('timestamp', inplace=True); data[tf] = df
        
        df = data['1h'].copy()
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
        return df[feature_cols].iloc[-1:]
    except Exception:
        return None

def get_short_opportunity_analysis(features, prob):
    """Analiza una señal de short y devuelve un estado y un diagnóstico."""
    
    rsi_4h = features['rsi_4h'].iloc[-1]
    dist_ma = features['distance_from_ma_24h'].iloc[-1]
    vol_spike = features['volume_spike_5m'].iloc[-1]

    # Condición 1: Es una señal de élite, lista para entrar
    if prob >= PROB_THRESHOLD_ALERTA:
        return "🟢 BUENO PARA ENTRAR (SEÑAL ACTIVA)", "Todos los indicadores de agotamiento están alineados.", 0

    # Condición 2: El momento ya pasó, es demasiado tarde
    if prob < 0.40 and rsi_4h > RSI_EXTREMO:
        return "❌ DEMASIADO TARDE", "El pico de euforia parece haber pasado y el momentum de reversión se debilita.", 2

    # Condición 3: Señal en desarrollo, estamos anticipados
    diagnosis = []
    if rsi_4h < RSI_EXTREMO:
        diagnosis.append(f"el RSI 4H ({rsi_4h:.1f}) aún no es extremo (> {RSI_EXTREMO})")
    if vol_spike < VOLUMEN_SPIKE:
        diagnosis.append(f"el volumen 5m ({vol_spike:.1f}x) no muestra un pico de clímax (> {VOLUMEN_SPIKE}x)")
    if dist_ma < DISTANCIA_MEDIA_EXTREMA:
        diagnosis.append("el precio no está suficientemente sobreextendido de su media")
    
    if not diagnosis:
        diagnosis.append("el patrón general no es lo suficientemente claro para el modelo.")

    return "🟡 ANTICIPADO (SEÑAL EN DESARROLLO)", "Falta confirmación en: " + ", ".join(diagnosis) + ".", 1

# --- BUCLE PRINCIPAL DEL MONITOR ---
if __name__ == "__main__":
    while True:
        try:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("--- 🎯 Cazador de Señales Anti-FOMO (Shorts) ---")
            print(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*80)

            all_tickers = exchange.fetch_tickers()
            top_gainers = sorted(
                [t for t in all_tickers.values() if t['symbol'].endswith('/USDT:USDT') and t.get('percentage')],
                key=lambda t: t['percentage'],
                reverse=True
)
            

            # --- INICIO DEL BLOQUE DE DIAGNÓSTICO ---
            print("\n" + "-"*40)
            print("Diagnóstico del Mercado (Top Ganador):")
            if top_gainers:
                top_coin = top_gainers[0]
                top_symbol_clean = top_coin['symbol'].replace(':USDT','')
                top_percentage = top_coin['percentage']

                print(f"-> Moneda con mayor alza: {top_symbol_clean} ({top_percentage:.2f}%)")

                # Usamos 15% como nuestra referencia de "alta volatilidad"
                if top_percentage < 15.0:
                    print("-> Veredicto: El mercado está en BAJA VOLATILIDAD. Es normal no encontrar candidatos para una señal Anti-FOMO.")
                else:
                    print("-> Veredicto: El mercado SÍ tiene volatilidad. El problema probablemente es la falta de historial en los candidatos.")
            else:
                print("No se encontraron datos de tickers.")
            print("-" * 40 + "\n")
            # --- FIN DEL BLOQUE DE DIAGNÓSTICO ---


            candidates = []
            print("Analizando los principales ganadores del mercado...")
            for ticker in top_gainers[:TOP_N_TO_ANALYZE]:
                symbol = ticker['symbol'].replace(':USDT', '')
                features = get_live_features(symbol)
                
                if features is not None and not features.isnull().values.any():
                    prob = antifomo_model.predict_proba(features)[0][1]
                    status, diagnosis, order = get_short_opportunity_analysis(features, prob)
                    candidates.append({
                        'symbol': symbol, 'prob': prob, 'status': status,
                        'diagnosis': diagnosis, 'order': order,
                        'features': features.iloc[0].to_dict()
                    })
            
            if candidates:
                # Ordenar por estado y luego por probabilidad
                sorted_candidates = sorted(candidates, key=lambda x: (x['order'], -x['prob']))
                for cand in sorted_candidates:
                    print(f"\n{cand['order']+1}. {cand['symbol']}")
                    print(f"   - ESTADO: {cand['status']}")
                    print(f"   - Confianza IA: {cand['prob']*100:.1f}%")
                    print(f"   - Diagnóstico: {cand['diagnosis']}")
                    # Imprimir data clave para contexto
                    f = cand['features']
                    print(f"   - Data Clave -> Var 24h: {f['change_24h']*100:+.1f}% | RSI 4H: {f['rsi_4h']:.1f} | Dist. Media: {f['distance_from_ma_24h']*100:+.1f}% | Vol 5m Spike: {f['volume_spike_5m']:.1f}x")
            else:
                print("No se encontraron candidatos para analizar.")

            print("\n" + "="*80)
            print(f"Próxima actualización en {REFRESH_SECONDS} segundos...")
            time.sleep(REFRESH_SECONDS)

        except KeyboardInterrupt:
            print("\nMonitor detenido."); break
        except Exception as e:
            print(f"\n❌ Error en el bucle del monitor: {e}\n{traceback.format_exc()}"); time.sleep(60)