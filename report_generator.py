# report_generator.py (Versión Sincronizada y Simplificada)

import pandas as pd
import operations_manager

# 🔥 AHORA IMPORTAMOS TODAS LAS HERRAMIENTAS DESDE EL SCANNER
from scanner import exchange, antifomo_model, get_live_features, get_atr_value, get_bet_size, get_short_opportunity_analysis

# --- CONFIGURACIÓN ---
TOP_N_TO_ANALYZE = 25
OUTPUT_CSV = "short_hunter_report.csv"

# --- FUNCIÓN PRINCIPAL DE REPORTE ---
def generate_report():
    """Usa las herramientas del scanner para construir un reporte."""
    all_tickers = exchange.fetch_tickers()
    top_gainers = sorted(
        [t for t in all_tickers.values() if t['symbol'].endswith('/USDT:USDT') and t.get('percentage')],
        key=lambda t: t['percentage'], reverse=True
    )
    
    candidates = []
    print(f"Analizando los {TOP_N_TO_ANALYZE} principales ganadores...")
    for ticker in top_gainers[:TOP_N_TO_ANALYZE]:
        symbol = ticker['symbol'].replace(':USDT', '')
        features, precio = get_live_features(symbol)
        
        if features is not None and not features.isnull().values.any():
            prob = antifomo_model.predict_proba(features)[0][1]
            status, diagnosis = get_short_opportunity_analysis(features, prob)
            
            if status == "🟢 BUENO PARA ENTRAR (SEÑAL ACTIVA)":
                atr = get_atr_value(symbol)
                if atr:
                    atr_normalizado = atr / precio
                    bet_size = get_bet_size(prob, atr_normalizado)
                    signal_for_alert = {
                        'symbol': symbol, 'precio_entrada': float(precio), 'probabilidad_ia': float(prob),
                        'apuesta_sugerida': bet_size, 'atr_value': float(atr), 'tipo': 'short'
                    }
                    operations_manager.save_new_alert(signal_for_alert)
                    print(f"   -> 🔥 ¡Señal ACTIVA para {symbol} enviada a Alertas!")
            
            candidates.append({
                'Símbolo': symbol, 'Estado': status, 'Confianza IA (%)': prob * 100,
                'Diagnóstico': diagnosis, 'Var 24h (%)': features['change_24h'].iloc[-1] * 100,
                'Var 1h (%)': features['change_1h'].iloc[-1] * 100,
                'Dist. Media (%)': features['distance_from_ma_24h'].iloc[-1] * 100,
                'RSI 4H': features['rsi_4h'].iloc[-1],
                'RSI 1D': features['rsi_1d'].iloc[-1],
                'Vol Spike 5m': features['volume_spike_5m'].iloc[-1]
            })
    
    return pd.DataFrame(candidates) if candidates else pd.DataFrame()

# --- EJECUCIÓN (SI SE LLAMA DIRECTAMENTE) ---
if __name__ == "__main__":
    print("Ejecutando generador de reporte en modo standalone...")
    report_df = generate_report()
    if not report_df.empty:
        report_df.to_csv(OUTPUT_CSV, index=False)
        print(f"\n✅ Reporte guardado con éxito en '{OUTPUT_CSV}'.")
    else:
        print("\n⚠️ No se encontraron candidatos.")