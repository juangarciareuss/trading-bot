from binance.client import Client
import pandas as pd
import time

# === 1. TUS CREDENCIALES DE API ===
API_KEY = 'TU_API_KEY'
API_SECRET = 'TU_API_SECRET'

client = Client(API_KEY, API_SECRET)
client.FUTURES_URL = 'https://fapi.binance.com'

# === 2. FUNCIÓN PARA DESCARGAR TODOS TUS TRADES POR SÍMBOLO ===
def get_all_futures_trades(symbol):
    trades = []
    from_id = 0

    while True:
        try:
            results = client.futures_account_trades(symbol=symbol, fromId=from_id, limit=1000)
            if not results:
                break
            trades.extend(results)
            from_id = results[-1]['id'] + 1
            time.sleep(0.1)  # evitar rate limit
        except Exception as e:
            print(f"⚠️ Error en {symbol}: {e}")
            break

    return trades

# === 3. OBTENER TODOS LOS SÍMBOLOS ACTIVOS DE FUTUROS USDT ===
def get_all_symbols():
    info = client.futures_exchange_info()
    return [s['symbol'] for s in info['symbols'] if s['contractType'] == 'PERPETUAL' and s['quoteAsset'] == 'USDT']

symbols = get_all_symbols()
print(f"🔍 Total símbolos detectados: {len(symbols)}")

# === 4. DESCARGAR TODOS LOS TRADES DE CADA SÍMBOLO ===
all_trades = []

for symbol in symbols:
    print(f"📥 Descargando {symbol}...")
    trades = get_all_futures_trades(symbol)
    for t in trades:
        t['symbol'] = symbol
    all_trades.extend(trades)

# === 5. GUARDAR COMO CSV ===
df = pd.DataFrame(all_trades)

if not df.empty:
    df['time'] = pd.to_datetime(df['time'], unit='ms')
    df.to_csv("futuros_binance_todos_los_trades.csv", index=False)
    print("✅ Archivo guardado: 'futuros_binance_todos_los_trades.csv'")
else:
    print("⚠️ No se encontraron trades.")
