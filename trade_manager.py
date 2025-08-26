# /trade_manager.py

import json
from datetime import datetime, timezone
import os

# Definimos los nombres de los archivos como constantes
ABIERTAS_FILE = 'abiertas.json'
CERRADAS_FILE = 'cerradas.json'
ALERTAS_FILE = 'alertas.json'

def load_from_json(file_path):
    """Carga datos desde un archivo JSON."""
    try:
        # Asegurarse de que el archivo no esté vacío
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            with open(file_path, 'r') as f:
                return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return []

def save_to_json(data, file_path):
    """Guarda datos en un archivo JSON."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

def close_trade_by_id(trade_id, close_price, reason="Cierre Manual"):
    """
    Mueve una operación de abiertas.json a cerradas.json.
    """
    abiertas = load_from_json(ABIERTAS_FILE)
    cerradas = load_from_json(CERRADAS_FILE)

    trade_to_close = None
    # Buscar la operación por su ID
    for trade in abiertas:
        if trade.get('id') == trade_id:
            trade_to_close = trade
            break

    if trade_to_close:
        # Eliminar la operación de la lista de abiertas
        abiertas = [t for t in abiertas if t.get('id') != trade_id]

        # Actualizar la operación con los datos de cierre
        trade_to_close['status'] = 'CERRADA'
        trade_to_close['precio_cierre'] = close_price
        trade_to_close['timestamp_cierre'] = datetime.now(timezone.utc).isoformat()
        trade_to_close['motivo_cierre'] = reason

        # Añadir a la lista de cerradas
        cerradas.append(trade_to_close)

        # Guardar ambos archivos
        save_to_json(abiertas, ABIERTAS_FILE)
        save_to_json(cerradas, CERRADAS_FILE)
        print(f"✅ Operación {trade_id} movida de abiertas a cerradas.")
        return True
    else:
        print(f"⚠️ No se encontró la operación con ID {trade_id} en abiertas.json.")
        return False

# PEGA ESTA FUNCIÓN AL FINAL DE TU ARCHIVO trade_manager.py

def create_climax_alert(candidate_data):
    """
    Registra una nueva alerta de clímax en alertas.json si supera el score
    y no es un duplicado reciente.
    """
    # La variable ALERTAS_FILE debe estar definida al principio del archivo
    # si no lo está, añade: ALERTAS_FILE = 'alertas.json'
    alertas = load_from_json(ALERTAS_FILE)
    now = datetime.now(timezone.utc)

    # Comprobar si ya existe una alerta para el mismo símbolo
    for alerta in alertas:
        if alerta.get('symbol') == candidate_data['symbol']:
            print(f"  -> Alerta para {candidate_data['symbol']} ya existe. Omitiendo.")
            return None

    # Construir la nueva alerta
    alert_id = f"climax_{candidate_data['symbol'].replace('/', '')}_{now.strftime('%Y%m%d%H%M%S')}"

    new_alert = {
        "id": alert_id,
        "symbol": candidate_data['symbol'],
        "strategy": "Climax Reversal",
        "alert_time": now.isoformat(),
        "direction": "ALCISTA 🟢" if candidate_data['change_15m'] > 0 else "BAJISTA 🔴",
        "details": {
            "score": round(candidate_data['score'], 4),
            "acel_15m_pct": round(candidate_data['change_15m'] * 100, 2),
            "vol_mult": round(candidate_data['vol_mult'], 2)
        }
    }

    alertas.append(new_alert)
    save_to_json(alertas, ALERTAS_FILE)
    print(f"✅ NUEVA ALERTA para {candidate_data['symbol']} registrada con Score: {new_alert['details']['score']:.2f}")
    return new_alert