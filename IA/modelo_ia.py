import pandas as pd
import numpy as np
import os
import joblib
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

# === CONFIGURACIÓN GENERAL ===
SYMBOL = "btcusdt"
TIMEFRAME = "15m"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, "datasets_ia_regresion")
MODEL_FOLDER = "modelo_regresion"
PRED_FOLDER = os.path.join(BASE_DIR, "predicciones")


# Nombre de archivos dinámico por símbolo y timeframe
DATASET_LONG = f"dataset_regresion_{SYMBOL.lower()}_alcista_{TIMEFRAME}.csv"
DATASET_SHORT = f"dataset_regresion_{SYMBOL.lower()}_bajista_{TIMEFRAME}.csv"
MODEL_LONG = f"modelo_regresion_{SYMBOL.lower()}_{TIMEFRAME}_long.pkl"
MODEL_SHORT = f"modelo_regresion_{SYMBOL.lower()}_{TIMEFRAME}_short.pkl"


# Features que vamos a usar
ORDER_FEATURES = [
    "open", "high", "low", "close", "volume",
    "rsi", "macd", "macd_signal",
    "ema7", "ema21", "ema25", "vol_ma",
    "ema7_vs_25", "vol_ratio", "cuerpo_pct"
]

# Clasificación de cada fila
def clasificar(y_pred, y_real, umbral=0.02):
    if y_pred >= umbral:
        if y_real >= umbral:
            return "✅ Éxito"
        else:
            return "❌ Fallo"
    else:
        return "⏳ Neutro"

# === FUNCIÓN PRINCIPAL DE ENTRENAMIENTO ===
def entrenar_y_guardar_modelo(dataset_path, model_path, modo):
    df = pd.read_csv(dataset_path)

    X = df[ORDER_FEATURES].astype(np.float64).to_numpy()
    y = df["target"].astype(np.float64).to_numpy()

    # Separación entrenamiento/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    modelo = HistGradientBoostingRegressor(
        loss="absolute_error",
        learning_rate=0.1,
        max_iter=300,
        max_depth=8,
        random_state=42
    )

    modelo.fit(X_train, y_train)

    # Guardar modelo
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(modelo, model_path)
    print(f"\n✅ Modelo IA REGRESIÓN ({modo}) entrenado y guardado en: {model_path}")

    # Evaluación
    y_pred = modelo.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print(f"📊 Evaluación {modo.upper()}")
    print(f"• MAE (Error absoluto medio): {mae:.4f}")
    print(f"• R² Score: {r2:.4f}")

    # Clasificar resultados
    resultados = pd.DataFrame({
        "y_real": y_test,
        "y_pred": y_pred
    })
    resultados["resultado"] = resultados.apply(lambda row: clasificar(row["y_pred"], row["y_real"]), axis=1)

    # Guardar CSV
    os.makedirs(PRED_FOLDER, exist_ok=True)
    archivo_salida = os.path.join(PRED_FOLDER, f"predicciones_{SYMBOL.lower()}_{TIMEFRAME}_{modo}.csv")
    resultados.to_csv(archivo_salida, index=False)
    print(f"📁 Predicciones clasificadas guardadas en: {archivo_salida}")

# === EJECUCIÓN PRINCIPAL ===
if __name__ == "__main__":
    print("⚙️ Entrenando modelos IA REGRESIÓN con evaluación...\n")

    entrenar_y_guardar_modelo(
        dataset_path=os.path.join(DATA_FOLDER, DATASET_LONG),
        model_path=os.path.join(MODEL_FOLDER, MODEL_LONG),
        modo="alcista"
    )

    entrenar_y_guardar_modelo(
        dataset_path=os.path.join(DATA_FOLDER, DATASET_SHORT),
        model_path=os.path.join(MODEL_FOLDER, MODEL_SHORT),
        modo="bajista"
    )