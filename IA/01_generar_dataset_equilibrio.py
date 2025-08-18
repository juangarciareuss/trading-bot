# 01_generar_dataset_equilibrio.py (versión mejorada)

import pandas as pd
import numpy as np
import os

# === CONFIGURACIÓN ===
ALT_SYMBOL = "ETHUSDT"
BTC_SYMBOL = "BTCUSDT"
TIMEFRAME = "1h"
BASE_PATH = os.path.join("backtest", "data", "historico", TIMEFRAME)
OUTPUT_FOLDER = "datasets_equilibrio"
WINDOW = 5  # Para correlación y volatilidad

# === CARGA ===
def load_data(symbol):
    path = os.path.join(BASE_PATH, f"{symbol}.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Archivo no encontrado: {path}")
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp_dt"])
    df.set_index("timestamp", inplace=True)
    df = df.sort_index()
    df["log_return"] = np.log(df["close"] / df["close"].shift(1))
    df["rsi"] = df["close"].diff().rolling(14).mean()  # Proxy RSI simplificado
    df["macd"] = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
    df["macd_signal"] = df["macd"].ewm(span=9).mean()
    return df[["close", "volume", "log_return", "rsi", "macd", "macd_signal"]].dropna()

# === EJECUCIÓN ===
if __name__ == "__main__":
    btc_df = load_data(BTC_SYMBOL)
    alt_df = load_data(ALT_SYMBOL)

    df = btc_df.join(alt_df, lsuffix="_btc", rsuffix="_alt", how="inner")
    df["ret_diff"] = df["log_return_alt"] - df["log_return_btc"]
    df["ret_diff_3v"] = df["ret_diff"].rolling(3).sum()
    df["rsi_diff"] = df["rsi_alt"] - df["rsi_btc"]
    df["macd_diff"] = df["macd_alt"] - df["macd_btc"]
    df["macd_signal_diff"] = df["macd_signal_alt"] - df["macd_signal_btc"]
    df["rolling_corr"] = df["log_return_alt"].rolling(WINDOW).corr(df["log_return_btc"])
    df["volatility_ratio"] = df["log_return_alt"].rolling(WINDOW).std() / (df["log_return_btc"].rolling(WINDOW).std() + 1e-6)

    # Nuevo target: reversión real
    df["target"] = (df["ret_diff"].shift(-4).abs() < 0.004).astype(int)

    # Selección final de features
    df_final = df[[
        "ret_diff", "ret_diff_3v", "rsi_diff", "macd_diff", "macd_signal_diff",
        "rolling_corr", "volatility_ratio", "target"
    ]].dropna()

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    out_path = os.path.join(OUTPUT_FOLDER, f"dataset_equilibrio_{ALT_SYMBOL.lower()}_vs_btc_{TIMEFRAME}.csv")
    df_final.to_csv(out_path, index=False)
    print(f"\n✅ Dataset de equilibrio guardado en: {out_path}")
