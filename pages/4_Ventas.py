import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from conexion import load_data, get_gspread_client, SHEET_ID, MAIN_WORKSHEET_NAME

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(layout="wide", page_title="Gestión de Ventas SmartFarm", page_icon="💰")

SALES_WORKSHEET_NAME = "Ventas SmartFarm"
TIPO_VENTA_OPTIONS = ["Componente", "Licencia", "Servicio"]
ESTADO_VENTA_OPTIONS = ["Posible", "Cerrado", "Perdido"]

# --- MAPEO DE COLUMNAS REALES (Según tu Google Sheets) ---
COL_FECHA = "FECHA DE REGISTRO"
COL_ID = "ID CLIENTE"
COL_CLIENTE = "CLIENTE"
COL_TIPO = "TIPO DE VENTA"
COL_ESTADO = "ESTADO DE LA VENTA"
COL_MONTO = "MONTO"
COL_DETALLE = "DETALLE DE LA OPORTUNIDAD/VENTA"


def normalizar_df(df):
    """Limpia encabezados: quita espacios y pasa a MAYÚSCULAS."""
    if df is not None and not df.empty:
        df.columns = [str(c).strip().upper() for c in df.columns]
        if COL_MONTO in df.columns:
            df[COL_MONTO] = pd.to_numeric(df[COL_MONTO], errors='coerce').fillna(0.0)
    return df


st.title("💰 Gestión de Oportunidades y Ventas SmartFarm")

# Carga de datos
main_df = normalizar_df(load_data(MAIN_WORKSHEET_NAME))
sales_df = normalizar_df(load_data(SALES_WORKSHEET_NAME))

tab_reg, tab_manage, tab_analysis = st.tabs(["➕ Registrar Venta", "✏️ Gestionar Estados", "📊 Análisis"])

# --- TAB 1: REGISTRO ---
with tab_reg:
    if not main_df.empty:
        main_df['SELECTOR'] = main_df['ID CLIENTE'].astype(str) + " - " + main_df['CLIENTE'].astype(str)
        client_options = ["Selecciona un cliente"] + main_df['SELECTOR'].unique().tolist()

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
                    partes = cliente_sel.split(" - ")
                    # Fila ordenada: Fecha, ID, Cliente, Tipo, Estado, Monto, Detalle
                    nueva_fila = [
                        datetime.now().strftime("%d/%m/%Y"),
                        partes[0], partes[1], tipo, estado, monto, detalle
                    ]
                    try:
                        client = get_gspread_client()
                        ws = client.open_by_key(SHEET_ID).worksheet(SALES_WORKSHEET_NAME)
                        ws.append_row(nueva_fila)
                        st.success("¡Venta registrada con éxito!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

# --- TAB 2: GESTIONAR ESTADOS (EDICIÓN) ---
with tab_manage:
    if not sales_df.empty:
        # Selector para identificar la venta
        sales_df['SELECTOR_EDIT'] = sales_df[COL_CLIENTE].astype(str) + " | " + \
                                    sales_df[COL_TIPO].astype(str) + " | $" + \
                                    sales_df[COL_MONTO].astype(str)

        venta_sel = st.selectbox("Seleccione la venta para actualizar:", [""] + sales_df['SELECTOR_EDIT'].tolist())

        if venta_sel:
            idx = sales_df[sales_df['SELECTOR_EDIT'] == venta_sel].index[0]
            row = sales_df.iloc[idx]

            with st.form("form_edit_venta"):
                st.info(f"Actualizando oportunidad de: **{row[COL_CLIENTE]}**")
                c1, c2, c3 = st.columns(3)

                # Estado actual (normalizado para el buscador)
                est_actual = str(row[COL_ESTADO]).capitalize()
                nuevo_estado = c1.selectbox("Nuevo Estado:", ESTADO_VENTA_OPTIONS,
                                            index=ESTADO_VENTA_OPTIONS.index(
                                                est_actual) if est_actual in ESTADO_VENTA_OPTIONS else 0)

                nuevo_monto = c2.number_input("Monto Actualizado (USD):", value=float(row[COL_MONTO]))

                tipo_actual = str(row[COL_TIPO]).capitalize()
                nuevo_tipo = c3.selectbox("Tipo de Venta:", TIPO_VENTA_OPTIONS,
                                          index=TIPO_VENTA_OPTIONS.index(
                                              tipo_actual) if tipo_actual in TIPO_VENTA_OPTIONS else 0)

                nuevo_detalle = st.text_area("Detalle actualizado:", value=row.get(COL_DETALLE, ""))

                if st.form_submit_button("Guardar Cambios"):
                    try:
                        client = get_gspread_client()
                        ws = client.open_by_key(SHEET_ID).worksheet(SALES_WORKSHEET_NAME)
                        row_num = int(idx) + 2

                        # Actualización de celdas (D=4, E=5, F=6, G=7)
                        ws.update_cell(row_num, 4, nuevo_tipo)
                        ws.update_cell(row_num, 5, nuevo_estado)
                        ws.update_cell(row_num, 6, nuevo_monto)
                        ws.update_cell(row_num, 7, nuevo_detalle)

                        st.success("¡Venta actualizada!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al conectar con Google Sheets: {e}")
    else:
        st.info("No hay ventas registradas para gestionar.")

# --- TAB 3: ANÁLISIS ---
with tab_analysis:
    if not sales_df.empty:
        # Cálculos Robustos (Insensibles a mayúsculas en el contenido)
        total_pipeline = sales_df[COL_MONTO].sum()

        # Filtro de ganadas comparando en mayúsculas
        ganadas_df = sales_df[sales_df[COL_ESTADO].astype(str).str.upper() == 'CERRADO']
        monto_ganado = ganadas_df[COL_MONTO].sum()

        tasa_conversion = (len(ganadas_df) / len(sales_df)) * 100 if len(sales_df) > 0 else 0

        # KPIs
        k1, k2, k3 = st.columns(3)
        k1.metric("Pipeline Total", f"USD {total_pipeline:,.0f}")
        k2.metric("Ventas Cerradas", f"USD {monto_ganado:,.0f}")
        k3.metric("Efectividad Cierre", f"{tasa_conversion:.1f}%")

        st.divider()

        # Gráficos
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            # Normalizamos temporalmente para el gráfico para que el color_map coincida
            plot_df = sales_df.copy()
            plot_df[COL_ESTADO] = plot_df[COL_ESTADO].astype(str).str.upper()

            fig_pie = px.pie(
                plot_df, names=COL_ESTADO, values=COL_MONTO,
                title="Montos por Estado de Venta",
                color=COL_ESTADO,
                color_discrete_map={'CERRADO': '#28a745', 'POSIBLE': '#ffc107', 'PERDIDO': '#dc3545'}
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_g2:
            fig_bar = px.bar(
                sales_df, x=COL_TIPO, y=COL_MONTO, color=COL_ESTADO,
                title="Oportunidades por Tipo", barmode='group'
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("📋 Listado Detallado")
        st.dataframe(sales_df, use_container_width=True, hide_index=True)
    else:
        st.info("No hay datos de ventas para analizar.")
