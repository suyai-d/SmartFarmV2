import streamlit as st
import gspread
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from conexion import load_data, SHEET_ID, MAIN_WORKSHEET_NAME, COL_PUNTAJE

# -----------------------------------------------------------
# CONFIGURACIÓN INICIAL
# -----------------------------------------------------------
st.set_page_config(layout="wide", page_title="Gestión de Ventas SmartFarm")

# **IMPORTANTE:** Este debe ser el nombre de la nueva hoja en tu Google Sheet
SALES_WORKSHEET_NAME = "Ventas SmartFarm"

TIPO_VENTA_OPTIONS = ["Componente", "Licencia", "Servicio"]
ESTADO_VENTA_OPTIONS = ["Posible", "Cerrado", "Perdido"]  # Añadimos "Perdido" para gestión completa


# -----------------------------------------------------------
# FUNCIONES DE CONEXIÓN Y DATOS
# (Reutilizadas de 3_proyectos.py, asegurando consistencia)
# -----------------------------------------------------------

@st.cache_resource(ttl=3600)
def get_gspread_client():
    """Autentica el cliente de gspread."""
    creds_json = st.secrets["gcp_service_account"]
    return gspread.service_account_from_dict(creds_json)


@st.cache_data(ttl=300)
def load_worksheet_data(worksheet_name, force_reload_key=0):
    """Carga y devuelve todos los datos de una hoja específica en un DataFrame."""
    try:
        client = get_gspread_client()
        sheet = client.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        _ = force_reload_key
        return pd.DataFrame(data)
    except gspread.WorksheetNotFound:
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al cargar datos de {worksheet_name}: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=5)  # Cache corto para reflejar cambios recientes
def get_sales_data_for_ui(force_reload_key=0):
    """Carga datos de ventas, incluyendo el índice de fila de Sheets para edición y cálculos."""
    try:
        client = get_gspread_client()
        sheet = client.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet(SALES_WORKSHEET_NAME)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        if df.empty:
            return df

        # Conversión de Monto a numérico (necesario para sumar)
        if 'Monto' in df.columns:
            df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0.0)

        # Índice de fila para edición
        df['__sheet_row_index'] = df.index + 2

        _ = force_reload_key
        return df
    except gspread.WorksheetNotFound:
        # Si la hoja aún no existe o está vacía (sin encabezados), devolver vacío
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al cargar ventas: {e}")
        return pd.DataFrame()


def save_new_sale(sale_data):
    """Guarda la nueva venta en la hoja 'Ventas SmartFarm'."""
    try:
        client = get_gspread_client()
        sheet = client.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet(SALES_WORKSHEET_NAME)

        # Obtener encabezados actuales (si es la primera fila, garantiza que se escriban)
        if not worksheet.row_values(1):
            worksheet.append_row(list(sale_data.keys()))

        row_data = list(sale_data.values())
        worksheet.append_row(row_data)
        get_sales_data_for_ui.clear()
        return True
    except gspread.WorksheetNotFound:
        st.error(f"Error: La hoja '{SALES_WORKSHEET_NAME}' no fue encontrada.")
        return False
    except Exception as e:
        st.error(f"Error al guardar los datos de la venta: {e}")
        return False


def update_sale_data(sheet_row_index, new_sale_data):
    """Actualiza el estado, monto o detalle de una venta existente."""
    try:
        client = get_gspread_client()
        sheet = client.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet(SALES_WORKSHEET_NAME)

        cols_to_update = ["Estado de la Venta", "Monto", "Detalle de la Oportunidad/Venta"]

        headers = worksheet.row_values(1)

        for col_name in cols_to_update:
            if col_name in new_sale_data:
                col_index = headers.index(col_name) + 1
                new_value = new_sale_data[col_name]

                # Asegurar formato correcto para Monto
                if col_name == "Monto":
                    new_value = f"{float(new_value):.2f}"

                worksheet.update_cell(sheet_row_index, col_index, new_value)

        get_sales_data_for_ui.clear()
        return True
    except gspread.WorksheetNotFound:
        st.error(f"Error al actualizar: La hoja '{SALES_WORKSHEET_NAME}' no fue encontrada.")
        return False
    except Exception as e:
        st.error(f"Error al actualizar la venta: {e}")
        return False


# -----------------------------------------------------------
# LÓGICA DE CARGA GLOBAL
# -----------------------------------------------------------

st.title("💰 Gestión de Oportunidades y Ventas SmartFarm")

main_df = load_worksheet_data(MAIN_WORKSHEET_NAME)
sales_df = get_sales_data_for_ui()

if main_df.empty:
    st.error("No se pudieron cargar los clientes de la Hoja 1. Deteniendo la aplicación.")
    st.stop()

