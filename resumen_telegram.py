# === resumen_telegram_1h.py ===

import json
import os
from datetime import datetime, timedelta
from utils import enviar_telegram
import pandas as pd


def generar_resumen_diario():
    archivo = "cerradas_1h.json"
    if not os.path.exists(archivo):
        print("❌ No hay señales cerradas para generar resumen.")
        return

    with open(archivo, "r") as f:
        data = json.load(f)

    if not data:
        print("❌ Lista vacía de señales cerradas.")
        return

    df = pd.DataFrame(data)
    df['timestamp_salida'] = pd.to_datetime(df['timestamp_salida'])
    hoy = datetime.utcnow().date()
    df_hoy = df[df['timestamp_salida'].dt.date == hoy]

    if df_hoy.empty:
        enviar_telegram("📊 Resumen Diario 1H\nHoy no se cerraron señales.")
        return

    total = len(df_hoy)
    ganadoras = df_hoy[df_hoy['resultado_pct'] > 0]
    perdedoras = df_hoy[df_hoy['resultado_pct'] <= 0]
    mejor = df_hoy.loc[df_hoy['resultado_pct'].idxmax()]
    peor = df_hoy.loc[df_hoy['resultado_pct'].idxmin()]

    resumen = f"""
📊 *Resumen Diario 1H – {hoy.strftime('%d-%b-%Y')}*

🔢 Total señales cerradas: {total}
✅ Ganadoras: {len(ganadoras)}
❌ Perdedoras: {len(perdedoras)}

🏆 Mejor cripto: {mejor['symbol']} (+{mejor['resultado_pct']}%)
💀 Peor cripto: {peor['symbol']} ({peor['resultado_pct']}%)

💬 Escenarios más comunes:
{df_hoy['escenario'].value_counts().head(3).to_string()}
    """

    enviar_telegram(resumen.strip())


# Puedes llamarla desde tu main diario:
# generar_resumen_diario()
