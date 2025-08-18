import pandas as pd
import ccxt

# --- INICIALIZACIÓN DEL EXCHANGE ---
# Lo definimos aquí para que sea accesible desde cualquier parte del sistema
exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})

# --- FUNCIONES AUXILIARES ---
def resample_dataframe(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Convierte un DataFrame de OHLCV a un timeframe mayor."""
    df_resampled = df.resample(timeframe).agg({
        'o': 'first', 'h': 'max', 'l': 'min', 'c': 'last', 'v': 'sum'
    })
    df_resampled.dropna(inplace=True)
    return df_resampled