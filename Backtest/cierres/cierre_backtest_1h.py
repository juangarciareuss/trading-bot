# === cierre_backtest_1h.py ===

import pandas as pd
from utils import compute_indicators

def evaluar_cierre_tecnico_backtest_1h(df, tipo, escenario, precio_entrada):
    df = compute_indicators(df)
    df.reset_index(inplace=True)  # Conserva la columna timestamp_dt

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

        # Parámetros por escenario
        trailing_gap = 1.0
        objetivo_alto = 3.5
        if escenario in ["escenario_01_reentrada_post_consolidacion", "escenario_09_triple_techo"]:
            trailing_gap = 1.8
        elif escenario in ["escenario_05_base_redondeada", "escenario_10_techo_redondeado"]:
            trailing_gap = 1.2
        elif escenario in ["escenario_07_pullback_ema21_bajista", "escenario_02_pullback_ema21"]:
            trailing_gap = 0.8

        if cambio_pct > objetivo_alto + trailing_gap and vol_actual < vol_ma:
            return {
                "precio_salida": vela["close"],
                "timestamp_salida": vela["timestamp_dt"],
                "resultado_pct": round(cambio_pct, 2),
                "motivo": f"✅ Trailing anticipado sin volumen (+{cambio_pct:.2f}%)"
            }
        elif cambio_pct > objetivo_alto:
            return {
                "precio_salida": vela["close"],
                "timestamp_salida": vela["timestamp_dt"],
                "resultado_pct": round(cambio_pct, 2),
                "motivo": f"✅ Objetivo alcanzado (+{cambio_pct:.2f}%)"
            }
        elif cambio_pct > 0 and not vela_intencion:
            return {
                "precio_salida": vela["close"],
                "timestamp_salida": vela["timestamp_dt"],
                "resultado_pct": round(cambio_pct, 2),
                "motivo": f"✅ Cierre rentable sin intención (+{cambio_pct:.2f}%)"
            }
        elif cambio_pct <= 0 and estructura_perdida and not vela_intencion:
            return {
                "precio_salida": vela["close"],
                "timestamp_salida": vela["timestamp_dt"],
                "resultado_pct": round(cambio_pct, 2),
                "motivo": f"❌ Reversa sin intención y pérdida de estructura"
            }

    return None  # No se activó ningún cierre dentro del rango