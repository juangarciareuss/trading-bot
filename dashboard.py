import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
import ccxt
import traceback
import numpy as np
from datetime import datetime, timezone
import operations_manager
import report_generator
import joblib
from io import BytesIO


# --- FUNCIÓN DE EXCEL ---
@st.cache_data
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte_AntiFOMO')
    return output.getvalue()

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Dashboard Anti-FOMO",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CONEXIÓN AL EXCHANGE ---
@st.cache_resource
def init_exchange():
    try:
        exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
        st.sidebar.success("Conectado a Binance para precios en vivo.")
        return exchange
    except Exception as e:
        st.sidebar.error(f"Error conectando a Binance: {e}")
        return None
exchange = init_exchange()

# Pega este bloque después de la función init_exchange
@st.cache_resource
def load_models():
    try:
        antifomo_model = joblib.load("antifomo_model.pkl")
        antifud_model = joblib.load("antifud_model.pkl")
        return antifomo_model, antifud_model
    except FileNotFoundError as e:
        st.error(f"No se pudo cargar un modelo: {e}")
        return None, None

antifomo_model, antifud_model = load_models()

# --- FUNCIONES DE PROCESAMIENTO ---
def load_data(file_path):
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        with open(file_path, 'r') as f: data = json.load(f)
        df = pd.DataFrame(data)
        for col in ['timestamp_entrada', 'timestamp_cierre']:
            if col in df.columns: df[col] = pd.to_datetime(df[col], errors='coerce', utc=True)
        return df
    return pd.DataFrame()

def process_closed_trades(df):
    if df.empty or 'precio_cierre' not in df.columns: return pd.DataFrame()
    df['precio_entrada'] = pd.to_numeric(df['precio_entrada'], errors='coerce')
    df['precio_cierre'] = pd.to_numeric(df['precio_cierre'], errors='coerce')
    df.dropna(subset=['precio_entrada', 'precio_cierre'], inplace=True)
    df['resultado_pct'] = ((df['precio_entrada'] - df['precio_cierre']) / df['precio_entrada']) * 100
    if 'prediccion_ia' in df.columns: df['confianza_ia'] = pd.to_numeric(df['prediccion_ia'].astype(str).str.replace('%', ''), errors='coerce')
    else: df['confianza_ia'] = 0
    df['resultado'] = df['resultado_pct'].apply(lambda x: 'Ganadora' if x > 0 else 'Perdedora')
    if 'timestamp_cierre' in df.columns and 'timestamp_entrada' in df.columns: df['duracion_horas'] = (df['timestamp_cierre'] - df['timestamp_entrada']).dt.total_seconds() / 3600
    df.sort_values('timestamp_cierre', ascending=True, inplace=True)
    df['pnl_acumulado'] = df['resultado_pct'].cumsum()
    return df

def get_live_features(symbol):
    """Obtiene las features de una moneda para el análisis de la IA."""
    try:
        data = {}
        timeframes = {'1d': 26, '4h': 26, '1h': 26, '5m': 13}
        for tf, min_candles in timeframes.items():
            ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=50)
            if len(ohlcv) < min_candles: return None
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms'); df.set_index('timestamp', inplace=True); data[tf] = df
        
        df = data['1h'].copy()
        df['change_24h'] = df['close'].pct_change(periods=24); df['change_1h'] = df['close'].pct_change(periods=1)
        ma_24h = df['close'].rolling(24).mean(); df['distance_from_ma_24h'] = (df['close'] - ma_24h) / ma_24h
        for tf_context in ['4h', '1d']:
            delta = data[tf_context]['close'].diff(1); gain = delta.where(delta > 0, 0); loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14).mean(); avg_loss = loss.rolling(window=14).mean(); rs = avg_gain / avg_loss
            data[tf_context][f'rsi_{tf_context}'] = 100 - (100 / (1 + rs))
        data['5m']['volume_spike_5m'] = data['5m']['volume'] / data['5m']['volume'].rolling(window=12).mean()
        df = pd.merge_asof(df.sort_index(), data['4h'][['rsi_4h']].sort_index(), on='timestamp', direction='backward')
        df = pd.merge_asof(df.sort_index(), data['1d'][['rsi_1d']].sort_index(), on='timestamp', direction='backward')
        df = pd.merge_asof(df.sort_index(), data['5m'][['volume_spike_5m']].sort_index(), on='timestamp', direction='backward')
        
        feature_cols = ['change_24h', 'change_1h', 'distance_from_ma_24h', 'rsi_4h', 'rsi_1d', 'volume_spike_5m']
        return df[feature_cols].iloc[-1:]
    except Exception:
        return None

