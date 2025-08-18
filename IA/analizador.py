# analizador_logs_reversion.py
# Analiza el rendimiento histórico de las predicciones IA de reversión

import pandas as pd
import os

# === CONFIGURACIÓN ===
DATASET_LOG = "logs/predicciones_reversion.csv"
UMBRAL_PROB = 0.75  # Solo analizamos señales fuertes

# === VERIFICACIONES ===
if not os.path.exists(DATASET_LOG):
    print("❌ No existe el archivo de log aún.")
    exit()

df = pd.read_csv(DATASET_LOG)
df["timestamp"] = pd.to_datetime(df["timestamp"])

# === FILTRO: Solo señales con alta probabilidad ===
df_senales = df[df["prob_reversion"] >= UMBRAL_PROB]

# === MÉTRICAS GLOBALES ===
total = len(df)
senales = len(df_senales)
aciertos = df_senales["se_revirtio"].sum()
tasa_acierto = aciertos / senales * 100 if senales > 0 else 0

print(f"📈 Análisis histórico de señales IA")
print(f"-------------------------------------")
print(f"🔢 Total de predicciones: {total}")
print(f"📌 Señales generadas (prob ≥ {UMBRAL_PROB}): {senales}")
print(f"✅ Señales que se cumplieron: {aciertos}")
print(f"🎯 Tasa de acierto: {tasa_acierto:.2f}%")

# === TOP monedas por tasa de éxito ===
print("\n🏅 Ranking de monedas (por tasa de éxito en señales):")
ranking = (
    df_senales.groupby("symbol")["se_revirtio"]
    .agg(["count", "sum"])
    .rename(columns={"count": "senales", "sum": "aciertos"})
)
ranking["tasa_acierto_%"] = (ranking["aciertos"] / ranking["senales"]) * 100
ranking = ranking.sort_values(by="tasa_acierto_%", ascending=False)

print(ranking.round(2).reset_index().to_string(index=False))
