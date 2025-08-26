import os
import sys
import pandas as pd

# === Agrega la ruta a tu sistema ===
sys.path.append("C:/Users/Darkj/Desktop/Altcoin_M")

from utils import compute_indicators

# === Configuración ===
symbol = "CHZUSDT"
timeframe = "1h"

# === Paths ===
BASE_PATH = os.path.join("backtest", "data", "historico")
RUTA_DATA = os.path.join("backtest", "data", "historico", "1h")

# === Cargar histórico ===
def cargar_historico(symbol):
    ruta_archivo = os.path.join(RUTA_DATA, f"{symbol}.csv")
    if not os.path.exists(ruta_archivo):
        print(f"⚠️ No existe el archivo: {ruta_archivo}")
        return None
    df = pd.read_csv(ruta_archivo)
    df['timestamp'] = pd.to_datetime(df['timestamp_dt'])
    df.set_index('timestamp', inplace=True)
    return compute_indicators(df)

# === Crear Dataset ===
def crear_dataset():
    df = cargar_historico(symbol)
    if df is None:
        print("⛔ No se pudo cargar el histórico.")
        return

    # Crear variables adicionales
    df["cambio_pct"] = (df["close"] - df["open"]) / df["open"] * 100
    df["vela_alcista"] = (df["close"] > df["open"]).astype(int)

    # Seleccionar columnas relevantes compatibles con IA
    columnas = [
        "open", "high", "low", "close", "volume",
        "ema_21", "ema_50", "ema_200",
        "rsi_14", "macd_line", "macd_signal", "macd_hist",
        "atr_14", "willr_14", "tema_9",
        "cambio_pct", "vela_alcista"
    ]

    # Validar columnas faltantes
    columnas_existentes = [col for col in columnas if col in df.columns]
    df_final = df[columnas_existentes].copy()
    df_final.reset_index(inplace=True)

    # Crear carpeta datasets si no existe
    os.makedirs("datasets", exist_ok=True)
    output_path = os.path.join("datasets", f"dataset_{symbol}_{timeframe}.csv")

    df_final.to_csv(output_path, index=False, sep=";", decimal=",", encoding="utf-8-sig")

    print(f"\n✅ Dataset creado exitosamente: {output_path}")

    # 🔥 Espacio preparado para agregar targets IA en el futuro:
    # df_final["target_subida"] = ...
    # df_final["target_bajada"] = ...

if __name__ == "__main__":
    crear_dataset()
