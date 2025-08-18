# === CREAR DATASET IA PARA REGRESIÓN - RENTABILIDAD FUTURA ===

import pandas as pd
import numpy as np
import os
import sys
from tqdm import tqdm

# Corrección de path para importar utils
sys.path.append(os.path.abspath(".."))
sys.path.append("C:/Users/Darkj/Desktop/Altcoin_M")

from utils import compute_indicators

# === CONFIGURACIÓN GENERAL ===
SIMBOLO = "DASHUSDT"
TIMEFRAME = "15m"
PATH_DATA = "../Backtest/data/historico"
PATH_DATASETS_IA = "datasets_ia_regresion"

# CONFIGURACIÓN RENTABILIDAD FUTURA
VELAS_FUTURO = 8  # Cuántas velas hacia adelante miramos

# === FUNCION PRINCIPAL PARA CREAR DATASET ===
def crear_dataset_ia_regresion(symbol, timeframe, modo="alcista"):
    print(f"\n⚙️ Creando dataset IA REGRESIÓN para {symbol} [{timeframe}] modo: {modo}...")

    # === Cargar histórico ===
    path_csv = os.path.join(PATH_DATA, timeframe, f"{symbol}.csv")
    df = pd.read_csv(path_csv)
    df['timestamp'] = pd.to_datetime(df['timestamp_dt'])
    df.set_index('timestamp', inplace=True)
    df = compute_indicators(df)

    # 🔥 Agregar indicadores adicionales
    df['ema7'] = df['close'].ewm(span=7, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema25'] = df['close'].ewm(span=25, adjust=False).mean()
    df['vol_ma'] = df['volume'].rolling(window=20).mean()

    # === Calcular RENTABILIDAD FUTURA como nuevo TARGET ===
    print("\n🔎 Calculando rentabilidad futura como target...")
    futuros_high = df['high'].rolling(window=VELAS_FUTURO, min_periods=1).max().shift(-VELAS_FUTURO)
    futuros_low = df['low'].rolling(window=VELAS_FUTURO, min_periods=1).min().shift(-VELAS_FUTURO)
    close_actual = df['close']

    if modo == "alcista":
        df["target"] = (futuros_high - close_actual) / close_actual
    else:  # bajista
        df["target"] = (close_actual - futuros_low) / close_actual

    # Limpiar datos
    df.dropna(inplace=True)

    # === Seleccionar Features ===
    df_final = df[[
        "open", "high", "low", "close", "volume",
        "rsi", "macd", "macd_signal",
        "ema7", "ema21", "ema25", "vol_ma",
        "target"
    ]]

    # Limpieza final
    df_final = df_final.apply(pd.to_numeric, errors='coerce')
    df_final = df_final.dropna()

    # Agregar relaciones adicionales
    df_final["ema7_vs_25"] = df_final["ema7"] / df_final["ema25"]
    df_final["vol_ratio"] = df_final["volume"] / df_final["vol_ma"]
    df_final["cuerpo_pct"] = abs(df_final["close"] - df_final["open"]) / (df_final["high"] - df_final["low"] + 1e-6)

    # === Guardar Dataset ===
    os.makedirs(PATH_DATASETS_IA, exist_ok=True)

    nombre_archivo = f"dataset_regresion_{symbol.lower()}_{modo}_{timeframe}.csv"
    output_path = os.path.join(PATH_DATASETS_IA, nombre_archivo)
    df_final.to_csv(output_path, index=False)
    print(f"\n✅ Dataset IA REGRESIÓN creado en: {output_path}")

# === EJECUCIÓN PRINCIPAL ===
if __name__ == "__main__":
    crear_dataset_ia_regresion(SIMBOLO, TIMEFRAME, modo="alcista")
    crear_dataset_ia_regresion(SIMBOLO, TIMEFRAME, modo="bajista")
