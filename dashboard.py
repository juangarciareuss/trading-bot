import pandas as pd
import numpy as np
import os
import pandas_ta as ta
import warnings

# --- CONFIGURACIÓN ---
warnings.simplefilter(action='ignore', category=FutureWarning)
pd.options.mode.chained_assignment = None

SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'DOGE/USDT',
    'AVAX/USDT', 'LINK/USDT', 'DOT/USDT', 'ADA/USDT', 'UNI/USDT', 'ICP/USDT',
    'NEAR/USDT', 'ATOM/USDT', 'OP/USDT', 'ARB/USDT', 'RNDR/USDT', 'AAVE/USDT'
]
OUTPUT_FILE = "topfinder_dataset_elite.csv"
HORIZON_CANDLES = 48  # Corresponde a 48 horas en un timeframe de 1h
SCORE_THRESHOLD = 20

# --- FUNCIONES ---

def fetch_data_from_local_files(symbol):
    """Lee los datos históricos desde los archivos CSV locales."""
    timeframes = ['1w', '1d', '4h', '1h', '5m']
    data = {}
    print(f"  Leyendo datos locales para {symbol}...")
    
    base_path = "Backtest/data/historico"
    formatted_symbol = symbol.replace('/', '')

    for tf in timeframes:
        file_path = os.path.join(base_path, tf, f"{formatted_symbol}.csv")
        try:
            df = pd.read_csv(file_path)
            df.rename(columns={df.columns[0]: 'timestamp'}, inplace=True)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            df.columns = [col.lower() for col in df.columns]
            data[tf] = df
        except FileNotFoundError:
            print(f"    - ADVERTENCIA: No se encontró el archivo para {tf} en la ruta: {file_path}")
            if tf in ['1h', '5m', '4h']:
                 print(f"    - Faltan datos cruciales. Omitiendo {symbol}.")
                 return None
        except Exception as e:
            print(f"    - Error inesperado leyendo {file_path}: {e}")
            return None
    return data

def create_advanced_features(altcoin_data, btc_data, eth_data):
    """Calcula el set completo de features avanzadas."""
    print("    Calculando features...")
    df = altcoin_data['1h'].copy()
    
    df['ath'] = df['high'].cummax()
    df['change_1h'] = df['close'].pct_change(periods=1)
    df['change_4h'] = df['close'].pct_change(periods=4)
    df['change_12h'] = df['close'].pct_change(periods=12)
    df['change_24h'] = df['close'].pct_change(periods=24)
    df['distance_from_ma_24h'] = (df['close'] - df['close'].rolling(24).mean()) / df['close']

    for tf_context in ['1w', '1d', '4h']:
        if tf_context in altcoin_data:
            altcoin_data[tf_context][f'rsi_{tf_context}'] = ta.rsi(altcoin_data[tf_context]['close'], length=14)
    
    altcoin_data['5m']['volume_spike_5m'] = altcoin_data['5m']['volume'] / altcoin_data['5m']['volume'].rolling(window=12).mean()

    df['btc_change_24h'] = btc_data['1h']['close'].pct_change(periods=24)
    df['eth_change_24h'] = eth_data['1h']['close'].pct_change(periods=24)
    
    for tf_context in ['1w', '1d', '4h']:
         if tf_context in altcoin_data:
            df = pd.merge_asof(df.sort_index(), altcoin_data[tf_context][[f'rsi_{tf_context}']].sort_index(), on='timestamp', direction='backward')
    df = pd.merge_asof(df.sort_index(), altcoin_data['5m'][['volume_spike_5m']].sort_index(), on='timestamp', direction='backward')
    return df