def run_hunter_analysis():
    """Realiza el análisis completo del cazador y devuelve un DataFrame."""
    with st.spinner("Analizando el mercado... Esto puede tardar 1-2 minutos."):
        top_gainers = sorted(
            [t for t in exchange.fetch_tickers().values() if t['symbol'].endswith('/USDT:USDT') and t.get('percentage')],
            key=lambda t: t['percentage'], reverse=True
        )
        
        candidates = []
        for ticker in top_gainers[:25]:
            symbol = ticker['symbol'].replace(':USDT', '')
            features = get_live_features(symbol)
            
            if features is not None and not features.isnull().values.any():
                prob = antifomo_model.predict_proba(features)[0][1]
                candidates.append({'Símbolo': symbol, 'Confianza IA (%)': prob*100, 'Var 24h (%)': features['change_24h'].iloc[-1]*100})
        
        if candidates:
            return pd.DataFrame(candidates)
        else:
            return pd.DataFrame()


def cerrar_operacion_manual(trade_id, symbol):
    """
    Función callback para el botón de cierre. Obtiene el precio actual y cierra el trade.
    """
    print(f"Iniciando cierre manual para {symbol} (ID: {trade_id[:8]})")
    try:
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        operations_manager.close_trade_by_id(trade_id, current_price, "Cierre Manual (Dashboard)")
        st.success(f"¡Operación {symbol} cerrada manualmente al precio {current_price}!")
    except Exception as e:
        st.error(f"Error al cerrar {symbol}: {e}")

