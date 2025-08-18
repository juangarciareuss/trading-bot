import os
import json
import pandas as pd
from binance.client import Client
from datetime import datetime, timezone
from time import sleep
from tqdm import tqdm
import argparse
import re

# === CONFIGURACIÓN API ===
API_KEY = "0bFrw5FvPTTKFa6ICo8tcx9M6ci1Bnl1RhHft6JaAMtuk00KQVqD0IaNxlTYyVIJ"
API_SECRET = "O94hJoV2kcCe1NJS7rjl6v53tL00NhXyiF1uelPUtbrE0rqlwOF6rzAiGm57cN5d"
client = Client(api_key=API_KEY, api_secret=API_SECRET)

# === CONFIG GENERAL ===
CONFIG_PATH = "backtest/config/activos_en_medicion.json"
BASE_PATH = "backtest/data/historico"
TIMEFRAMES = {
    "1h": Client.KLINE_INTERVAL_1HOUR,
    # "4h": Client.KLINE_INTERVAL_4HOUR,
    # "1d": Client.KLINE_INTERVAL_1DAY
}
LIMIT = 1000

# === FUNCIONES ===
def simbolo_para_archivo(symbol):
    seguro = re.sub(r'\W+', '_', symbol)
    if re.match(r'^\d', seguro):
        seguro = f"sym_{seguro}"
    return seguro

def cargar_activos():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return []

def descargar_historico(symbol, tf_alias, tf_binance):
    safe_symbol = simbolo_para_archivo(symbol)
    path_csv = os.path.join(BASE_PATH, tf_alias, f"{safe_symbol}.csv")

    if os.path.exists(path_csv):
        df_existente = pd.read_csv(path_csv)
        last_time = int(df_existente.iloc[-1]['timestamp']) + 1 if not df_existente.empty else int(datetime(2021, 1, 1).timestamp() * 1000)
    else:
        df_existente = pd.DataFrame()
        last_time = int(datetime(2021, 1, 1).timestamp() * 1000)

    while True:
        try:
            now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
            if last_time > now_ts:
                print(f"🚫 {symbol} [{tf_alias}] alcanzó el presente.")
                break

            start_str = datetime.fromtimestamp(last_time / 1000, tz=timezone.utc).strftime("%d %b, %Y %H:%M:%S")
            klines = client.get_historical_klines(symbol, tf_binance, start_str, limit=LIMIT)

            if not klines:
                print(f"🟡 {symbol} [{tf_alias}] sin nuevos datos.")
                break

            df = pd.DataFrame(klines, columns=[
                "timestamp", "open", "high", "low", "close", "volume",
                "close_time", "quote_asset_volume", "number_of_trades",
                "taker_buy_base", "taker_buy_quote", "ignore"
            ])
            df.drop(columns=["ignore"], inplace=True)
            df = df.astype({
                "timestamp": "int64",
                "open": "float",
                "high": "float",
                "low": "float",
                "close": "float",
                "volume": "float",
                "close_time": "int64",
                "quote_asset_volume": "float",
                "number_of_trades": "int64",
                "taker_buy_base": "float",
                "taker_buy_quote": "float"
            })
            df["timestamp_dt"] = pd.to_datetime(df["timestamp"], unit="ms")

            if len(df) == 1 and int(df["timestamp"].iloc[-1]) <= last_time:
                print(f"🚫 {symbol} [{tf_alias}] sin avance real, probablemente vela en formación.")
                break

            df_existente = pd.concat([df_existente, df], ignore_index=True).drop_duplicates(subset="timestamp")
            df_existente.to_csv(path_csv, index=False)

            last_time = int(df["timestamp"].iloc[-1]) + 1
            print(f"✅ {symbol} [{tf_alias}] +{len(df)} velas")
            sleep(0.2)

        except Exception as e:
            print(f"❌ Error con {symbol} [{tf_alias}]: {e}")
            with open("errores_descarga.txt", "a") as log:
                log.write(f"{datetime.now(timezone.utc)} - {symbol} [{tf_alias}] - {str(e)}\n")
            sleep(1)
            break

def main(tf_arg=None, symbol_arg=None):
    activos = cargar_activos()

    # Si no se pasó símbolo y no hay lista, usar uno por defecto
    if not symbol_arg and not activos:
        activos = ["BNBUSDT"]

    elif symbol_arg:
        activos = [symbol_arg]

    for tf_alias, tf_binance in TIMEFRAMES.items():
        if tf_arg and tf_arg != tf_alias:
            continue

        print(f"\n⏳ Descargando timeframe: {tf_alias}")
        os.makedirs(os.path.join(BASE_PATH, tf_alias), exist_ok=True)

        for symbol in tqdm(activos):
            descargar_historico(symbol, tf_alias, tf_binance)
            sleep(0.1)

# === CLI ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Descarga histórico de criptomonedas desde Binance")
    parser.add_argument("--tf", type=str, help="Timeframe: 1h, 4h, 1d", required=False)
    parser.add_argument("--symbol", type=str, help="Símbolo de cripto (ej: BTCUSDT)", required=False)
    args = parser.parse_args()

    if args.tf and args.tf not in TIMEFRAMES:
        print("❌ Timeframe no válido. Usa: 1h, 4h o 1d")
    else:
        main(tf_arg=args.tf or "1h", symbol_arg=args.symbol)