def calculate_quality_score(row):
    """Asigna una puntuación a cada vela horaria basada en reglas ponderadas."""
    score = 0
    if 'rsi_4h' in row and not pd.isna(row['rsi_4h']):
        if row['rsi_4h'] > 85: score += 10
        elif row['rsi_4h'] > 75: score += 5
    if 'distance_from_ma_24h' in row and not pd.isna(row['distance_from_ma_24h']):
        if row['distance_from_ma_24h'] > 0.25: score += 10
        elif row['distance_from_ma_24h'] > 0.15: score += 5
    if row['close'] < (row['ath'] * 0.98): score += 5
    if 'volume_spike_5m' in row and not pd.isna(row['volume_spike_5m']):
        if row['volume_spike_5m'] > 3.0: score += 5
    if 'btc_change_24h' in row and not pd.isna(row['btc_change_24h']) and 'eth_change_24h' in row and not pd.isna(row['eth_change_24h']):
        if row['btc_change_24h'] > 0.04 and row['eth_change_24h'] > 0.04: score += 8
    return score

def define_target_48h(df):
    """Define el target: 1 si el precio es menor en 48h."""
    print("    Definiendo el target a 48 horas...")
    future_price = df['close'].shift(-HORIZON_CANDLES)
    df['target'] = np.where(future_price < df['close'], 1, 0)
    return df

# --- EJECUCIÓN PRINCIPAL ---
if __name__ == "__main__":
    print("--- 🛠️ Iniciando Creación de Dataset de IA desde Archivos Locales ---")
    
    print("Cargando datos locales de los líderes del mercado (BTC y ETH)...")
    btc_data = fetch_data_from_local_files('BTC/USDT')
    eth_data = fetch_data_from_local_files('ETH/USDT')
    
    if btc_data is None or eth_data is None:
        print("❌ No se pudieron cargar los datos de BTC/ETH. Saliendo.")
        exit()
    
    all_datasets = []
    symbols_to_process = SYMBOLS[:]
    if 'BTC/USDT' in symbols_to_process: symbols_to_process.remove('BTC/USDT')
    if 'ETH/USDT' in symbols_to_process: symbols_to_process.remove('ETH/USDT')
        
    for symbol in symbols_to_process:
        print(f"\n🔄 Procesando {symbol}...")
        altcoin_data = fetch_data_from_local_files(symbol)
        if altcoin_data is None:
            print(f"⚠️  Omitiendo {symbol}.")
            continue
            
        df_with_features = create_advanced_features(altcoin_data, btc_data, eth_data)
        df_with_target = define_target_48h(df_with_features)
        
        print("    Aplicando sistema de puntuación de señales...")
        df_with_target['quality_score'] = df_with_target.apply(calculate_quality_score, axis=1)
        
        final_df = df_with_target[df_with_target['quality_score'] >= SCORE_THRESHOLD].copy()
        
        if not final_df.empty:
            final_df['symbol'] = symbol
            all_datasets.append(final_df)

    if not all_datasets:
        print("\n❌ No se pudieron generar datos para el dataset final.")
    else:
        full_dataset = pd.concat(all_datasets)
        feature_cols = [
            'change_1h', 'change_4h', 'change_12h', 'change_24h',
            'btc_change_24h', 'eth_change_24h', 'rsi_1d', 'rsi_4h', 'rsi_1w',
            'distance_from_ma_24h', 'volume_spike_5m', 'quality_score',
            'symbol', 'target'
        ]
        final_cols = [col for col in feature_cols if col in full_dataset.columns]
        full_dataset = full_dataset[final_cols]
        
        rows_before = len(full_dataset)
        full_dataset.dropna(inplace=True)
        rows_after = len(full_dataset)
        if rows_before > rows_after:
            print(f"\nℹ️ Se eliminaron {rows_before - rows_after} filas con datos incompletos.")

        full_dataset.to_csv(OUTPUT_FILE, index=False)
        
        print(f"\n✅ Dataset de ÉLITE guardado en: {OUTPUT_FILE}")
        print(f"Total de registros para entrenar: {len(full_dataset)}")
        print("\nDistribución del Target:")
        print(full_dataset['target'].value_counts(normalize=True))