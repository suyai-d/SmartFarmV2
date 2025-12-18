import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from conexion import load_data, get_gspread_client, SHEET_ID, MAIN_WORKSHEET_NAME

# -----------------------------------------------------------
# CONFIGURACIÓN INICIAL
# -----------------------------------------------------------
st.set_page_config(layout="wide", page_title="Gestión de Ventas SmartFarm", page_icon="💰")

# Nombre de la hoja en tu Google Sheet
SALES_WORKSHEET_NAME = "Ventas SmartFarm"
TIPO_VENTA_OPTIONS = ["Componente", "Licencia", "Servicio"]
ESTADO_VENTA_OPTIONS = ["Posible", "Cerrado", "Perdido"]


# -----------------------------------------------------------
# FUNCIONES DE DATOS ESPECÍFICAS
# -----------------------------------------------------------

@st.cache_data(ttl=60)
def get_sales_data_ui():
    """Carga datos de ventas normalizando columnas a MAYÚSCULAS y GUIONES_BAJOS."""
    df = load_data(SALES_WORKSHEET_NAME)
    if not df.empty:
        # Normalización estricta: Espacios por guiones y todo a Mayúsculas
        df.columns = [str(c).replace(" ", "_").strip().upper() for c in df.columns]

        # Asegurar que MONTO sea numérico para cálculos
        if 'MONTO' in df.columns:
            df['MONTO'] = pd.to_numeric(df['MONTO'], errors='coerce').fillna(0.0)

        # Índice para futuras ediciones
        df['__ROW_INDEX'] = df.index + 2
    return df


def save_new_sale(sale_data):
    """Guarda una nueva fila en la hoja de ventas."""
    try:
        client = get_gspread_client()
        worksheet = client.open_by_key(SHEET_ID).worksheet(SALES_WORKSHEET_NAME)
        worksheet.append_row(list(sale_data.values()))
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False


# -----------------------------------------------------------
# INTERFAZ DE USUARIO
# -----------------------------------------------------------

st.title("💰 Gestión de Oportunidades y Ventas SmartFarm")

# Cargamos datos de ambas hojas
main_df = load_data(MAIN_WORKSHEET_NAME)
sales_df = get_sales_data_ui()

if main_df.empty:
    st.warning("⚠️ No se encontraron datos en la Hoja Principal.")
    st.stop()

# Preparar opciones de clientes (Usando nombres normalizados de conexion.py)
main_df['SELECTOR'] = main_df['ID CLIENTE'].astype(str) + " - " + main_df['CLIENTE'].astype(str)
client_options = ["Selecciona un cliente"] + main_df['SELECTOR'].unique().tolist()

tab_reg, tab_manage, tab_analysis = st.tabs(["➕ Registrar Venta", "✏️ Gestionar Estados", "📊 Análisis"])

# --- TAB 1: REGISTRO ---
with tab_reg:
    with st.form("reg_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        cliente_sel = col1.selectbox("Cliente:", client_options)
        tipo = col2.selectbox("Tipo de Venta:", TIPO_VENTA_OPTIONS)

        col3, col4 = st.columns(2)
        monto = col3.number_input("Monto Estimado (USD):", min_value=0.0, step=100.0)
        estado = col4.selectbox("Estado:", ESTADO_VENTA_OPTIONS)

        detalle = st.text_area("Detalle de la oportunidad:")

        if st.form_submit_button("Registrar en Embudo"):
            if cliente_sel == "Selecciona un cliente":
                st.error("Por favor selecciona un cliente.")
            else:
                # Separamos el ID y el Nombre
                partes = cliente_sel.split(" - ")
                id_c = partes[0]
                nom_c = partes[1]

                nueva_data = {
                    "Fecha": datetime.now().strftime("%Y-%m-%d"),
                    "ID Cliente": id_c,
                    "Cliente": nom_c,
                    "Tipo": tipo,
                    "Estado": estado,
                    "Monto": monto,
                    "Detalle": detalle
                }
                if save_new_sale(nueva_data):
                    st.success("¡Venta registrada con éxito!")
                    st.rerun()

# --- TAB 3: ANÁLISIS ---
with tab_analysis:
    if not sales_df.empty:
        # Detectar nombres de columnas de forma flexible por si cambian en el Excel
        col_estado = 'ESTADO' if 'ESTADO' in sales_df.columns else 'ESTADO_DE_LA_VENTA'
        col_tipo = 'TIPO' if 'TIPO' in sales_df.columns else 'TIPO_DE_VENTA'

        # KPIs Principales
        total_pipeline = sales_df['MONTO'].sum()

        # Filtro para ventas ganadas (insensible a mayúsculas en el contenido)
        cerrado_df = sales_df[sales_df[col_estado].astype(str).str.upper() == 'CERRADO']
        monto_cerrado = cerrado_df['MONTO'].sum()

        tasa_conversion = (len(cerrado_df) / len(sales_df)) * 100 if len(sales_df) > 0 else 0

        k1, k2, k3 = st.columns(3)
        k1.metric("Pipeline Total", f"USD {total_pipeline:,.0f}")
        k2.metric("Ventas Cerradas", f"USD {monto_cerrado:,.0f}")
        k3.metric("Efectividad", f"{tasa_conversion:.1f}%")

        st.divider()

        # Gráficos

        c_g1, c_g2 = st.columns(2)

        with c_g1:
            fig_pie = px.pie(
                sales_df,
                names=col_estado,
                values='MONTO',
                title="Distribución de Montos por Estado",
                color=col_estado,
                color_discrete_map={'CERRADO': '#28a745', 'POSIBLE': '#ffc107', 'PERDIDO': '#dc3545'}
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with c_g2:
            fig_bar = px.bar(
                sales_df,
                x=col_tipo,
                y='MONTO',
                color=col_estado,
                title="Oportunidades por Tipo de Venta",
                barmode='group'
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("📋 Listado Detallado de Oportunidades")
        # Mostramos la tabla sin la columna técnica de índice
        cols_to_show = [c for c in sales_df.columns if c != '__ROW_INDEX']
        st.dataframe(sales_df[cols_to_show], use_container_width=True)

    else:
        st.info("No hay datos de ventas registrados para mostrar en el análisis.")
