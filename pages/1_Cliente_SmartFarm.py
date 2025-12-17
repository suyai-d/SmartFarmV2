import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
# Importamos lo necesario centralizado desde conexion.py
from conexion import (
    load_data,
    get_gspread_client,
    SHEET_ID,
    MAIN_WORKSHEET_NAME,
    COL_PUNTAJE
)

# -----------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# -----------------------------------------------------------
st.set_page_config(
    page_title="Gestión de Clientes - SmartFarm",
    layout="wide",
    page_icon="sf1.png"
)

# --- CONSTANTES ---
EVALUATION_CATEGORIES = ["Granos", "Ganadería", "Cultivos de Alto Valor"]
BRANCHES = ["Córdoba", "Pilar", "Sinsacate", "Arroyito", "Santa Rosa"]
CLIENT_TYPES = ["Tipo 1", "Tipo 2", "Tipo 3"]

# Diccionario de evaluación (Mantenemos la estructura de items)
EVALUATION_MAP = {
    "Granos": {
        "worksheet": "Granos",
        "items": [
            ("Item 1: Organización y estandarización de lotes.", 5, "Configuración/ Campos / Campos / Vista tabla..."),
            ("Item 2: Línea de guiado.", 5, "Configuración/ Campos/ Filtro campos sin guiado..."),
            ("Item 3: Organización altamente conectada.", 10, "Al menos un campo con tres tipos de labores cargadas."),
            ("Item 4: Uso de planificador de trabajo.", 15,
             "Planes de Trabajo enviados al equipo en los últimos 12 meses."),
            ("Item 5: Uso de Operations Center Mobile.", 10, "Navegación en la plataforma Móvil + Testimonio."),
            ("Item 6: JDLink.", 5, "Servicio de Conectividad JDLink activado."),
            ("Item 7: Envío remoto. Mezcla de tanque.", 10, "Mezcla de tanque generada o uso de SIA."),
            ("Item 8: % uso de autotrac en Tractor.", 10, "Promedio 40% de uso en tractores > 140 hp."),
            ("Item 9: % uso autotrac Cosecha.", 10, "Promedio 70% de uso en cosechadoras."),
            ("Item 10: % uso autotrac Pulverización.", 10, "Promedio 70% de uso en pulverizadoras."),
            ("Item 11: Uso de funcionalidades avanzadas.", 15, "Reporte + Video testimonio del cliente."),
            ("Item 12: Uso de tecnologías integradas.", 10, "Combine Advisor/ActiveYield/ExactApply/Sección."),
            ("Item 13: Señal de corrección StarFire.", 5, "Uso de señal SF2, SF3 o RTK."),
            ("Item 14: Paquete CSC.", 10, "Factura del paquete contratado."),
            ("Item 15: Vinculación de API.", 5, "Conexión activa mayor a 4 meses."),
            ("Item 16: JDLink en otra marca.", 15, "JDLink instalado en maquinaria de otra marca."),
        ]
    },
    "Ganadería": {
        "worksheet": "Ganadería",
        "items": [
            ("Item 1: Organización y estandarización de lotes.", 15, "Estandarización de lotes en OC."),
            ("Item 2: Digitalizar capa de siembra y mapa de picado.", 10,
             "Mapas de siembra y picado en el mismo lote."),
            ("Item 3: Uso de planificador de trabajo.", 20, "Uso en Siembra, Pulverización y Cosecha."),
            ("Item 4: Equipo registrados en el Centro de Operaciones.", 5, "Equipos e implementos de alimentación."),
            ("Item 5: Operadores registrados en el Centro de Operaciones.", 5,
             "Registro de empleados en la plataforma."),
            ("Item 6: Productos registrados en el Centro de Operaciones.", 5, "Químicos, variedades y fertilizantes."),
            ("Item 7: Uso de Operations Center Mobile.", 10, "Uso de App móvil + Testimonio."),
            ("Item 8: JDLink activado en máquinas John Deere.", 10, "Conectividad activa en flota JD."),
            ("Item 9: Planes de mantenimiento en tractores.", 10, "Seguimiento de mantenimiento en alimentación."),
            ("Item 10: Mapeo de constituyentes.", 20, "Uso de sensores de constituyentes (HarvestLab)."),
            ("Item 11: Conectividad alimentación.", 20, "Tractor de alimentación conectado."),
            ("Item 12: Generación de informes.", 10, "Informes de máquina generados."),
            ("Item 13: Paquete contratado con el concesionario (CSC).", 10, "Factura de servicios contratados."),
        ]
    },
    "Cultivos de Alto Valor": {
        "worksheet": "Cultivos de Alto Valor",
        "items": [
            ("Item 1: Organización y estandarización de lotes.", 15, "Configuración de campos."),
            ("Item 2: Lineas de guiado.", 5, "Lotes con líneas de guiado cargadas."),
            ("Item 3: Tener al menos una labor digitalizada.", 10, "Informe de cualquier labor digital."),
            ("Item 4: Uso de planificador de trabajo para alguna operación.", 15, "Planificación de tareas en OC."),
            ("Item 5: Uso del Operations Center Mobile.", 10, "App móvil y testimonio de valor."),
            ("Item 6: JDLink activado en máquinas John Deere.", 10, "Conectividad en equipos especializados."),
            ("Item 7: % uso de autotrac en Tractor.", 20, "Uso de guiado automático en tractores."),
            ("Item 8: Implement Guidance.", 20, "Uso de guiado de implementos."),
            ("Item 9: Señal de corrección StarFire.", 10, "Uso de señales de alta precisión."),
            ("Item 10: Paquete contratado con el concesionario (CSC).", 10, "Soporte especializado contratado."),
            ("Item 11: Equipos Registrados en Operations Center.", 5, "Inventario de equipos."),
            ("Item 12: Operadores registrados en Operations Center.", 5, "Staff cargado en plataforma."),
            ("Item 13: Productos registrados en el Operations Center.", 5, "Insumos y variedades."),
            ("Item 14: Configuración de Alertas Personalizables.", 10, "Alertas de mantenimiento o geocercas."),
        ]
    }
}


