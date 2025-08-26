# /dashboard/data_manager.py
import pandas as pd
import os
import json

def load_data(file_path):
    """Carga datos desde un archivo JSON en la raíz del proyecto."""
    root_path = os.path.join(os.path.dirname(__file__), '..', file_path)
    if os.path.exists(root_path) and os.path.getsize(root_path) > 0:
        with open(root_path, 'r') as f: data = json.load(f)
        df = pd.DataFrame(data)
        for col in ['entry_time', 'alert_time', 'timestamp_entrada', 'timestamp_cierre']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce', utc=True)
        return df
    return pd.DataFrame()

def process_closed_trades(df):
    """Calcula las métricas de rendimiento para las operaciones cerradas."""
    if df.empty or 'precio_cierre' not in df.columns: return pd.DataFrame()
    df['precio_entrada'] = pd.to_numeric(df['precio_entrada'], errors='coerce')
    df['precio_cierre'] = pd.to_numeric(df['precio_cierre'], errors='coerce')
    df.dropna(subset=['precio_entrada', 'precio_cierre'], inplace=True)

    # --- CORRECCIÓN DEL ERROR ---
    # Usamos 'direction' si existe, si no, usamos 'tipo' como respaldo.
    direction_col = 'direction' if 'direction' in df.columns else 'tipo'
    if direction_col not in df.columns: return df # No podemos calcular si falta la columna

    df['resultado_pct'] = 100 * df.apply(
        lambda row: ((row['precio_cierre'] - row['precio_entrada']) / row['precio_entrada']) if row[direction_col].upper() == 'LONG'
        else ((row['precio_entrada'] - row['precio_cierre']) / row['precio_entrada']),
        axis=1
    )
    # --- FIN DE LA CORRECCIÓN ---

    df['resultado'] = df['resultado_pct'].apply(lambda x: 'Ganadora' if x > 0 else 'Perdedora')
    entry_col = 'timestamp_entrada' if 'timestamp_entrada' in df.columns else 'entry_time'
    if 'timestamp_cierre' in df.columns and entry_col in df.columns:
        df['duracion_horas'] = (df['timestamp_cierre'] - df[entry_col]).dt.total_seconds() / 3600

    df.sort_values('timestamp_cierre', ascending=True, inplace=True)
    df['pnl_acumulado'] = df['resultado_pct'].cumsum()
    return df

def accept_alert(alert_id, entry_price):
    """Mueve una alerta de alertas.json a abiertas.json, marcándola como aceptada."""
    alertas = load_from_json(ALERTAS_FILE)
    abiertas = load_from_json(ABIERTAS_FILE)

    alert_to_move = None
    for alert in alertas:
        if alert.get('id') == alert_id:
            alert_to_move = alert
            break

    if alert_to_move:
        alertas = [a for a in alertas if a.get('id') != alert_id]

        alert_to_move['status'] = 'ABIERTA'
        alert_to_move['decision'] = 'aceptada'
        alert_to_move['precio_entrada'] = entry_price
        alert_to_move['timestamp_entrada'] = datetime.now(timezone.utc).isoformat()

        abiertas.append(alert_to_move)

        save_to_json(alertas, ALERTAS_FILE)
        save_to_json(abiertas, ABIERTAS_FILE)
        print(f"✅ Alerta {alert_id} aceptada y movida a operaciones abiertas.")
        return True
    return False

def reject_alert(alert_id):
    """Mueve una alerta de alertas.json a cerradas.json, marcándola como rechazada."""
    alertas = load_from_json(ALERTAS_FILE)
    cerradas = load_from_json(CERRADAS_FILE)

    alert_to_move = None
    for alert in alertas:
        if alert.get('id') == alert_id:
            alert_to_move = alert
            break

    if alert_to_move:
        alertas = [a for a in alertas if a.get('id') != alert_id]

        alert_to_move['status'] = 'CERRADA'
        alert_to_move['decision'] = 'rechazada'
        alert_to_move['precio_cierre'] = None
        alert_to_move['timestamp_cierre'] = datetime.now(timezone.utc).isoformat()
        alert_to_move['motivo_cierre'] = 'Rechazada por el usuario'

        cerradas.append(alert_to_move)

        save_to_json(alertas, ALERTAS_FILE)
        save_to_json(cerradas, CERRADAS_FILE)
        print(f"✅ Alerta {alert_id} rechazada y movida al historial.")
        return True
    return False