# Generación de opciones de cliente (igual que en proyectos.py)
if 'ID Cliente' in main_df.columns and 'Cliente' in main_df.columns:
    main_df['Cliente ID Combinado'] = (
            main_df['ID Cliente'].astype(str) +
            ' - ' +
            main_df['Cliente'].astype(str)
    )
    client_options = ['Selecciona un cliente'] + main_df['Cliente ID Combinado'].unique().tolist()
else:
    st.error("Error: Las columnas 'ID Cliente' o 'Cliente' no se encontraron en la Hoja 1.")
    st.stop()

# -----------------------------------------------------------
# PESTAÑAS DE NAVEGACIÓN
# -----------------------------------------------------------

tab_register, tab_manage, tab_tracker = st.tabs([
    "➕ Registrar Nueva Venta",
    "✏️ Gestionar Venta Existente",
    "📊 Tablero de Análisis de Ventas"
])

# ===========================================================
# PESTAÑA 1: REGISTRO DE NUEVA VENTA
# ===========================================================

with tab_register:
    st.header("1. Carga de Nuevo Prospecto/Venta")

    with st.form("register_sale_form", clear_on_submit=True):

        # --- FILA 1: Cliente y Tipo de Venta ---
        col1, col2 = st.columns(2)
        selected_client_combined = col1.selectbox(
            "Cliente:",
            options=client_options,
            key='reg_client_select'
        )
        tipo_venta = col2.selectbox(
            "Tipo de Venta:",
            options=TIPO_VENTA_OPTIONS,
            key='reg_tipo_venta'
        )

        # --- FILA 2: Estado y Monto ---
        col3, col4 = st.columns(2)
        estado_venta = col3.selectbox(
            "Estado de la Venta:",
            options=["Posible", "Cerrado", "Perdido"],
            key='reg_estado_venta',
            index=0  # Por defecto 'Posible'
        )
        monto = col4.number_input(
            "Monto (en números):",
            min_value=0.00,
            value=0.00,
            step=100.00,
            format="%.2f",
            key='reg_monto'
        )

        # --- FILA 3: Detalle/Comentario ---
        st.markdown("Detalle de la Oportunidad/Venta:")
        st.caption("Ej: Posible venta de componente X para optimización de rendimiento.")
        detalle = st.text_area(
            "Comentario:",
            key='reg_detalle',
            label_visibility="collapsed"
        )

        submitted = st.form_submit_button("➕ Registrar Venta")

        if submitted:
            if selected_client_combined == 'Selecciona un cliente':
                st.error("❌ Error: Debe seleccionar un cliente válido.")
            else:
                try:
                    # Extraer ID y Nombre
                    id_cliente = selected_client_combined.split(' - ')[0]
                    nombre_cliente = selected_client_combined.split(' - ')[1]
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    data_to_save = {
                        "Fecha de Registro": current_time,
                        "ID Cliente": id_cliente,
                        "Cliente": nombre_cliente,
                        "Tipo de Venta": tipo_venta,
                        "Estado de la Venta": estado_venta,
                        "Monto": monto,
                        "Detalle de la Oportunidad/Venta": detalle
                    }

                    if save_new_sale(data_to_save):
                        st.success(f"✅ Oportunidad/Venta registrada con éxito para {nombre_cliente}.")
                        st.rerun()

                except Exception as e:
                    st.error(f"❌ Error al procesar el registro: {e}")

# ===========================================================
# PESTAÑA 2: GESTIÓN/EDICIÓN DE VENTA EXISTENTE
# ===========================================================

with tab_manage:
    st.header("1. Seleccionar Venta a Gestionar")

    if sales_df.empty:
        st.info("No hay ventas registradas para gestionar.")
    else:
        # Generar opciones de selección
        sales_df['Venta ID Combinada'] = (
                sales_df['Cliente'].astype(str) + ' - ' +
                sales_df['Tipo de Venta'].astype(str) +
                ' (Monto: ' + sales_df['Monto'].round(2).astype(str) + ')'
        )

        manage_options = ['Selecciona una venta'] + sales_df['Venta ID Combinada'].tolist()

        selected_sale_combined = st.selectbox(
            "📝 Venta / Oportunidad:",
            options=manage_options,
            key='manage_sale_select'
        )

        if selected_sale_combined != 'Selecciona una venta':

            selected_record = sales_df[
                sales_df['Venta ID Combinada'] == selected_sale_combined
                ].iloc[0]

            sheet_row_index = selected_record['__sheet_row_index']

            st.markdown("---")
            st.subheader(f"Gestión de Venta: **{selected_record['Cliente']}**")

            with st.form("manage_sale_form"):

                # --- FILA 1: Estado y Monto ---
                col_m1, col_m2 = st.columns(2)

                current_estado = selected_record['Estado de la Venta']
                current_monto = float(selected_record['Monto'])

                new_estado = col_m1.selectbox(
                    "Actualizar Estado de la Venta:",
                    options=ESTADO_VENTA_OPTIONS,
                    index=ESTADO_VENTA_OPTIONS.index(current_estado),
                    key='man_estado_venta'
                )

                new_monto = col_m2.number_input(
                    "Actualizar Monto (en números):",
                    min_value=0.00,
                    value=current_monto,
                    step=100.00,
                    format="%.2f",
                    key='man_monto'
                )

                # --- FILA 2: Detalle/Comentario ---
                st.markdown("Actualizar Detalle de la Oportunidad/Venta:")
                new_detalle = st.text_area(
                    "Detalle:",
                    value=selected_record['Detalle de la Oportunidad/Venta'],
                    key='man_detalle',
                    label_visibility="collapsed"
                )

                edited = st.form_submit_button("✅ Guardar Cambios de Gestión")

                if edited:

                    data_to_update = {
                        "Estado de la Venta": new_estado,
                        "Monto": new_monto,
                        "Detalle de la Oportunidad/Venta": new_detalle,
                    }

                    if update_sale_data(sheet_row_index, data_to_update):
                        st.success(f"✅ Venta/Oportunidad de {selected_record['Cliente']} actualizada con éxito.")
                        st.rerun()
        else:
            st.info("Seleccione una venta/oportunidad de la lista desplegable para editar.")