# --- FUNCIONES AUXILIARES ---
def get_row_index(worksheet, id_cliente, timestamp):
    data = worksheet.get_all_values()
    if not data: return None
    df_idx = pd.DataFrame(data[1:], columns=data[0])
    # Normalizamos para búsqueda segura
    df_idx.columns = [c.strip().upper() for c in df_idx.columns]
    match = df_idx[(df_idx['ID CLIENTE'].astype(str) == str(id_cliente)) & (df_idx['FECHA Y HORA'] == timestamp)]
    return match.index[0] + 2 if not match.empty else None


# -----------------------------------------------------------
# INTERFAZ PRINCIPAL
# -----------------------------------------------------------
st.title("🚜 Gestión de Clientes SmartFarm")

t1, t2, t3 = st.tabs(["➕ Registro", "✏️ Modificar", "📊 Análisis"])

# --- TAB 1: REGISTRO ---
with t1:
    st.header("Nuevo Registro")
    cat_seleccionada = st.selectbox("Categoría de Evaluación", EVALUATION_CATEGORIES, key="cat_reg")

    with st.form("f_reg_cliente", clear_on_submit=True):
        c1, c2 = st.columns(2)
        id_c = c1.text_input("ID Cliente (6 dígitos)", max_chars=6)
        nom = c2.text_input("Razón Social")

        c3, c4 = st.columns(2)
        suc = c3.selectbox("Sucursal", BRANCHES)
        tip = c4.selectbox("Tipo de Cliente", CLIENT_TYPES)

        st.divider()
        scores = {}
        items_list = EVALUATION_MAP[cat_seleccionada]["items"]
        cols = st.columns(2)

        for i, (name, max_s, desc) in enumerate(items_list):
            with cols[i % 2]:
                scores[name] = st.slider(f"{name}", 0, max_s, 0, key=f"s_{cat_seleccionada}_{i}")
                with st.expander("Ayuda"): st.write(desc)

        if st.form_submit_button("✅ Guardar"):
            if len(id_c) == 6 and nom:
                try:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    total = sum(scores.values())
                    client = get_gspread_client()
                    sh = client.open_by_key(SHEET_ID)

                    sh.worksheet(MAIN_WORKSHEET_NAME).append_row([now, cat_seleccionada, id_c, nom, suc, tip, total])
                    sh.worksheet(EVALUATION_MAP[cat_seleccionada]["worksheet"]).append_row(
                        [now, id_c] + list(scores.values()))

                    st.success("¡Cliente registrado!")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Complete ID (6 dígitos) y Nombre.")

