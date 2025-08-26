import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import joblib
import warnings
import matplotlib.pyplot as plt
import seaborn as sns

# --- CONFIGURACIÓN ---
warnings.simplefilter(action='ignore', category=FutureWarning)
DATASET_FILE = "topfinder_dataset_elite.csv"
MODEL_FILE = "topfinder_model.joblib"

# --- EJECUCIÓN DEL ENTRENAMIENTO ---
if __name__ == "__main__":
    print("--- 🧠 Iniciando Entrenamiento del Modelo de IA ---")
    
    # 1. Cargar el dataset que creaste con el script 01
    try:
        df = pd.read_csv(DATASET_FILE)
        print(f"✅ Dataset '{DATASET_FILE}' cargado con {len(df)} registros.")
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo '{DATASET_FILE}'.")
        print("Asegúrate de ejecutar primero el script '01_create_antifomo_dataset.py'.")
        exit()

    if df.empty or len(df) < 50:
        print(f"❌ Error: El dataset tiene muy pocos registros ({len(df)}). No es suficiente para entrenar un modelo fiable.")
        exit()

    # 2. Definir las 'features' (variables de entrada) y el 'target' (lo que queremos predecir)
    # Excluimos 'symbol', 'target' y el 'quality_score' antiguo
    features = [col for col in df.columns if col not in ['symbol', 'target', 'quality_score']]
    target = 'target'
    
    X = df[features]
    y = df[target]
    print(f"Usando {len(features)} features para el entrenamiento: {features}")

    # 3. Dividir los datos: 80% para entrenar, 20% para probar
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    print(f"\nDatos divididos: {len(X_train)} para entrenamiento, {len(X_test)} para prueba.")

    # 4. Crear y entrenar el modelo LightGBM
    print("\nEntrenando el modelo LightGBM...")
    # 'objective='binary'' le dice al modelo que es un problema de clasificación (gana o pierde)
    model = lgb.LGBMClassifier(objective='binary', random_state=42)
    model.fit(X_train, y_train)
    print("✅ Modelo entrenado.")

    # 5. Evaluar el rendimiento del modelo con datos que nunca ha visto
    print("\n--- 📊 Evaluación del Modelo ---")
    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    print(f"Precisión (Accuracy) en datos de prueba: {accuracy * 100:.2f}%")
    
    print("\nMatriz de Confusión:")
    # [[Aciertos de 0, Errores (predijo 1 era 0)],
    #  [Errores (predijo 0 era 1), Aciertos de 1]]
    print(confusion_matrix(y_test, predictions))

    print("\nReporte de Clasificación:")
    print(classification_report(y_test, predictions))

    # 6. Análisis de Features Más Importantes
    print("\n--- 🧐 Análisis de Features Más Importantes ---")
    feature_importances = pd.DataFrame({'feature': features, 'importance': model.feature_importances_})
    feature_importances = feature_importances.sort_values(by='importance', ascending=False).reset_index(drop=True)
    
    print("Top 10 features que el modelo considera más importantes:")
    print(feature_importances.head(10))
    
    # Opcional: Crear un gráfico de importancia de features
    try:
        plt.figure(figsize=(10, 8))
        sns.barplot(x="importance", y="feature", data=feature_importances.head(15))
        plt.title("Importancia de Features para el Modelo")
        plt.tight_layout()
        plt.savefig("feature_importance.png")
        print("\n✅ Gráfico de importancia de features guardado como 'feature_importance.png'")
    except ImportError:
         print("\n⚠️ Para generar el gráfico, instala las librerías: pip install matplotlib seaborn")
    except Exception as e:
        print(f"\n⚠️ No se pudo generar el gráfico. Error: {e}")

    # 7. Guardar el "cerebro" del modelo en un archivo
    joblib.dump(model, MODEL_FILE)
    print(f"\n✅ Modelo de IA guardado exitosamente en '{MODEL_FILE}'.")