# /AnalisisGeneral.py

import config
from utils import exchange

def run_analisis_general() -> list:
    """
    Escanea el momentum de 5 minutos de todos los activos líquidos para encontrar
    a los 'sospechosos' con la variación más fuerte.
    """
    print("Fase 1: Ejecutando Análisis General de Momentum...")
    
    all_tickers = exchange.fetch_tickers()
    liquid_symbols = [
        symbol for symbol, ticker in all_tickers.items()
        if symbol.endswith('/USDT:USDT') and ticker.get('quoteVolume', 0) > config.MIN_24H_VOLUME_USD
    ]
    
    if not liquid_symbols:
        print("  -> No se encontraron activos con liquidez suficiente.")
        return []

    momentum_candidates = []
    for i, symbol in enumerate(liquid_symbols):
        print(f"  -> Escaneando {i+1}/{len(liquid_symbols)}: {symbol}", end='\r')
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, config.TIMEFRAME_ANALYSIS, limit=3)
            if len(ohlcv) < 2: continue
            
            last_closed_candle = ohlcv[-2]
            open_price, close_price = last_closed_candle[1], last_closed_candle[4]

            if open_price > 0:
                momentum_pct = (close_price - open_price) / open_price * 100
                momentum_candidates.append({'symbol': symbol, 'momentum_5m': momentum_pct})
        except Exception:
            continue
    
    print("\n  -> Escaneo de momentum completado.")

    if not momentum_candidates:
        print("  -> No se pudo calcular el momentum para los activos.")
        return []
        
    sorted_by_momentum = sorted(momentum_candidates, key=lambda x: abs(x['momentum_5m']), reverse=True)
    watchlist = [cand['symbol'] for cand in sorted_by_momentum[:config.WATCHLIST_SIZE]]
    
    if watchlist:
        print(f"  -> Top {len(watchlist)} 'sospechosos' identificados para Análisis de Detalle.")
        for cand in sorted_by_momentum[:3]:
            print(f"    - {cand['symbol']}: Momentum 5m: {cand['momentum_5m']:+.2f}%")
            
    return watchlist