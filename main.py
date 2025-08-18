import time
from datetime import datetime, timezone
import warnings
import config
from AnalisisGeneral import run_analisis_general
from AnalisisDetalle import run_analisis_detalle

# Ignorar advertencias de pandas que no son críticas
warnings.simplefilter(action='ignore', category=FutureWarning)

def print_report(acceleration_candidates: list, reversal_signals: list):
    """Imprime los rankings de aceleración y reversión."""
    now = datetime.now(timezone.utc)
    
    print("\n== 🚀 RANKING DE ACELERACIÓN (CONTEXTO) ==")
    if acceleration_candidates:
        sorted_accel = sorted(acceleration_candidates, key=lambda x: x['score'], reverse=True)
        for i, cand in enumerate(sorted_accel[:5]):
            signal_marker = "🔥" if cand['is_strong'] else " "
            direction = "ALCISTA 🟢" if cand['change_15m'] > 0 else "BAJISTA 🔴"
            print(f"{signal_marker} {i+1}. {cand['symbol']}: {direction} | Score: {cand['score']:.2f} | Acel. 15m: {cand['change_15m']*100:+.2f}% | Vol: {cand['vol_mult']:.1f}x prom.")
    else:
        print("(No se han podido analizar candidatos)")

    print("\n== 🚨 RANKING DE REVERSIONES (CLÍMAX RECIENTE) ==")
    if reversal_signals:
        unique_signals = {f"{s['symbol']}_{s['pattern']}_{s['time'].isoformat()}": s for s in sorted(reversal_signals, key=lambda x: x['time'], reverse=True)}.values()
        for signal in list(unique_signals)[:5]:
            time_ago = (now - signal['time']).total_seconds() / 60
            print(f"- {signal['pattern']} en {signal['symbol']} (hace {time_ago:.0f} min)")
    else:
        print("(No se han detectado patrones de reversión)")

if __name__ == "__main__":
    print(f"--- 🔥 Cazador de Clímax (Sistema Modular) ---")

    while True:
        try:
            start_time = time.monotonic()
            now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n--- Análisis a las {now_str} UTC ---")

            # --- FASE 1 ---
            watchlist = run_analisis_general()

            # --- FASE 2 ---
            if watchlist:
                acceleration, reversals = run_analisis_detalle(watchlist)
                print_report(acceleration, reversals)
            else:
                print("  -> No se encontraron activos para la Fase 2. Reintentando...")

            # --- CÁLCULO DE TIEMPO DE CICLO EXACTO ---
            end_time = time.monotonic()
            duration = end_time - start_time
            sleep_time = config.REFRESH_SECONDS - duration
            
            if sleep_time > 0:
                print(f"\nAnálisis completado en {duration:.1f} segundos. Esperando {sleep_time:.1f} segundos...")
                time.sleep(sleep_time)
            else:
                print(f"\nADVERTENCIA: El análisis tardó {duration:.1f} segundos, más que el ciclo de {config.REFRESH_SECONDS} segundos.")

        except KeyboardInterrupt:
            print("\nCazador detenido."); break
        except Exception as e:
            print(f"Error en el bucle principal: {e}"); time.sleep(60)