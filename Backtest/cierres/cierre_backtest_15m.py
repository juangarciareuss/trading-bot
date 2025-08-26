# === cierre_backtest_15m.py (VERSIÓN QUIRÚRGICA ACTUALIZADA) ===

import pandas as pd
from utils import compute_indicators

def evaluar_cierre_tecnico_backtest_15m(df, tipo, escenario, precio_entrada):
    df = compute_indicators(df)
    df.reset_index(inplace=True)  # Conserva timestamp_dt si existe

    for i in range(1, len(df)):
        vela = df.iloc[i]
        vol_actual = vela['volume']
        vol_ma = df['volume'].rolling(20).mean().iloc[i]
        ema21 = df['close'].ewm(span=21, adjust=False).mean().iloc[i]
        cuerpo = abs(vela['close'] - vela['open'])
        rango = vela['high'] - vela['low']
        vela_firme = cuerpo > rango * 0.45
        vela_intencion = (
            (vela['close'] > vela['open'] if tipo == 'COMPRA' else vela['close'] < vela['open'])
            and vela_firme and vol_actual > vol_ma * 1.1
        )
        cambio_pct = (
            (vela['close'] - precio_entrada) / precio_entrada * 100
            if tipo == "COMPRA" else (precio_entrada - vela['close']) / precio_entrada * 100
        )
        estructura_perdida = (
            vela['close'] < ema21 * 0.995 if tipo == "COMPRA" else vela['close'] > ema21 * 1.005
        )

        # Lógica específica para acumulación explosiva
        objetivo_fijo = 4.0
        trailing_gap = 1.4 if "acumulacion" in escenario else 1.2

        if cambio_pct > objetivo_fijo + trailing_gap and vol_actual < vol_ma:
            return {
                "precio_salida": vela["close"],
                "timestamp_salida": vela.get("timestamp_dt", None),
                "resultado_pct": round(cambio_pct, 2),
                "motivo": f"✅ Trailing anticipado sin volumen (+{cambio_pct:.2f}%)"
            }
        elif cambio_pct > objetivo_fijo:
            return {
                "precio_salida": vela["close"],
                "timestamp_salida": vela.get("timestamp_dt", None),
                "resultado_pct": round(cambio_pct, 2),
                "motivo": f"✅ Objetivo alcanzado (+{cambio_pct:.2f}%)"
            }
        elif cambio_pct > 0 and not vela_intencion:
            return {
                "precio_salida": vela["close"],
                "timestamp_salida": vela.get("timestamp_dt", None),
                "resultado_pct": round(cambio_pct, 2),
                "motivo": f"✅ Rentable sin intención (+{cambio_pct:.2f}%)"
            }
        elif cambio_pct <= 0 and estructura_perdida and not vela_intencion:
            return {
                "precio_salida": vela["close"],
                "timestamp_salida": vela.get("timestamp_dt", None),
                "resultado_pct": round(cambio_pct, 2),
                "motivo": f"❌ Reversa y pérdida de estructura"
            }

        # Tiempo máximo: 90 minutos (6 velas)
        if i >= 6 and cambio_pct < 0.5:
            return {
                "precio_salida": vela["close"],
                "timestamp_salida": vela.get("timestamp_dt", None),
                "resultado_pct": round(cambio_pct, 2),
                "motivo": f"⚠️ Cierre por falta de avance (>90 minutos)"
            }

    return None  # No se activó ningún cierre dentro del rango