def display_live_trades_section(df_live, title, is_virtual=False):
    st.header(title)
    PROYECCION_CIERRE_H = 48.0
    
    if not df_live.empty and exchange:
        try:
            # --- FASE 1: CÁLCULO DE DATOS EN VIVO ---
            live_pnl_list, live_duration_list = [], []
            symbols_in_file = df_live['symbol'].unique().tolist()
            tickers = exchange.fetch_tickers(symbols_in_file)
            now_utc = datetime.now(timezone.utc)

            for index, trade in df_live.iterrows():
                symbol = trade.get('symbol')
                ticker_data = tickers.get(symbol) or tickers.get(f"{symbol}:USDT")
                pnl = 0
                # Asegurarse de que el timestamp de entrada es timezone-aware
                entry_time = pd.to_datetime(trade['timestamp_entrada']).tz_convert('UTC')
                duration_hours = (now_utc - entry_time).total_seconds() / 3600
                
                if ticker_data:
                    current_price = ticker_data['last']
                    entry_price = float(trade['precio_entrada'])
                    pnl = ((entry_price - current_price) / entry_price * 100) if trade['tipo'] == 'short' else ((current_price - entry_price) / entry_price * 100)
                
                live_pnl_list.append(pnl)
                live_duration_list.append(duration_hours)

            df_live['pnl_actual_pct'] = live_pnl_list
            df_live['duracion_actual_h'] = live_duration_list

            # --- FASE 2: MOSTRAR RESUMEN ---
            st.subheader("Resumen en Tiempo Real")
            total_pnl = df_live['pnl_actual_pct'].sum(); avg_pnl = df_live['pnl_actual_pct'].mean()
            avg_duracion = df_live['duracion_actual_h'].mean(); ganando = (df_live['pnl_actual_pct'] >= 0).sum()
            perdiendo = len(df_live) - ganando
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("PnL Total", f"{total_pnl:.2f}%"); c2.metric("PnL Promedio", f"{avg_pnl:.2f}%")
            c3.metric("Duración Promedio", f"{avg_duracion:.1f} h"); c4.metric("Ganando / Perdiendo", f"🟢 {ganando} / 🔴 {perdiendo}")

            # --- FASE 3: MOSTRAR DETALLE DE CADA OPERACIÓN ---
            col_header = st.columns((2.5, 2, 2.5, 2, 1))
            fields = ["Símbolo / Info", "PnL / Precio Actual", "Progreso a TP", "Tiempo Transcurrido", "Acción"]
            for col, field_name in zip(col_header, fields): col.markdown(f"**{field_name}**")

            
            for index, trade in df_live.iterrows():
                symbol = trade.get('symbol'); 
                if not symbol: continue
                
                ticker_data = tickers.get(symbol) or tickers.get(f"{symbol}:USDT")
                if ticker_data:
                    current_price = ticker_data['last']; entry_price = float(trade['precio_entrada'])
                    tp = float(trade.get('take_profit')) if trade.get('take_profit') else None
                    sl = float(trade.get('stop_loss')) if trade.get('stop_loss') else None
                    trade_type = trade['tipo']
                    pnl_actual = trade['pnl_actual_pct']; duration_hours = trade['duracion_actual_h']
                    
                    col_data = st.columns((2.5, 2, 2.5, 2, 1))
                    
                    # Columna 1: Info del Símbolo
                    col_data[0].markdown(f"**{symbol}** ({trade_type.upper()})<br><small>Entrada: {entry_price:.4f} | Confianza: {trade['prediccion_ia']}</small>", unsafe_allow_html=True)
                    
                    # Columna 2: PnL y Precio Actual
                    pnl_color = "green" if pnl_actual >= 0 else "red"
                    pnl_html = f"""<div style="line-height: 1.2;"><strong style="font-size: 1.5em; color: {pnl_color};">{pnl_actual:.2f}%</strong><br><small style="color: grey;">Actual: {current_price:.4f}</small></div>"""
                    col_data[1].markdown(pnl_html, unsafe_allow_html=True)
                    
                    # Columna 3: Dossier Interactivo de Progreso
                    progress_pct = 0
                    if tp:
                        total_dist = abs(tp - entry_price)
                        current_dist = abs(current_price - entry_price)
                        if total_dist > 0: progress_pct = current_dist / total_dist

                    with col_data[2].expander(f"Progreso a TP: {progress_pct*100:.0f}%", expanded=False):
                        if tp: st.text(f"Recorrido: {current_dist:.4f} de {total_dist:.4f}")
                        st.progress(max(0, min(1, progress_pct)))
                        try:
                            ohlcv_chart = exchange.fetch_ohlcv(symbol, '15m', limit=100)
                            df_chart = pd.DataFrame(ohlcv_chart, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                            df_chart['timestamp'] = pd.to_datetime(df_chart['timestamp'], unit='ms')
                            fig = px.line(df_chart, x='timestamp', y='close', title=f"Evolución (15m)")
                            fig.add_hline(y=entry_price, line_dash="dot", annotation_text="Entrada", line_color="grey")
                            if tp: fig.add_hline(y=tp, line_dash="solid", annotation_text="TP", line_color="green")
                            if sl: fig.add_hline(y=sl, line_dash="solid", annotation_text="SL", line_color="red")
                            fig.update_layout(height=250, margin=dict(t=30, b=10, l=10, r=10), yaxis_title=None, xaxis_title=None)
                            st.plotly_chart(fig, use_container_width=True)
                        except Exception as chart_e:
                            st.warning(f"No se pudo generar el gráfico: {chart_e}")

                    # Columna 4: Tiempo de progreso
                    col_data[3].markdown(f"{duration_hours:.1f}h / {PROYECCION_CIERRE_H:.1f}h máx.")

                    # 🔥 COLUMNA 5: BOTÓN DE CIERRE MANUAL 🔥
                    # Solo mostramos el botón para las operaciones aceptadas (reales), no las virtuales.
                    if not is_virtual:
                        col_data[4].button("Cerrar", key=f"close_{trade['id']}", on_click=cerrar_operacion_manual, args=(trade['id'], symbol))
                        
        except Exception as e:
            st.error(f"Ocurrió un error al obtener precios en vivo: {e}")
            st.dataframe(df_live)

    elif df_live.empty:
        st.success(f"No hay operaciones {'virtuales' if is_virtual else 'reales'} en curso.")
    else:
        st.error("No se pudo conectar a Binance.")

# --- CARGA Y FILTRADO DE DATOS ---
alerts_df = pd.DataFrame(operations_manager.load_data("alertas.json"))
abiertas_df = load_data("abiertas.json")
cerradas_df = load_data("cerradas.json")

# Filtramos las operaciones "abiertas" en sus dos categorías
aceptadas_df = abiertas_df[abiertas_df['estado'] == 'aceptada'].copy()
rechazadas_df = abiertas_df[abiertas_df['estado'] == 'rechazada'].copy()
cerradas_df_processed = process_closed_trades(cerradas_df.copy())

# --- TÍTULO Y ADVERTENCIA GLOBAL ---
st.title("📊 Centro de Comando de Trading")
if not alerts_df.empty:
    st.warning(f"⚠️ ¡Atención! Tienes {len(alerts_df)} señales nuevas que requieren tu decisión en la pestaña 'Alertas'.", icon="🚨")
st.markdown("---")

# --- PESTAÑAS PRINCIPALES ---
tab_alertas, tab_aceptadas, tab_rechazadas, tab_cerradas, tab_hunter = st.tabs([
    f"🚨 Alertas ({len(alerts_df)})", 
    f"🟢 Aceptadas ({len(aceptadas_df)})",
    f"⚪️ Rechazadas ({len(rechazadas_df)})",
    f"🔴 Historial ({len(cerradas_df)})",
    "🎯 Cazador de Shorts" # Nueva Pestaña
])



#Pestaña de Alertas
with tab_alertas:
    st.header("Señales Pendientes de Decisión")
    st.caption("Revisa las mejores señales de cada ciclo y decide si las aceptas, las rechazas o las anulas.")
    st.markdown("---")

    if not alerts_df.empty:
        # Funciones callback para los botones
        def accept_signal(alert_id):
            operations_manager.accept_alert(alert_id)

        def reject_signal(alert_id):
            operations_manager.reject_alert(alert_id)
            
        def void_signal(alert_id):
            operations_manager.void_alert(alert_id)

        for index, alert in alerts_df.iterrows():
            # 🔥 CORRECCIÓN: Añadimos una columna más
            col1, col2, col3, col4, col5, col6, col7 = st.columns([3, 1.5, 1.5, 1.5, 1, 1, 1])
            
            tipo = alert.get('tipo', 'N/A').upper()
            color = "red" if tipo == "SHORT" else "green"
            
            col1.markdown(f"**{alert['symbol']}**<br><span style='color:{color};'>{tipo}</span>", unsafe_allow_html=True)
            col2.metric("Precio Señal", f"{alert.get('precio_entrada', 0):.4f}")
            col3.metric("Confianza IA", f"{alert.get('probabilidad_ia', 0)*100:.2f}%")
            col4.metric("Apuesta Sugerida", f"${alert.get('apuesta_sugerida', 0)}")
            
            # Botones de Acción
            col5.button("Aceptar 👍", key=f"accept_{alert['id']}", on_click=accept_signal, args=(alert['id'],))
            col6.button("Rechazar 👎", key=f"reject_{alert['id']}", on_click=reject_signal, args=(alert['id'],))
            
            # 🔥 NUEVO BOTÓN DE ANULAR 🔥
            col7.button("Anular ❌", key=f"void_{alert['id']}", on_click=void_signal, args=(alert['id'],))

            st.markdown("---")
    else:
        st.info("No hay nuevas alertas en este momento.")

# --- PESTAÑAS DE OPERACIONES EN CURSO ---
with tab_aceptadas:
    display_live_trades_section(aceptadas_df, f"Monitor de Operaciones Aceptadas ({len(aceptadas_df)})", is_virtual=False)

with tab_rechazadas:
    display_live_trades_section(rechazadas_df, f"Monitor de Operaciones Rechazadas ({len(rechazadas_df)})", is_virtual=True)

# --- 🔥 PESTAÑA DE HISTORIAL Y MÉTRICAS (REDiseñada) 🔥 ---
with tab_cerradas:
    st.header("📈 Análisis de Rendimiento Histórico")

 # 🔥 AHORA SOLO HAY UN FILTRO
    estado_filter = st.radio(
        "Filtrar por Decisión:",
        ('Todas', 'Solo Aceptadas (Real)', 'Solo Rechazadas (Virtual)'),
        horizontal=True, key="estado_filter"
    )

    st.markdown("---") # Una línea para separar visualmente

    if not cerradas_df_processed.empty:
        df_to_analyze = cerradas_df_processed
        if estado_filter == 'Solo Aceptadas (Real)':
            df_to_analyze = cerradas_df_processed[cerradas_df_processed['estado'] == 'aceptada']
        elif estado_filter == 'Solo Rechazadas (Virtual)':
            df_to_analyze = cerradas_df_processed[cerradas_df_processed['estado'] == 'rechazada']

        
        # --- A partir de aquí, todo el código usa 'df_to_analyze' ---
        if df_to_analyze.empty:
            st.info(f"No hay operaciones en la categoría seleccionada.")
        else:
            # --- KPIs ---
            st.subheader("Signos Vitales de la Estrategia")
            total_trades = len(df_to_analyze)
            win_rate = (df_to_analyze['resultado'] == 'Ganadora').mean() * 100
            ganancias_df = df_to_analyze[df_to_analyze['resultado_pct'] > 0]
            perdidas_df = df_to_analyze[df_to_analyze['resultado_pct'] <= 0]
            avg_win = ganancias_df['resultado_pct'].mean() if not ganancias_df.empty else 0
            avg_loss = perdidas_df['resultado_pct'].mean() if not perdidas_df.empty else 0
            profit_factor = ganancias_df['resultado_pct'].sum() / abs(perdidas_df['resultado_pct'].sum()) if not perdidas_df.empty and perdidas_df['resultado_pct'].sum() != 0 else float('inf')

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Operaciones Totales", f"{total_trades}")
            col2.metric("Tasa de Acierto (Win Rate)", f"{win_rate:.2f}%")
            col3.metric("Profit Factor", f"{profit_factor:.2f}")
            col4.metric("Ganancia Promedio vs. Pérdida Promedio", f"{avg_win:.2f}% / {avg_loss:.2f}%")

        # --- 2. LA CURVA DE CAPITAL (LA LÍNEA DE FONDO) ---
        st.subheader("Curva de Capital (PnL Acumulado)")
        st.plotly_chart(px.line(cerradas_df_processed, x='timestamp_cierre', y='pnl_acumulado', title="Evolución de la Rentabilidad Neta"), use_container_width=True)
        st.markdown("---")

        # --- 3. ANÁLISIS PROFUNDO POR CATEGORÍAS ---
        st.header("🔬 Desglose del Rendimiento")
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            # --- ANÁLISIS LONG vs. SHORT ---
            st.subheader("Rendimiento por Dirección (Long vs. Short)")
            resumen_tipo = cerradas_df_processed.groupby('tipo')['resultado_pct'].agg(['mean', 'count', 'sum']).reset_index()
            fig_tipo = px.bar(resumen_tipo, x='tipo', y='mean', color='tipo', 
                              title="Rentabilidad Promedio por Tipo de Operación",
                              labels={'tipo': 'Tipo de Operación', 'mean': 'PnL Promedio (%)'},
                              color_discrete_map={'long': 'green', 'short': 'red'}, text_auto='.2f')
            st.plotly_chart(fig_tipo, use_container_width=True)

            # --- ANÁLISIS POR MOTIVO DE CIERRE ---
            st.subheader("Rendimiento por Motivo de Cierre")
            if 'motivo' in cerradas_df_processed.columns:
                resumen_motivos = cerradas_df_processed.groupby('motivo', observed=False)['resultado_pct'].agg(['mean', 'count']).reset_index()
                st.plotly_chart(px.bar(resumen_motivos, x='motivo', y='mean', color='motivo', title="PnL Promedio por Motivo", text_auto='.2f'), use_container_width=True)

        with col_g2:
            # --- ANÁLISIS POR CRIPTOMONEDA ---
            st.subheader("Rendimiento por Criptomoneda")
            resumen_symbol = cerradas_df_processed.groupby('symbol')['resultado_pct'].agg(['sum', 'count']).reset_index()
            fig_symbol = px.bar(resumen_symbol.sort_values(by='sum', ascending=False), x='symbol', y='sum',
                                title="Rentabilidad Total por Símbolo",
                                labels={'symbol': 'Criptomoneda', 'sum': 'PnL Total (%)'})
            st.plotly_chart(fig_symbol, use_container_width=True)

            # --- ANÁLISIS DE CONFIANZA DE LA IA (MEJORADO) ---
            st.subheader("Rendimiento por Confianza de la IA")
            if 'confianza_ia' in cerradas_df_processed.columns:
                # Nuevos rangos más granulares para altas confianzas
                bins = [0, 85, 95, 98, 101]
                labels = ['Buena (0-85%)', 'Alta (85-95%)', 'Muy Alta (95-98%)', 'Élite (>98%)']
                cerradas_df_processed['grupo_confianza'] = pd.cut(cerradas_df_processed['confianza_ia'], bins=bins, labels=labels, right=False)
                resumen_ia = cerradas_df_processed.groupby('grupo_confianza', observed=False)['resultado_pct'].agg(['mean', 'count']).reset_index()
                st.plotly_chart(px.bar(resumen_ia, x='grupo_confianza', y='mean', color='grupo_confianza', title="PnL Promedio por Nivel de Confianza"), use_container_width=True)
        
        st.markdown("---")
        st.header("📋 Historial Detallado de Operaciones Cerradas")
        st.dataframe(cerradas_df, use_container_width=True) # Mostramos el original sin procesar
    else:
        st.info("Aún no hay operaciones cerradas para analizar.")

with tab_hunter:
    st.header("🎯 Cazador de Shorts (Anti-FOMO)")
    st.markdown("Genera un reporte en tiempo real de las oportunidades de venta en el mercado.")

    if 'hunter_report' not in st.session_state:
        st.session_state.hunter_report = pd.DataFrame()

    if st.button("Generar Reporte en Pantalla 🚀"):
        with st.spinner("Analizando el mercado... Esto puede tardar 1-2 minutos."):
            # Llamamos a la función de tu script para obtener el reporte
            st.session_state.hunter_report = report_generator.generate_report()
        
        if st.session_state.hunter_report.empty:
            st.warning("No se encontraron candidatos con datos suficientes en este momento.")
        else:
            st.success("¡Reporte generado con éxito!")
    
    st.markdown("---")

    if not st.session_state.hunter_report.empty:
        report_df = st.session_state.hunter_report
        st.info(f"Mostrando reporte de {len(report_df)} candidatos.")
        
        # Botón de Descarga
        excel_data = to_excel(report_df)
        st.download_button(
            label="📥 Descargar Reporte en Excel",
            data=excel_data,
            file_name="reporte_cazador_shorts.xlsx"
        )
        
        # Formatear para mejor visualización
        df_display = report_df.copy()
        df_display.sort_values(by='Confianza IA (%)', ascending=False, inplace=True)
        
        format_dict = {
            'Confianza IA (%)': '{:.2f}%',
            'Var 24h (%)': '{:.2f}%',
            'Var 1h (%)': '{:.2f}%',
            'Dist. Media (%)': '{:.2f}%',
            'RSI 4H': '{:.2f}',
            'RSI 1D': '{:.2f}',
            'Vol Spike 5m': '{:.2f}'
        }
        for col, fmt in format_dict.items():
            if col in df_display.columns:
                df_display[col] = df_display[col].map(fmt.format)

        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("Haz clic en el botón de arriba para generar tu primer reporte.")