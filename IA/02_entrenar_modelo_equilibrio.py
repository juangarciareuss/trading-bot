import pandas as pd
import numpy as np
import os
import joblib
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import TimeSeriesSplit, cross_validate
from sklearn.metrics import classification_report, confusion_matrix

# === CONFIGURACIÓN ===
ALT_SYMBOL = "AAVEUSDT"
TIMEFRAME = "1h"
DATASET_PATH = f"datasets_equilibrio/dataset_equilibrio_{ALT_SYMBOL.lower()}_vs_btc_{TIMEFRAME}.csv"
OUTPUT_MODEL = f"modelos_equilibrio/modelo_equilibrio_{ALT_SYMBOL.lower()}_vs_btc_{TIMEFRAME}.pkl"

# === CARGA ===
df = pd.read_csv(DATASET_PATH)
X = df.drop("target", axis=1).values
y = df["target"].values

# === VALIDACIÓN CON TimeSeriesSplit ===
print("\n🔍 Validación cruzada temporal (TimeSeriesSplit)...")
tscv = TimeSeriesSplit(n_splits=5)
modelo_cv = HistGradientBoostingClassifier(
    max_iter=300, learning_rate=0.1, max_depth=6,
    random_state=42
)

resultados = cross_validate(
    modelo_cv, X, y, cv=tscv,
    scoring=["accuracy", "precision", "recall", "f1"],
    return_train_score=False
)

for metrica in resultados:
    if "test" in metrica:
        scores = resultados[metrica]
        print(f"{metrica}: {np.mean(scores):.4f} ± {np.std(scores):.4f}")

# === ENTRENAMIENTO FINAL COMPLETO ===
print("\n🧠 Entrenando modelo final completo...")
modelo = HistGradientBoostingClassifier(
    max_iter=300, learning_rate=0.1, max_depth=6,
    random_state=42
)
modelo.fit(X, y)

# === GUARDADO ===
os.makedirs("modelos_equilibrio", exist_ok=True)
joblib.dump(modelo, OUTPUT_MODEL)
print(f"\n✅ Modelo guardado en: {OUTPUT_MODEL}")
