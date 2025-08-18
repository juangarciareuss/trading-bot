# === VALIDAR MODELO IA REGRESIÓN REAL - RENTABILIDAD FUTURA ===

import pandas as pd
import numpy as np
import os
import joblib
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split

# === CONFIGURACIÓN GENERAL ===
SYMBOL = "1inchUSDT"
TIMEFRAME = "15m"
UMBRAL_TP = 0.015  # Umbral mínimo para operar (2%)
MOSTRAR_PLOT = True
GUARDAR_CSV = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, "datasets_ia_regresion")
MODEL_FOLDER = os.path.join(BASE_DIR, "modelo_regresion")
PRED_FOLDER = BASE_DIR  # donde guardar las predicciones

# Archivos
DATASET_LONG = f"dataset_regresion_{SYMBOL.lower()}_alcista_{TIMEFRAME}.csv"
DATASET_SHORT = f"dataset_regresion_{SYMBOL.lower()}_bajista_{TIMEFRAME}.csv"
MODEL_LONG = f"modelo_regresion_{SYMBOL.lower()}_{TIMEFRAME}_long.pkl"
MODEL_SHORT = f"modelo_regresion_{SYMBOL.lower()}_{TIMEFRAME}_short.pkl"

ORDER_FEATURES = [
    "open", "high", "low", "close", "volume",
    "rsi", "macd", "macd_signal",
    "ema7", "ema21", "ema25", "vol_ma",
    "ema7_vs_25", "vol_ratio", "cuerpo_pct"
]

# Clasificador
def clasificar(y_pred, y_real, umbral):
    if y_pred >= umbral:
        if y_real >= umbral:
            return "✅ Éxito"
        else:
            return "❌ Fallo"
    else:
        return "⏳ Neutro"

# === VALIDACIÓN DEL MODELO ===
def validar_modelo_regresion(path_dataset, path_modelo, modo):
    df = pd.read_csv(path_dataset)
    modelo = joblib.load(path_modelo)

    X = df[ORDER_FEATURES].astype(np.float64).to_numpy()
    y = df["target"].astype(np.float64).to_numpy()

    # División entrenamiento/test
    _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    # Predicción sobre test
    y_pred = modelo.predict(X_test)

    # Clasificación
    resultados = pd.DataFrame({
        "y_real": y_test,
        "y_pred": y_pred
    })
    resultados["resultado"] = resultados.apply(lambda row: clasificar(row["y_pred"], row["y_real"], UMBRAL_TP), axis=1)

    # Métricas
    total = len(resultados)
    activadas = resultados[resultados["resultado"] != "⏳ Neutro"]
    éxitos = (activadas["resultado"] == "✅ Éxito").sum()
    fallos = (activadas["resultado"] == "❌ Fallo").sum()
    neutros = (resultados["resultado"] == "⏳ Neutro").sum()

    tasa_exito = (éxitos / len(activadas)) * 100 if len(activadas) > 0 else 0

    # Mostrar resultados
    print(f"\n📊 Evaluación REGRESIÓN {SYMBOL} [{TIMEFRAME}] modo {modo.upper()}")
    print(f"✅ Éxitos (predijo bien movimientos grandes): {éxitos}")
    print(f"❌ Fallos (predijo y no se cumplió): {fallos}")
    print(f"⏳ Neutros (no activó señal): {neutros}")
    print(f"🎯 Tasa de Éxito (solo señales activadas): {tasa_exito:.2f}%")
    print(f"📈 Total señales activadas: {len(activadas)} / {total} ({len(activadas)/total*100:.2f}%)")

    # Guardar CSV con resultados
    if GUARDAR_CSV:
        nombre_archivo = f"evaluacion_{SYMBOL.lower()}_{TIMEFRAME}_{modo}.csv"
        resultados.to_csv(os.path.join(PRED_FOLDER, nombre_archivo), index=False)
        print(f"📁 Resultados guardados en: {nombre_archivo}")

    # Gráfico
    if MOSTRAR_PLOT:
        plt.hist(y_pred, bins=50, alpha=0.7, color="skyblue", edgecolor="black")
        plt.axvline(UMBRAL_TP, color="red", linestyle="--", label=f"Umbral TP: {UMBRAL_TP}")
        plt.title(f"Distribución Predicciones IA - {SYMBOL} {TIMEFRAME} {modo.upper()}")
        plt.xlabel("Predicción (rentabilidad esperada)")
        plt.ylabel("Cantidad")
        plt.legend()
        plt.tight_layout()
        plt.show()

# === EJECUCIÓN PRINCIPAL ===
if __name__ == "__main__":
    validar_modelo_regresion(
        path_dataset=os.path.join(DATA_FOLDER, DATASET_LONG),
        path_modelo=os.path.join(MODEL_FOLDER, MODEL_LONG),
        modo="alcista"
    )

    validar_modelo_regresion(
        path_dataset=os.path.join(DATA_FOLDER, DATASET_SHORT),
        path_modelo=os.path.join(MODEL_FOLDER, MODEL_SHORT),
        modo="bajista"
    )
