# main.py (Versión Final - Especialista Anti-FOMO / Shorts)

from datetime import datetime, timezone
import time
import os
import sys

import scanner
import operations_manager
import position_evaluator
from utils import enviar_telegram, esperar_proxima_vela

# --- CONFIGURACIÓN ---
MAX_SHORT_TRADES = 6 # Límite total, ahora solo para shorts
LOCK_FILE = "bot.lock"

# --- LÓGICA DE BLOQUEO ---
if os.path.exists(LOCK_FILE):
    print("❌ ERROR: Ya hay una instancia del bot corriendo.")
    sys.exit()

with open(LOCK_FILE, "w") as f:
    f.write(str(os.getpid()))

print("🚀 Iniciando Bot Especialista Anti-FOMO (Shorts)...")

try:
    while True:
        try:
            print(f"\n🛰️  Iniciando ciclo | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
            
            # --- FASE 1: GESTIÓN DE OPERACIONES EXISTENTES ---
            print("\n--- Fase de Gestión ---")
            open_trades = operations_manager.load_data("abiertas.json")
            if open_trades:
                actions_to_take = position_evaluator.evaluate_open_positions(open_trades, scanner.exchange)
                if actions_to_take:
                    print(f"🔎 Se encontraron {len(actions_to_take)} acciones de gestión:")
                    for action in actions_to_take:
                        if action['action'] == 'CLOSE':
                            ticker = scanner.exchange.fetch_ticker(action['symbol'])
                            current_price = ticker['last']
                            closed_trade = operations_manager.close_trade_by_id(action['trade_id'], current_price, action['reason'])
                            if closed_trade:
                                 enviar_telegram(f"✅ CIERRE AUTOMÁTICO: {action['symbol']} cerrada por {action['reason']}.")
                else:
                    print("  No se requieren acciones de gestión.")
            else:
                print("  No hay operaciones abiertas para gestionar.")

            # --- FASE 2: BÚSQUEDA DE NUEVAS ALERTAS (Solo Shorts) ---
            print("\n--- Fase de Escaneo de Alertas (Solo Shorts) ---")
            accepted_counts = operations_manager.count_accepted_trades_by_type()
            current_shorts = accepted_counts.get('short', 0)

            print(f"📊 Operaciones Short aceptadas: {current_shorts} de {MAX_SHORT_TRADES}")

            if current_shorts >= MAX_SHORT_TRADES:
                print(f"⚠️ Límite de {MAX_SHORT_TRADES} operaciones short alcanzado. Omitiendo escaneo.")
            else:
                short_signals = scanner.scan_for_shorts()
                if short_signals:
                    alerts = operations_manager.load_data("alertas.json")
                    existing_symbols = [t['symbol'] for t in open_trades] + [a['symbol'] for a in alerts]
                    available_new_signals = [s for s in short_signals if s['symbol'] not in existing_symbols]

                    if available_new_signals:
                        best_signal = sorted(available_new_signals, key=lambda x: x['probabilidad_ia'], reverse=True)[0]
                        print(f"\n🏆 Nueva ALERTA generada (mejor opción short): {best_signal['symbol']} con {best_signal['probabilidad_ia']*100:.2f}%")
                        operations_manager.save_new_alert(best_signal)
                    else:
                        print("✔️ Todas las señales encontradas ya tienen una posición o alerta existente.")
                else:
                    print("✅ No se encontraron señales de venta de alta confianza en este ciclo.")
            
            esperar_proxima_vela(60)
            
        except Exception as e:
            print(f"❌ Error en el bucle principal: {e}")
            time.sleep(300)

finally:
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)
    print("\n🛑 Generador de Alertas detenido.")