# --- TAB 2: MODIFICAR ---
with t2:
    df_m = load_data(MAIN_WORKSHEET_NAME)
    if not df_m.empty:
        df_m['LABEL'] = df_m['ID CLIENTE'].astype(str) + " - " + df_m['CLIENTE']
        choice = st.selectbox("Seleccione para editar", ["..."] + df_m['LABEL'].tolist())

        if choice != "...":
            sel_row = df_m[df_m['LABEL'] == choice].iloc[0]
            cat = sel_row['CATEGORÍA DE EVALUACIÓN']

            # Cargar datos de la hoja específica
            df_detail = load_data(EVALUATION_MAP[cat]["worksheet"])
            detail_match = df_detail[(df_detail['ID CLIENTE'].astype(str) == str(sel_row['ID CLIENTE'])) &
                                     (df_detail['FECHA Y HORA'] == sel_row['FECHA Y HORA'])]

            if not detail_match.empty:
                ev_row = detail_match.iloc[0]
                with st.form("f_mod_cliente"):
                    st.subheader(f"Editando: {sel_row['CLIENTE']}")
                    new_nom = st.text_input("Nombre", sel_row['CLIENTE'])
                    new_suc = st.selectbox("Sucursal", BRANCHES, index=BRANCHES.index(sel_row['SUCURSAL']))

                    new_scores = {}
                    cols_ed = st.columns(2)
                    for i, (name, max_s, _) in enumerate(EVALUATION_MAP[cat]["items"]):
                        val = int(ev_row.get(name.strip().upper(), 0))
                        with cols_ed[i % 2]:
                            new_scores[name] = st.slider(name, 0, max_s, val, key=f"mod_{i}")

                    if st.form_submit_button("💾 Actualizar"):
                        try:
                            client = get_gspread_client()
                            sh = client.open_by_key(SHEET_ID)

                            # Update Main
                            ws1 = sh.worksheet(MAIN_WORKSHEET_NAME)
                            idx1 = get_row_index(ws1, sel_row['ID CLIENTE'], sel_row['FECHA Y HORA'])
                            if idx1:
                                ws1.update_cell(idx1, 4, new_nom)
                                ws1.update_cell(idx1, 5, new_suc)
                                ws1.update_cell(idx1, 7, sum(new_scores.values()))

                            # Update Detail
                            ws2 = sh.worksheet(EVALUATION_MAP[cat]["worksheet"])
                            idx2 = get_row_index(ws2, sel_row['ID CLIENTE'], sel_row['FECHA Y HORA'])
                            if idx2:
                                headers = [h.strip().upper() for h in ws2.row_values(1)]
                                for k, v in new_scores.items():
                                    if k.strip().upper() in headers:
                                        ws2.update_cell(idx2, headers.index(k.strip().upper()) + 1, v)

                            st.success("¡Datos actualizados!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
    else:
        st.info("Sin datos.")

# --- TAB 3: ANÁLISIS ---
with t3:
    df_a = load_data(MAIN_WORKSHEET_NAME)
    if not df_a.empty:
        target = COL_PUNTAJE.upper()
        df_a[target] = pd.to_numeric(df_a[target], errors='coerce').fillna(0)

        # Filtros rápidos
        c1, c2 = st.columns(2)
        f_cat = c1.multiselect("Categorías", EVALUATION_CATEGORIES, default=EVALUATION_CATEGORIES)
        f_suc = c2.multiselect("Sucursales", BRANCHES, default=BRANCHES)

        df_f = df_a[df_a['CATEGORÍA DE EVALUACIÓN'].isin(f_cat) & df_a['SUCURSAL'].isin(f_suc)]

        st.plotly_chart(
            px.bar(df_f.sort_values(target), x=target, y='CLIENTE', color='CATEGORÍA DE EVALUACIÓN', orientation='h',
                   title="Ranking de Clientes"), use_container_width=True)
    else:
        st.info("Registre clientes para ver el análisis.")
