# === VALIDAR_REENTRENAMIENTO_FINAL.PY ===
# Verifica que el modelo IA reentrenado puede predecir normalmente.

import numpy as np
import joblib

def validar_modelo(path_modelo, nombre):
    print(f"\n🔍 Validando modelo: {nombre}")
    try:
        modelo = joblib.load(path_modelo)

        # Crear input de prueba (15 features flotantes realistas)
        X_test = np.array([[1, 2, 3, 4, 5, 30, -10, -5, 50, 60, 70, 100, 0.95, 0.4, 0.5]], dtype=np.float64)

        # Intentar predecir
        prob = modelo.predict_proba(X_test)[0][1]
        print(f"✅ Modelo {nombre} predice OK. Probabilidad: {prob:.4f}")
    except Exception as e:
        print(f"❌ Error en modelo {nombre}: {e}")

if __name__ == "__main__":
    print("⚙️ Iniciando validación final de modelos IA...\n")

    validar_modelo(
        path_modelo="C:/Users/Darkj/Desktop/IA/modelo/modelo_rf_15m_long.pkl",
        nombre="LONG"
    )

    validar_modelo(
        path_modelo="C:/Users/Darkj/Desktop/IA/modelo/modelo_rf_15m_short.pkl",
        nombre="SHORT"
    )

    print("\n🏁 Validación finalizada.")
