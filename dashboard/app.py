# /dashboard/app.py

import streamlit as st

st.set_page_config(page_title="Dashboard de Estrategias", layout="wide")

from data_manager import load_data, process_closed_trades
from ui_components import display_alerts_tab, display_open_tab, display_closed_tab



# --- CARGA DE DATOS ---
alertas_df = load_data('alertas.json')
abiertas_df = load_data('abiertas.json')
cerradas_df_raw = load_data('cerradas.json')
cerradas_df_processed = process_closed_trades(cerradas_df_raw.copy()) # Usar .copy() por seguridad

st.title("📊 Centro de Comando de Trading")
if not alertas_df.empty:
    st.warning(f"⚠️ ¡Atención! Tienes {len(alertas_df)} señales nuevas.", icon="🚨")
st.markdown("---")

# --- PESTAÑAS ---
tab_alertas, tab_abiertas, tab_cerradas = st.tabs([
    f"🚨 Alertas ({len(alertas_df)})", 
    f"🟢 Abiertas ({len(abiertas_df)})",
    f"🔴 Historial ({len(cerradas_df_processed)})"
])

with tab_alertas:
    display_alerts_tab(alertas_df)

with tab_abiertas:
    display_open_tab(abiertas_df)

with tab_cerradas:
    display_closed_tab(cerradas_df_processed)