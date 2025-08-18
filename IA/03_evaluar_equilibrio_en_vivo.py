import pandas as pd
import numpy as np
import joblib
import os

# === CONFIGURACIÓN ===
ALT_SYMBOL = "BNBUSDT"
BTC_SYMBOL = "BTCUSDT"
TIMEFRAME = "1h"
MODELO_PATH = f"modelos_equilibrio/modelo_equilibrio_{ALT_SYMBOL.lower()}_vs_btc_{TIMEFRAME}.pkl"
BASE_PATH = f"backtest/data/historico/{TIMEFRAME}"

# === FUNCIONES ===
def load_latest_data(symbol):
    path = os.path.join(BASE_PATH, f"{symbol}.csv")
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp_dt"])
    df.set_index("timestamp", inplace=True)
    df = df.sort_index()
    df["log_return"] = np.log(df["close"] / df["close"].shift(1))
    df["rsi"] = df["close"].diff().rolling(14).mean()  # proxy simple de RSI
    df["macd"] = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
    df["macd_signal"] = df["macd"].ewm(span=9).mean()
    df.dropna(inplace=True)
    return df[["close", "volume", "log_return", "rsi", "macd", "macd_signal"]]

def evaluar_equilibrio_en_vivo():
    modelo = joblib.load(MODELO_PATH)

    btc_df = load_latest_data(BTC_SYMBOL)
    alt_df = load_latest_data(ALT_SYMBOL)

    df = btc_df.join(alt_df, lsuffix="_btc", rsuffix="_alt", how="inner")

    # === Calcular las 7 features ===
    df["ret_diff"] = df["log_return_alt"] - df["log_return_btc"]
    df["ret_diff_3v"] = df["ret_diff"].rolling(3).sum()
    df["rsi_diff"] = df["rsi_alt"] - df["rsi_btc"]
    df["macd_diff"] = df["macd_alt"] - df["macd_btc"]
    df["macd_signal_diff"] = df["macd_signal_alt"] - df["macd_signal_btc"]
    df["rolling_corr"] = df["log_return_alt"].rolling(5).corr(df["log_return_btc"])
    df["volatility_ratio"] = df["log_return_alt"].rolling(5).std() / (df["log_return_btc"].rolling(5).std() + 1e-6)

    df.dropna(inplace=True)

    X = df[[
        "ret_diff",
        "ret_diff_3v",
        "rsi_diff",
        "macd_diff",
        "macd_signal_diff",
        "rolling_corr",
        "volatility_ratio"
    ]].iloc[-1:].values

    # === Predicción ===
    pred = modelo.predict(X)[0]
    prob = modelo.predict_proba(X)[0][1]

    print(f"\n🔍 Evaluación en vivo para {ALT_SYMBOL} respecto a BTC")
    print(f"Desequilibrio actual: {df['ret_diff'].iloc[-1]:.4f}")
    print(f"Probabilidad de reversión: {prob*100:.2f}%")
    if pred == 1:
        print("⚠️ Señal: Alta probabilidad de reversión al equilibrio")
    else:
        print("✅ Sin señales de reversión importantes")

# === EJECUCIÓN ===
if __name__ == "__main__":
    evaluar_equilibrio_en_vivo()
