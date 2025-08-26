import time
from datetime import datetime, timezone
import warnings
import config
from AnalisisGeneral import run_analisis_general
from AnalisisDetalle import run_analisis_detalle
import trade_manager
from live_ia_engine import get_ai_prediction, fetch_live_data
import asyncio
from notifications import send_telegram_alert

warnings.simplefilter(action='ignore', category=FutureWarning)

def print_report(acceleration_candidates: list, reversal_signals: list):
    """Imprime los rankings de aceleración y reversión."""
    now = datetime.now(timezone.utc)
    print("\n== 🚀 RANKING DE ACELERACIÓN (CONTEXTO) ==")
    if acceleration_candidates:
        sorted_accel = sorted(acceleration_candidates, key=lambda x: x['score'], reverse=True)
        # Mostramos solo el Top 5 en la consola
        for i, cand in enumerate(sorted_accel[:5]):
            signal_marker = "🔥" if cand.get('is_strong') else " "
            direction = "ALCISTA 🟢" if cand['change_15m'] > 0 else "BAJISTA 🔴"
            print(f"{signal_marker} {i+1}. {cand['symbol']}: {direction} | Score: {cand['score']:.2f} | Acel. 15m: {cand['change_15m']*100:+.2f}% | Vol: {cand['vol_mult']:.1f}x prom.")
    else:
        print("(No se han podido analizar candidatos)")

    print("\n== 🚨 RANKING DE REVERSIONES (CLÍMAX RECIENTE) ==")
    if reversal_signals:
        unique_signals = {f"{s['symbol']}_{s['pattern']}_{s['time']}": s for s in sorted(reversal_signals, key=lambda x: x['time'], reverse=True)}.values()
        for signal in list(unique_signals)[:5]:
            # Convertimos el tiempo a un objeto datetime si es un string
            signal_time = pd.to_datetime(signal['time']) if isinstance(signal['time'], str) else signal['time']
            time_ago = (now - signal_time).total_seconds() / 60
            print(f"- {signal['pattern']} en {signal['symbol']} (hace {time_ago:.0f} min)")
    else:
        print("(No se han detectado patrones de reversión)")

async def main():
    """Bucle principal asíncrono que ejecuta el cazador."""
    print(f"--- 🔥 Cazador de Clímax con IA y Alertas de Telegram ---")
    
    while True:
        try:
            start_time = time.monotonic()
            now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n--- Análisis a las {now_str} UTC ---")

            # --- FASE 1: ANÁLISIS GENERAL ---
            watchlist = run_analisis_general()

            # --- FASE 2 y 3: ANÁLISIS DE DETALLE Y CONSULTA A IA ---
            if watchlist:
                acceleration_candidates, reversals = run_analisis_detalle(watchlist)
                
                print("\n--- Procesando señales para Alertas de Telegram ---")
                if acceleration_candidates:
                    # Obtenemos datos de BTC/ETH una sola vez para ser eficientes
                    btc_data = fetch_live_data('BTC/USDT')
                    eth_data = fetch_live_data('ETH/USDT')

                    if btc_data is None or eth_data is None:
                        print("  -> No se pudo cargar el contexto de mercado (BTC/ETH).")
                    else:
                        sorted_candidates = sorted(acceleration_candidates, key=lambda x: x['score'], reverse=True)
                        
                        for cand in sorted_candidates:
                            # 1. Filtro por Score en vivo
                            if cand['score'] >= config.TELEGRAM_SCORE_THRESHOLD:
                                print(f"  -> {cand['symbol']} (Score: {cand['score']:.2f}) califica para análisis de IA...")
                                
                                # 2. Consulta a la IA como filtro de calidad final
                                ai_result = get_ai_prediction(cand['symbol'], btc_data, eth_data)
                                
                                if ai_result and ai_result['win_probability'] >= config.AI_CONFIDENCE_THRESHOLD:

                                    win_prob = ai_result['win_probability']
                                    print(f"    - PREDICCIÓN IA (Prob. Éxito): {win_prob * 100:.2f}%")
                                    
                                    # Formateamos el mensaje para Telegram
                                    mensaje = (
                                        f"🚨 *Alerta de Clímax con IA* 🚨\n\n"
                                        f"*Símbolo:* `{cand['symbol']}`\n"
                                        f"*Dirección:* {'ALCISTA 🟢' if cand['change_15m'] > 0 else 'BAJISTA 🔴'}\n\n"
                                        f"*Score en Vivo:* `{cand['score']:.2f}`\n"
                                        f"*Confianza IA:* **{win_prob * 100:.2f}%**\n\n"
                                        f"*Entrada Sugerida:* `{ai_result['entry_price']:.4f}`\n"
                                        f"*Stop Loss:* `{ai_result['stop_loss']:.4f}`\n"
                                        f"*Take Profit:* `{ai_result['take_profit']:.4f}`"
                                    )
                                    # 3. Envío de la Alerta por Telegram
                                    await send_telegram_alert(mensaje)
                                    
                                    # 4. (Opcional) Guardar en alertas.json
                                    # trade_manager.create_ia_alert(cand, ai_result)
                                else:
                                    print(f"    - No se pudo obtener una predicción de la IA para {cand['symbol']}.")
                
                # Imprimimos el reporte en consola al final del ciclo
                print_report(acceleration_candidates, reversals)

            # --- CÁLCULO DE TIEMPO DE CICLO EXACTO ---
            end_time = time.monotonic()
            duration = end_time - start_time
            sleep_time = config.REFRESH_SECONDS - duration
            
            if sleep_time > 0:
                print(f"\nAnálisis completado en {duration:.1f} segundos. Esperando {sleep_time:.1f} segundos...")
                await asyncio.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\nCazador detenido."); break
        except Exception as e:
            print(f"Error en el bucle principal: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass