# --- PRIMERO, LE DAMOS EL "MAPA" ---
import sys
import os
# Añadir la carpeta raíz del proyecto a la ruta de búsqueda de Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# --- FIN DEL MAPA ---


# --- AHORA, PUEDE CONTACTAR A trade_manager Y A LOS DEMÁS ---
import streamlit as st
import pandas as pd
import plotly.express as px
import ccxt
from datetime import datetime, timezone
import trade_manager
import data_manager

# Mantenemos una conexión a ccxt para los precios en vivo
@st.cache_resource
def init_exchange():
    try:
        return ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    except Exception as e:
        st.sidebar.error(f"Error conectando a Binance: {e}")
        return None
exchange = init_exchange()

# REEMPLAZA LA FUNCIÓN display_alerts_tab ENTERA EN ui_components.py

def display_alerts_tab(df_alertas):
    """Muestra la pestaña de Alertas con detalles y botones de acción."""
    st.header("🚨 Alertas Pendientes de Decisión")
    st.caption("Revisa las señales detectadas por el bot y toma una decisión.")

    if df_alertas.empty:
        st.info("No hay nuevas alertas en este momento.")
        return

    # --- FUNCIONES CALLBACK PARA LOS BOTONES ---
    # (Definidas aquí para tener acceso a st.rerun)
    def accept_signal_callback(alert_id, symbol):
        try:
            # Obtenemos el precio actual al momento de aceptar
            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            data_manager.accept_alert(alert_id, current_price)
            st.rerun()
        except Exception as e:
            st.error(f"Error al aceptar {symbol}: {e}")

    def reject_signal_callback(alert_id):
        data_manager.reject_alert(alert_id)
        st.rerun()

    for index, alerta in df_alertas.iterrows():
        st.markdown("---")
        strategy = alerta.get('strategy', 'Desconocida')
        direction = alerta.get('direction', 'N/A').upper()
        symbol = alerta['symbol']
        alert_id = alerta['id']
        details = alerta.get('details', {})

        direction_color = "green" if "ALCISTA" in direction else "red"

        col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])

        with col1:
            st.markdown(f"**{symbol}**<br><small>Estrategia: {strategy}</small>", unsafe_allow_html=True)
            st.markdown(f"<span style='color:{direction_color};'>{direction}</span>", unsafe_allow_html=True)

        with col2:
            if "score" in details:
                st.metric("Score Clímax", f"{details.get('score', 0):.2f}")

        with col3:
            if "acel_15m_pct" in details:
                st.metric("Aceleración 15m", f"{details.get('acel_15m_pct', 0):.2f}%")

        # Botones de Acción
        with col4:
            st.button("Aceptar 👍", key=f"accept_{alert_id}", on_click=accept_signal_callback, args=(alert_id, symbol))

        with col5:
            st.button("Rechazar 👎", key=f"reject_{alert_id}", on_click=reject_signal_callback, args=(alert_id,))

def display_open_tab(df_abiertas):
    """
    Muestra la pestaña de Operaciones Abiertas con la interfaz gráfica completa,
    precios en vivo y el botón para cerrar.
    """
    st.header("🟢 Monitor de Operaciones Abiertas")

    if df_abiertas.empty:
        st.info("No hay operaciones abiertas actualmente.")
        return
    if not exchange:
        st.error("No se pudo conectar a Binance para obtener precios en vivo.")
        st.dataframe(df_abiertas)
        return

    # --- FUNCIÓN CALLBACK PARA EL BOTÓN ---
    def cerrar_operacion_callback(trade_id, symbol):
        """Obtiene el precio actual y cierra el trade usando el trade_manager."""
        try:
            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            if trade_manager.close_trade_by_id(trade_id, current_price, "Cierre Manual desde Dashboard"):
                st.success(f"¡Operación {symbol} cerrada exitosamente al precio {current_price}!")
            else:
                st.error(f"No se pudo cerrar la operación {symbol}.")
        except Exception as e:
            st.error(f"Error al obtener el precio para {symbol}: {e}")

    try:
        symbols_in_file = df_abiertas['symbol'].unique().tolist()
        tickers = exchange.fetch_tickers(symbols_in_file)
        now_utc = datetime.now(timezone.utc)

        # Encabezados de la tabla
        col_header = st.columns((2.5, 2, 2.5, 2, 1))
        fields = ["Símbolo / Info", "PnL / Precio Actual", "Gráfico (15m)", "Tiempo Transcurrido", "Acción"]
        for col, field_name in zip(col_header, fields):
            col.markdown(f"**{field_name}**")

        for index, trade in df_abiertas.iterrows():
            st.markdown("---")
            symbol = trade.get('symbol')
            if not symbol: continue

            ticker_data = tickers.get(symbol) or tickers.get(f"{symbol}:USDT")
            if not ticker_data:
                st.warning(f"No se pudo obtener el precio en vivo para {symbol}.")
                continue

            current_price = ticker_data['last']
            entry_price = float(trade['precio_entrada'])
            direction = trade.get('direction') or trade.get('tipo', 'LONG').upper()
            pnl_actual = ((current_price - entry_price) / entry_price * 100) if direction == 'LONG' else ((entry_price - current_price) / entry_price * 100)

            entry_time = pd.to_datetime(trade.get('entry_time') or trade.get('timestamp_entrada')).tz_convert('UTC')
            duration_hours = (now_utc - entry_time).total_seconds() / 3600

            # --- Visualización detallada ---
            col1, col2, col3, col4, col5 = st.columns((2.5, 2, 2.5, 2, 1))

            # Columna 1: Info
            col1.markdown(f"**{symbol}** ({direction})<br><small>Entrada: {entry_price:.4f}</small>", unsafe_allow_html=True)

            # Columna 2: PnL
            pnl_color = "green" if pnl_actual >= 0 else "red"
            col2.markdown(f"""<div style="line-height: 1.2;"><strong style="font-size: 1.5em; color: {pnl_color};">{pnl_actual:.2f}%</strong><br><small style="color: grey;">Actual: {current_price:.4f}</small></div>""", unsafe_allow_html=True)

            # Columna 3: Gráfico
            with col3.expander("Ver gráfico", expanded=False):
                ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
                df_chart = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df_chart['timestamp'] = pd.to_datetime(df_chart['timestamp'], unit='ms')
                fig = px.line(df_chart, x='timestamp', y='close', title=f"Evolución de {symbol}")
                fig.add_hline(y=entry_price, line_dash="dot", annotation_text="Entrada", line_color="grey")
                fig.update_layout(height=200, margin=dict(t=30, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True)

            # Columna 4: Duración
            col4.metric("Duración", f"{duration_hours:.1f} horas")

            # Columna 5: BOTÓN DE CIERRE
            col5.button("Cerrar", key=f"close_{trade['id']}", on_click=cerrar_operacion_callback, args=(trade['id'], symbol))

    except Exception as e:
        st.error(f"Ocurrió un error al obtener precios en vivo: {e}")

def display_closed_tab(df_cerradas):
    """Muestra la pestaña de Historial con todos los gráficos."""
    st.header("📈 Análisis de Rendimiento Histórico")
    if df_cerradas.empty:
        st.info("Aún no hay operaciones cerradas para analizar.")
        return

    st.subheader("Signos Vitales")
    total_trades = len(df_cerradas)
    win_rate = (df_cerradas['resultado'] == 'Ganadora').mean() * 100

    col1, col2 = st.columns(2)
    col1.metric("Operaciones Totales", f"{total_trades}")
    col2.metric("Tasa de Acierto (Win Rate)", f"{win_rate:.2f}%")

    st.subheader("Curva de Capital")
    fig_pnl = px.line(df_cerradas, x='timestamp_cierre', y='pnl_acumulado', title="Evolución de la Rentabilidad Neta")
    st.plotly_chart(fig_pnl, use_container_width=True)

    st.subheader("📋 Historial Detallado")
    st.dataframe(df_cerradas, use_container_width=True)