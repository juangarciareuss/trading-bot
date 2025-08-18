from utils import exchange
import config

def run_phase_1_radar() -> list:
    # PEGA ESTE CÓDIGO DENTRO DE TU FUNCIÓN run_phase_1_radar

    print("Fase 1: Escaneando momentum de 5 minutos en todos los activos líquidos...")

    # Paso A: Obtener todos los activos con liquidez
    all_tickers = exchange.fetch_tickers()
    liquid_symbols = []
    for symbol, ticker in all_tickers.items():
        if symbol.endswith('/USDT:USDT') and ticker.get('quoteVolume') is not None:
            if ticker['quoteVolume'] > MIN_24H_VOLUME_USD:
                liquid_symbols.append(symbol)

    if not liquid_symbols:
        print("  -> No se encontraron activos con liquidez suficiente.")
        return []

    # Paso B: Medir momentum de 5m en cada activo líquido
    momentum_candidates = []
    for i, symbol in enumerate(liquid_symbols):
        # Indicador de progreso
        print(f"  -> Escaneando {i+1}/{len(liquid_symbols)}: {symbol}", end='\r')
        try:
            # Pedir solo las últimas 3 velas para ser rápidos
            ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME_ANALYSIS, limit=3)
            if len(ohlcv) < 2: continue

            last_closed_candle = ohlcv[-2]
            open_price = last_closed_candle[1]
            close_price = last_closed_candle[4]

            if open_price > 0:
                momentum_pct = (close_price - open_price) / open_price * 100
                momentum_candidates.append({'symbol': symbol, 'momentum_5m': momentum_pct})
        except Exception:
            continue

    print("\n  -> Escaneo de momentum completado.")

    if not momentum_candidates:
        print("  -> No se pudo calcular el momentum para los activos.")
        return []

    # Crear la watchlist con el Top de activos con más momentum
    sorted_by_momentum = sorted(momentum_candidates, key=lambda x: abs(x['momentum_5m']), reverse=True)
    watchlist = [cand['symbol'] for cand in sorted_by_momentum[:WATCHLIST_SIZE]]

    if watchlist:
        print(f"  -> Top {len(watchlist)} 'sospechosos' identificados para análisis de contexto.")
        for cand in sorted_by_momentum[:3]:
            print(f"    - {cand['symbol']}: Momentum 5m: {cand['momentum_5m']:+.2f}%")

    return watchlist