import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

print("--- Iniciando Entrenamiento del Modelo de Clasificación v2 ---")
DATASET_PATH = "antifomo_dataset.csv"
MODEL_OUTPUT_PATH = "antifomo_model.pkl"

df = pd.read_csv(DATASET_PATH)
X = df.drop('target', axis=1)
y = df['target']

# Esta línea es crucial: asegura que el modelo conozca los nombres de las features
X.columns = [str(col) for col in X.columns] 

scale_pos_weight = y.value_counts()[0] / y.value_counts()[1]
print(f"Usando 'scale_pos_weight': {scale_pos_weight:.2f}")

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

model = xgb.XGBClassifier(
    objective='binary:logistic',
    scale_pos_weight=scale_pos_weight,
    n_estimators=250,
    learning_rate=0.05,
    max_depth=6,
    random_state=42
)

print("🧠 Entrenando modelo...")
model.fit(X_train, y_train)
print("✅ Modelo entrenado.")

y_pred = model.predict(X_test)
print("\n--- Reporte de Clasificación (Modelo Actualizado) ---")
print(classification_report(y_test, y_pred))

joblib.dump(model, MODEL_OUTPUT_PATH)
print(f"\n💾 Modelo guardado como: {MODEL_OUTPUT_PATH}")