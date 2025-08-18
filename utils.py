# === utils.py ===

import os
import json
import pandas as pd
import requests
import html
import socket
import time
from datetime import datetime, timezone

def compute_indicators(df):
    # Asegurar que columnas clave sean numéricas
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce')

    # Eliminar filas con NaNs críticos
    df = df.dropna(subset=['close', 'volume'])

    # 🔥 RSI manual
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # 🔥 MACD manual
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()

    # 🔥 Promedio móvil de volumen (20 velas)
    df['volume_ma'] = df['volume'].rolling(window=20).mean()

    return df


def obtener_siguiente_id():
    archivo = "contador_id_1h.txt"
    if not os.path.exists(archivo):
        with open(archivo, "w") as f:
            f.write("1")
        return 1
    with open(archivo, "r+") as f:
        actual = int(f.read().strip())
        siguiente = actual + 1
        f.seek(0)
        f.write(str(siguiente))
        f.truncate()
        return siguiente

def enviar_telegram(mensaje):
    TOKEN = '7732548537:AAEJvyfq9ErspOa-insph0NULb_7FUeI91g'
    CHAT_ID = '714501781'
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    data = {'chat_id': CHAT_ID, 'text': html.escape(mensaje)}
    requests.post(url, data=data)

def detectar_estructura(exchange, symbol, timeframe="1h"):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=30)
        df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # 🔥 LIMPIEZA REAL
        df = df.dropna()
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)

        max1 = df['high'].iloc[-1]
        max2 = df['high'].iloc[-5]
        min1 = df['low'].iloc[-1]
        min2 = df['low'].iloc[-5]

        if max1 > max2 and min1 > min2:
            return "alcista"
        elif max1 < max2 and min1 < min2:
            return "bajista"
        else:
            return "rango"
    except Exception as e:
        print(f"⚠️ Error al detectar estructura de {symbol} en {timeframe}: {e}")
        return "desconocida"


#Busca si el origen es de local o de Oracle
def origen_ejecucion():
    nombre_equipo = socket.gethostname().lower()
    if "bot-trading" in nombre_equipo:
        return "Oracle"
    else:
        return "Local"
    
def esperar_proxima_vela(intervalo_minutos=60):
    """
    Calcula los segundos restantes hasta la siguiente vela completa y espera.
    Ej: Si son las 15:25 y el intervalo es 60, esperará hasta las 16:00:02.
    """
    ahora = datetime.now(timezone.utc)
    minuto_actual = ahora.minute
    segundo_actual = ahora.second

    minutos_faltantes = intervalo_minutos - (minuto_actual % intervalo_minutos)

    # Segundos a esperar hasta el inicio del siguiente minuto
    segundos_hasta_minuto_cero = (minutos_faltantes - 1) * 60 + (60 - segundo_actual)

    # Añadimos un par de segundos de margen para asegurar que la vela ya se haya formado
    segundos_dormir = segundos_hasta_minuto_cero + 2

    # Asegurarnos de que no sea un valor negativo si se ejecuta justo en el cambio
    if segundos_dormir > intervalo_minutos * 60:
        segundos_dormir -= intervalo_minutos * 60

    print(f"🕒 Esperando {int(segundos_dormir)} segundos hasta la próxima vela de {intervalo_minutos} min...")
    time.sleep(segundos_dormir)