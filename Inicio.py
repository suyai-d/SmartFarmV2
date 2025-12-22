import streamlit as st
import pandas as pd
import plotly.express as px
from conexion import load_data, MAIN_WORKSHEET_NAME, COL_PUNTAJE

# 1. Configuración de página (Debe ser lo primero)
st.set_page_config(
    page_title="SmartFarm - Conci",
    layout="wide",
    page_icon="sf1.png",
    initial_sidebar_state="collapsed",
)

# 2. Carga de datos centralizada
df = load_data(MAIN_WORKSHEET_NAME)

# --- Encabezado Principal ---
col_text, col_img = st.columns([3, 1])

with col_text:
    st.title("🚜 Bienvenidos al Desafío SmartFarm")
    st.markdown("""
    Esta plataforma permite gestionar de manera integral el ecosistema digital de nuestros clientes, 
    midiendo su nivel de adopción tecnológica y detectando oportunidades de mejora.
    """)

with col_img:
    try:
        st.image("sf1.png", width=150)
    except:
        st.write("📷 **SmartFarm Logo**")

st.divider()

# 3. Resumen Ejecutivo (KPIs)
if not df.empty:
    # Procesamiento rápido de datos para el Inicio
    target_col = COL_PUNTAJE.upper()
    df[target_col] = pd.to_numeric(df[target_col], errors='coerce').fillna(0)

    # Métricas clave
    total_clientes = len(df)
    puntaje_promedio = df[target_col].mean()
    top_cliente = df.loc[df[target_col].idxmax(), 'CLIENTE']

    m1, m2, m3 = st.columns(3)
    m1.metric("Clientes Evaluados", f"{total_clientes}")
    m2.metric("Promedio General", f"{puntaje_promedio:.1f} pts")
    m3.metric("Líder Actual", top_cliente)

    st.divider()

    # Gráfico rápido de distribución
    st.subheader("📊 Estado Actual del Desafío")
    fig = px.histogram(
        df,
        x=target_col,
        nbins=10,
        title="Distribución de Puntajes (Nivel de Adopción)",
        color_discrete_sequence=['#28a745'],
        labels={target_col: "Puntaje"}
    )
    st.plotly_chart(fig, use_container_width=True)

    # Instrucciones de navegación
    st.info("""
    **Guía de Navegación:**
    * **Cliente SmartFarm:** Registra nuevos clientes o edita sus puntajes.
    * **Reporte Cliente:** Genera un análisis visual detallado (Gráfico Radar) para un cliente específico.
    * **Proyectos Agronomy Analyzer:** Seguimiento de implementaciones y proyectos Analyzer.
    * **Ventas:** Gestión de oportunidades comerciales detectadas.
    """)

else:
    st.warning(
        "⚠️ No se encontraron datos en la hoja principal. Comience registrando un cliente en la pestaña lateral.")

    # Botón de acceso rápido si está vacío
    if st.button("Ir a Registro de Clientes"):
        st.switch_page("pages/1_Cliente_SmartFarm.py")

st.link_button("📂 Acceder a Carpeta de SmartFarm (Drive)", "https://drive.google.com/drive/folders/1YhZgrnVi4xSrIeV8kK0klSEyG-nzxDxr?usp=sharing")

st.markdown("<br><footer style='text-align: center; color: gray;'>SmartFarm Dashboard © 2026 - Conci</footer>",
            unsafe_allow_html=True)

