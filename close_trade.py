# close_trade.py (Versión integrada)
import json
import os
from datetime import datetime, timezone

# 🔥 ¡Importamos tu función existente! 🔥
from cerradas import guardar_cerradas

ABIERTAS_FILE = "abiertas.json"

def load_open_trades():
    if os.path.exists(ABIERTAS_FILE) and os.path.getsize(ABIERTAS_FILE) > 0:
        with open(ABIERTAS_FILE, 'r') as f:
            try: return json.load(f)
            except json.JSONDecodeError: return []
    return []

def save_updated_open_trades(trades):
    with open(ABIERTAS_FILE, 'w') as f:
        json.dump(trades, f, indent=4)

def main():
    open_trades = load_open_trades()
    if not open_trades:
        print("❌ No hay operaciones abiertas para cerrar.")
        return

    print("--- Operaciones Abiertas ---")
    for i, trade in enumerate(open_trades):
        print(f"[{i}] ID: {trade.get('id', 'N/A')[:8]} | Symbol: {trade['symbol']} @ {trade['precio_entrada']}")

    try:
        choice_idx = int(input("\n➡️  Introduce el NÚMERO de la operación que quieres cerrar: "))
        trade_to_close = open_trades[choice_idx]

        close_price_str = input(f"➡️  Introduce el PRECIO de cierre para {trade_to_close['symbol']}: ")
        close_price = float(close_price_str)

        reason = input("➡️  Introduce el MOTIVO del cierre (ej: TP, SL, Manual): ")

    except (ValueError, IndexError):
        print("❌ Entrada inválida. Por favor, introduce números correctos.")
        return

    # 1. Preparamos el objeto de la operación cerrada
    closed_trade = trade_to_close.copy()
    closed_trade['estado'] = 'cerrado'
    closed_trade['precio_cierre'] = close_price # Nombre de columna consistente con el dashboard
    closed_trade['motivo'] = reason
    closed_trade['timestamp_cierre'] = datetime.now(timezone.utc).isoformat()
    
    # 2. 🔥 Usamos TU función para guardarla en cerradas.json 🔥
    guardar_cerradas(closed_trade)
    
    # 3. Eliminamos la operación de la lista de abiertas
    open_trades.pop(choice_idx)
    
    # 4. Guardamos la lista actualizada de operaciones abiertas
    save_updated_open_trades(open_trades)

    print(f"\n✅ ¡Operación para {closed_trade['symbol']} cerrada y guardada usando tu módulo cerradas.py!")

if __name__ == "__main__":
    main()