import operations_manager
from datetime import datetime, timezone, timedelta
import pandas as pd
import json

def main():
    """
    Script de utilidad para mover una operación CERRADA EN LAS ÚLTIMAS 48H 
    de vuelta a abiertas.json.
    """
    all_closed_trades = operations_manager.load_data("cerradas.json")
    if not all_closed_trades:
        print("❌ No hay operaciones en el historial de cerradas.")
        return

    print(f"ℹ️  Encontradas {len(all_closed_trades)} operaciones en el historial.")

    # --- FILTRO DE TIEMPO AÑADIDO ---
    now_utc = datetime.now(timezone.utc)
    cutoff_time = now_utc - timedelta(hours=48)

    recent_closed_trades = []
    for trade in all_closed_trades:
        close_time_str = trade.get('timestamp_cierre')
        if close_time_str:
            # Convertimos el string a un objeto de fecha comparable
            close_time = pd.to_datetime(close_time_str).tz_convert('UTC')
            if close_time > cutoff_time:
                recent_closed_trades.append(trade)

    if not recent_closed_trades:
        print("ℹ️ No se han cerrado operaciones en las últimas 48 horas que cumplan el criterio.")
        return
    # --- FIN DEL FILTRO ---
    
    print(f"✅ Encontradas {len(recent_closed_trades)} operaciones cerradas en las últimas 48 horas.")
    print("--- Selecciona una para Reabrir ---")

    for i, trade in enumerate(recent_closed_trades):
        symbol = trade.get('symbol', 'N/A')
        entry_price = trade.get('precio_entrada', 'N/A')
        close_reason = trade.get('motivo', 'N/A')
        print(f"[{i}] {symbol} @ {entry_price} (Cerrada por: {close_reason})")

    try:
        choice_idx = int(input("\n➡️  Introduce el NÚMERO de la operación que quieres REABRIR: "))
        if not (0 <= choice_idx < len(recent_closed_trades)):
            print("❌ Número inválido.")
            return

        trade_to_reopen = recent_closed_trades[choice_idx]
        confirm = input(f"❓ ¿Estás seguro de que quieres reabrir la operación para {trade_to_reopen['symbol']}? (s/n): ").lower()
        if confirm != 's':
            print("Operación cancelada.")
            return

    except (ValueError, IndexError):
        print("❌ Entrada inválida. Por favor, introduce un número correcto.")
        return

    # Buscamos el trade en la lista original completa para eliminarlo
    all_closed_trades = [t for t in all_closed_trades if t.get('id') != trade_to_reopen.get('id')]
    operations_manager.save_data(all_closed_trades, "cerradas.json")

    # Limpiamos los campos de cierre y movemos el trade a abiertas
    keys_to_remove = ['precio_cierre', 'motivo', 'timestamp_cierre', 'resultado_pct', 'confianza_ia', 'resultado', 'duracion_horas', 'pnl_acumulado']
    for key in keys_to_remove:
        trade_to_reopen.pop(key, None)
    
    # Restauramos el estado a 'aceptada' para que el dashboard la monitoree como real
    trade_to_reopen['estado'] = 'aceptada'

    open_trades = operations_manager.load_data("abiertas.json")
    open_trades.append(trade_to_reopen)
    operations_manager.save_data(open_trades, "abiertas.json")

    print(f"\n✅ ¡Operación para {trade_to_reopen['symbol']} REABIERTA!")

if __name__ == "__main__":
    main()