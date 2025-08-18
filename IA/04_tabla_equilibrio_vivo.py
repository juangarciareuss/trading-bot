# 04_tabla_equilibrio_vivo.py
# Muestra una tabla en vivo con el desequilibrio de cada altcoin respecto a BTC y la probabilidad de reversión

import pandas as pd
import numpy as np
import joblib
import os
import json
from tabulate import tabulate

# === CONFIGURACIÓN ===
CONFIG_PATH = "backtest/config/activos_en_medicion.json"
BASE_PATH = "backtest/data/historico/1h"
TIMEFRAME = "1h"
BTC_SYMBOL = "BTCUSDT"
MODELOS_FOLDER = "modelos_equilibrio"

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
    df.dropna(subset=["log_return"], inplace=True)
    return df[["close", "volume", "log_return"]]

def cargar_activos():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

# Reemplaza tu función actual 'evaluar_desequilibrio' por esta, que es consistente:
def evaluar_desequilibrio(btc_df, alt_df, modelo):
    # La lógica de cálculo de indicadores debe estar aquí
    # (por simplicidad la omito, pero debes añadirla como en tu script 03)
    # Por ahora, unimos los dataframes
    df = btc_df.join(alt_df, lsuffix="_btc", rsuffix="_alt", how="inner")

    # === Calcular las 7 features EXACTAS del entrenamiento ===
    df["ret_diff"] = df["log_return_alt"] - df["log_return_btc"]
    df["ret_diff_3v"] = df["ret_diff"].rolling(3).sum()
    
    # Necesitas calcular RSI y MACD aquí para poder obtener sus diferenciales
    # Esta parte es crucial y falta en tu script 04
    # ... (cálculo de rsi_alt, rsi_btc, macd_alt, macd_btc, etc.) ...
    
    # Asumiendo que ya calculaste los indicadores base:
    df["rsi_diff"] = df["rsi_alt"] - df["rsi_btc"]
    df["macd_diff"] = df["macd_alt"] - df["macd_btc"]
    df["macd_signal_diff"] = df["macd_signal_alt"] - df["macd_signal_btc"]
    df["rolling_corr"] = df["log_return_alt"].rolling(5).corr(df["log_return_btc"])
    df["volatility_ratio"] = df["log_return_alt"].rolling(5).std() / (df["log_return_btc"].rolling(5).std() + 1e-6)
    
    df.dropna(inplace=True)

    X = df[[
        "ret_diff", "ret_diff_3v", "rsi_diff", "macd_diff", 
        "macd_signal_diff", "rolling_corr", "volatility_ratio"
    ]].iloc[-1:].values

    prob = modelo.predict_proba(X)[0][1]
    return df["ret_diff"].iloc[-1], prob

def mostrar_tabla_equilibrio():
    btc_df = load_data(BTC_SYMBOL)
    if btc_df is None:
        print("❌ No se pudo cargar BTCUSDT")
        return

    activos = cargar_activos()
    resultados = []

    for alt in activos:
        if alt == BTC_SYMBOL:
            continue

        modelo_path = os.path.join(MODELOS_FOLDER, f"modelo_equilibrio_{alt.lower()}_vs_btc_{TIMEFRAME}.pkl")
        if not os.path.exists(modelo_path):
            continue

        try:
            alt_df = load_data(alt)
            if alt_df is None:
                continue

            modelo = joblib.load(modelo_path)
            ret_diff, prob = evaluar_desequilibrio(btc_df, alt_df, modelo)

            resultados.append({
                "symbol": alt,
                "ret_diff": ret_diff,
                "prob_reversion": prob
            })
        except Exception as e:
            print(f"⚠️ Error con {alt}: {e}")

    if not resultados:
        print("⚠️ No hay resultados para mostrar.")
        return

    df_result = pd.DataFrame(resultados)
    df_result.sort_values("ret_diff", key=abs, ascending=False, inplace=True)
    print("\n📊 Tabla de desequilibrios y probabilidades de reversión:\n")
    print(tabulate(df_result, headers="keys", tablefmt="pretty", floatfmt=".4f"))

# === EJECUCIÓN ===
if __name__ == "__main__":
    mostrar_tabla_equilibrio()
