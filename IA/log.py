# log_predicciones_diarias.py
# Registra predicciones IA y verifica si realmente hubo reversión al equilibrio

import os
import json
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timezone

# === CONFIGURACIÓN ===
TIMEFRAME = "1h"
BASE_PATH = f"backtest/data/historico/{TIMEFRAME}"
DATASET_LOG = "logs/predicciones_reversion.csv"
MODELOS_FOLDER = "modelos_equilibrio"
CONFIG_PATH = "backtest/config/activos_en_medicion.json"
WINDOW_FUTURO = 4

# === FUNCIONES ===
def load_data(symbol):
    path = os.path.join(BASE_PATH, f"{symbol}.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp_dt"])
    df.set_index("timestamp", inplace=True)
    df = df.sort_index()
    df["log_return"] = np.log(df["close"] / df["close"].shift(1))
    df["rsi"] = df["close"].diff().rolling(14).mean()
    df["macd"] = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
    df["macd_signal"] = df["macd"].ewm(span=9).mean()
    df.dropna(inplace=True)
    return df[["close", "volume", "log_return", "rsi", "macd", "macd_signal"]]

def evaluar_con_futuro(btc_df, alt_df, modelo, symbol):
    df = btc_df.join(alt_df, lsuffix="_btc", rsuffix="_alt", how="inner")

    # === Features IA (7)
    df["ret_diff"] = df["log_return_alt"] - df["log_return_btc"]
    df["ret_diff_3v"] = df["ret_diff"].rolling(3).sum()
    df["rsi_diff"] = df["rsi_alt"] - df["rsi_btc"]
    df["macd_diff"] = df["macd_alt"] - df["macd_btc"]
    df["macd_signal_diff"] = df["macd_signal_alt"] - df["macd_signal_btc"]
    df["rolling_corr"] = df["log_return_alt"].rolling(5).corr(df["log_return_btc"])
    df["volatility_ratio"] = df["log_return_alt"].rolling(5).std() / (df["log_return_btc"].rolling(5).std() + 1e-6)
    df.dropna(inplace=True)

    # === Predicción y evaluación futura
    ret_diff_actual = df["ret_diff"].iloc[-1]
    ret_diff_futuro = df["ret_diff"].shift(-WINDOW_FUTURO).iloc[-1]
    X = df[[
        "ret_diff",
        "ret_diff_3v",
        "rsi_diff",
        "macd_diff",
        "macd_signal_diff",
        "rolling_corr",
        "volatility_ratio"
    ]].iloc[-1:].values
    prob = modelo.predict_proba(X)[0][1]
    se_revirtio = int(abs(ret_diff_futuro) < 0.001)

    return {
        "symbol": symbol,
        "ret_diff": ret_diff_actual,
        "prob_reversion": prob,
        "ret_diff_futuro": ret_diff_futuro,
        "se_revirtio": se_revirtio,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# === FLUJO PRINCIPAL ===
if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)

    with open(CONFIG_PATH, "r") as f:
        activos = json.load(f)

    if "BTCUSDT" not in activos:
        activos.append("BTCUSDT")

    btc_df = load_data("BTCUSDT")
    if btc_df is None:
        print("❌ No se pudo cargar BTCUSDT.")
        exit()

    logs = []
    for symbol in activos:
        if symbol == "BTCUSDT":
            continue

        modelo_path = os.path.join(MODELOS_FOLDER, f"modelo_equilibrio_{symbol.lower()}_vs_btc_{TIMEFRAME}.pkl")
        if not os.path.exists(modelo_path):
            continue

        alt_df = load_data(symbol)
        if alt_df is None or len(alt_df) < WINDOW_FUTURO + 1:
            continue

        try:
            modelo = joblib.load(modelo_path)
            fila_log = evaluar_con_futuro(btc_df, alt_df, modelo, symbol)
            logs.append(fila_log)
        except Exception as e:
            print(f"⚠️ Error evaluando {symbol}: {e}")

    # === Guardar logs
    if logs:
        df_log = pd.DataFrame(logs)
        if os.path.exists(DATASET_LOG):
            df_ant = pd.read_csv(DATASET_LOG)
            df_log = pd.concat([df_ant, df_log], ignore_index=True)
        df_log.to_csv(DATASET_LOG, index=False)
        print(f"\n✅ Log actualizado en: {DATASET_LOG}")
    else:
        print("⚠️ No se generaron logs hoy.")