# ===========================================================
# PESTAÑA 3: TABLERO DE ANÁLISIS DE VENTAS
# ===========================================================

with tab_tracker:
    st.header("📊 Tablero de Análisis de Ventas")

    if sales_df.empty:
        st.info("No hay datos de ventas registrados para mostrar el análisis.")
    else:
        # ---------------------
        # 1. MÉTRICAS CLAVE (KPIs)
        # ---------------------
        st.subheader("Indicadores de Desempeño (KPIs)")

        total_oportunidades = len(sales_df)

        df_cerradas = sales_df[sales_df['Estado de la Venta'] == 'Cerrado']
        df_posibles = sales_df[sales_df['Estado de la Venta'] == 'Posible']

        monto_cerrado = df_cerradas['Monto'].sum()
        monto_posible = df_posibles['Monto'].sum()

        conversion_rate = (len(df_cerradas) / total_oportunidades) * 100 if total_oportunidades > 0 else 0

        col_k1, col_k2, col_k3, col_k4 = st.columns(4)

        with col_k1:
            st.metric("Total Oportunidades", value=total_oportunidades)
        with col_k2:
            st.metric("Monto Total Cerrado", value=f"${monto_cerrado:,.2f}")
        with col_k3:
            st.metric("Monto en Posibles", value=f"${monto_posible:,.2f}")
        with col_k4:
            st.metric("Tasa de Cierre", value=f"{conversion_rate:.1f}%")

        st.markdown("---")

        # ---------------------
        # 2. GRÁFICOS DE DISTRIBUCIÓN
        # ---------------------
        st.subheader("Distribución de Ventas")

        col_g1, col_g2 = st.columns(2)

        # Gráfico 1: Monto por Tipo de Venta (Cerradas)
        with col_g1:
            if not df_cerradas.empty:
                fig_type = px.pie(
                    df_cerradas,
                    names='Tipo de Venta',
                    values='Monto',
                    title='Distribución de Monto por Tipo de Venta (Cerradas)',
                    hole=.3
                )
                st.plotly_chart(fig_type, use_container_width=True)
            else:
                st.info("No hay ventas cerradas para mostrar la distribución por tipo.")

        # Gráfico 2: Monto por Estado (Total)
        with col_g2:
            fig_estado = px.bar(
                sales_df.groupby('Estado de la Venta')['Monto'].sum().reset_index(),
                x='Estado de la Venta',
                y='Monto',
                title='Monto Total por Estado de Venta',
                color='Estado de la Venta',
                color_discrete_map={'Cerrado': '#28a745', 'Posible': '#ffc107', 'Perdido': '#dc3545'},
                text='Monto'
            )
            fig_estado.update_traces(texttemplate='$.2s', textposition='outside')
            st.plotly_chart(fig_estado, use_container_width=True)

        st.markdown("---")

        # ---------------------
        # 3. TABLA DETALLADA
        # ---------------------
        st.subheader("Listado Detallado de Oportunidades")

        display_cols = ['Fecha de Registro', 'Cliente', 'Tipo de Venta', 'Estado de la Venta', 'Monto',
                        'Detalle de la Oportunidad/Venta']

        display_df = sales_df[display_cols].rename(columns={
            'Fecha de Registro': 'Fecha',
            'Tipo de Venta': 'Tipo',
            'Estado de la Venta': 'Estado',
            'Detalle de la Oportunidad/Venta': 'Detalle'
        })

        # Formato de Monto
        display_df['Monto'] = display_df['Monto'].apply(lambda x: f"${x:,.2f}")

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )