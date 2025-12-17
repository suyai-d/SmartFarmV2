import os
from datetime import datetime
import gspread
import pandas as pd
import streamlit as st
import plotly.express as px
from conexion import load_data, SHEET_ID, MAIN_WORKSHEET_NAME, COL_PUNTAJE


# -----------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# -----------------------------------------------------------
st.set_page_config(
    page_title="SmartFarm - Conci",
    layout="wide",
    page_icon="sf1.png",
    initial_sidebar_state="collapsed",
)


EVALUATION_CATEGORIES = ["Granos", "Ganadería", "Cultivos de Alto Valor"]
BRANCHES = ["Córdoba", "Pilar", "Sinsacate", "Arroyito", "Santa Rosa"]
CLIENT_TYPES = ["Tipo 1", "Tipo 2", "Tipo 3"]

# MAPEO COMPLETO DE ÍTEMS
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


# -----------------------------------------------------------
# FUNCIONES DE CONEXIÓN
# -----------------------------------------------------------
@st.cache_resource(ttl=3600)
def get_gspread_client():
    creds_json = st.secrets["gcp_service_account"]
    return gspread.service_account_from_dict(creds_json)


@st.cache_data(ttl=300)
def load_data(ws_name):
    try:
        client = get_gspread_client()
        sh = client.open_by_key(SHEET_ID)
        df = pd.DataFrame(sh.worksheet(ws_name).get_all_records())
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except:
        return pd.DataFrame()


def get_row_index(worksheet, id_cliente, timestamp):
    data = worksheet.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])
    match = df[(df['ID Cliente'].astype(str) == str(id_cliente)) & (df['Fecha y Hora'] == timestamp)]
    return match.index[0] + 2 if not match.empty else None


# -----------------------------------------------------------
# INTERFAZ PRINCIPAL
# -----------------------------------------------------------
st.title("🚜 SmartFarm Dashboard - Conci")

t1, t2, t3 = st.tabs(["➕ Registro", "✏️ Modificar", "📊 Análisis"])

# --- TAB 1: REGISTRO ---
with t1:
    st.header("Nuevo Registro de Cliente")

    # IMPORTANTE: El selector de categoría está FUERA del form para activar el refresco
    cat_seleccionada = st.selectbox("Elija la Categoría de Evaluación", EVALUATION_CATEGORIES)

    with st.form("f_reg", clear_on_submit=True):
        c1, c2 = st.columns(2)
        id_c = c1.text_input("ID Cliente (6 dígitos)", max_chars=6)
        nom = c2.text_input("Cliente / Razón Social")

        c3, c4, c5 = st.columns(3)
        suc = c3.selectbox("Sucursal", BRANCHES)
        tip = c4.selectbox("Tipo de Cliente", CLIENT_TYPES)

        st.divider()
        st.subheader(f"Puntuación: {cat_seleccionada}")

        scores = {}
        # Cargamos los items correspondientes a la categoría seleccionada arriba
        items_list = EVALUATION_MAP[cat_seleccionada]["items"]
        cols = st.columns(2)

        for i, (name, max_s, desc) in enumerate(items_list):
            with cols[i % 2]:
                # Usamos una clave única combinando categoría e índice para evitar errores de estado
                scores[name] = st.slider(f"{name} (Máx: {max_s})", 0, max_s, 0, key=f"reg_{cat_seleccionada}_{i}")
                with st.expander("Ver criterios de evaluación"):
                    st.write(desc)

        if st.form_submit_button("✅ Guardar Registro"):
            if len(id_c) == 6 and nom:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                tot = sum(scores.values())
                client = get_gspread_client()
                sh = client.open_by_key(SHEET_ID)

                # Guardar en Hoja Principal (Hoja 1)
                sh.worksheet(MAIN_WORKSHEET_NAME).append_row([now, cat_seleccionada, id_c, nom, suc, tip, tot])

                # Guardar en Hoja de Detalles (Granos, Ganadería, etc.)
                sh.worksheet(EVALUATION_MAP[cat_seleccionada]["worksheet"]).append_row(
                    [now, id_c] + list(scores.values()))

                st.success(f"¡Cliente {nom} guardado exitosamente en {cat_seleccionada}!")
                load_data.clear()
            else:
                st.error("Error: Verifique que el ID tenga 6 dígitos y el nombre no esté vacío.")

# --- TAB 2: MODIFICAR ---
with t2:
    df_m = load_data(MAIN_WORKSHEET_NAME)
    if not df_m.empty:
        df_m['LABEL'] = df_m['ID CLIENTE'].astype(str) + " - " + df_m['CLIENTE'] + " (" + df_m['FECHA Y HORA'] + ")"
        choice = st.selectbox("Seleccione cliente a editar", ["Seleccionar..."] + df_m['LABEL'].tolist())

        if choice != "Seleccionar...":
            sel_row = df_m[df_m['LABEL'] == choice].iloc[0]
            curr_cat = sel_row['CATEGORÍA DE EVALUACIÓN']
            df_ev = load_data(EVALUATION_MAP[curr_cat]["worksheet"])

            # Buscamos la fila de detalles
            ev_row = df_ev[(df_ev['ID CLIENTE'].astype(str) == str(sel_row['ID CLIENTE'])) & (
                    df_ev['FECHA Y HORA'] == sel_row['FECHA Y HORA'])].iloc[0]

            with st.form("f_mod"):
                st.subheader(f"Editando: {sel_row['CLIENTE']} ({curr_cat})")
                c_nom = st.text_input("Nombre", sel_row['CLIENTE'])
                c_suc = st.selectbox("Sucursal", BRANCHES, index=BRANCHES.index(sel_row['SUCURSAL']))
                c_tip = st.selectbox("Tipo", CLIENT_TYPES, index=CLIENT_TYPES.index(sel_row['TIPO DE CLIENTE']))

                new_scores = {}
                cols_edit = st.columns(2)
                for i, (name, max_s, _) in enumerate(EVALUATION_MAP[curr_cat]["items"]):
                    # Normalizamos el nombre para buscar en el dataframe cargado
                    val = int(ev_row.get(name.strip().upper(), 0))
                    with cols_edit[i % 2]:
                        new_scores[name] = st.slider(name, 0, max_s, val, key=f"mod_{i}")

                if st.form_submit_button("💾 Actualizar"):
                    client = get_gspread_client()
                    sh = client.open_by_key(SHEET_ID)

                    # Actualizar Hoja Principal
                    ws1 = sh.worksheet(MAIN_WORKSHEET_NAME)
                    idx1 = get_row_index(ws1, sel_row['ID CLIENTE'], sel_row['FECHA Y HORA'])
                    if idx1:
                        ws1.update_cell(idx1, 4, c_nom)
                        ws1.update_cell(idx1, 5, c_suc)
                        ws1.update_cell(idx1, 6, c_tip)
                        ws1.update_cell(idx1, 7, sum(new_scores.values()))

                    # Actualizar Hoja de Detalles
                    ws2 = sh.worksheet(EVALUATION_MAP[curr_cat]["worksheet"])
                    idx2 = get_row_index(ws2, sel_row['ID CLIENTE'], sel_row['FECHA Y HORA'])
                    if idx2:
                        hd = ws2.row_values(1)
                        for k, v in new_scores.items():
                            if k in hd: ws2.update_cell(idx2, hd.index(k) + 1, v)

                    st.success("¡Datos actualizados correctamente!")
                    load_data.clear()
                    st.rerun()

# --- TAB 3: ANÁLISIS ---
with t3:
    df_a = load_data(MAIN_WORKSHEET_NAME)
    target = COL_PUNTAJE.upper()

    if not df_a.empty and target in df_a.columns:
        df_a[target] = pd.to_numeric(df_a[target], errors='coerce').fillna(0)

        st.header("📊 Tablero de Análisis")
        fa, fb = st.columns(2)
        f_cat = fa.selectbox("Filtrar por Categoría", ["Todas"] + EVALUATION_CATEGORIES, key="f_cat_an")
        f_suc = fb.selectbox("Filtrar por Sucursal", ["Todas"] + BRANCHES, key="f_suc_an")

        df_f = df_a.copy()
        if f_cat != "Todas": df_f = df_f[df_f['CATEGORÍA DE EVALUACIÓN'] == f_cat]
        if f_suc != "Todas": df_f = df_f[df_f['SUCURSAL'] == f_suc]

        # Leaderboard
        st.subheader("🏆 Ranking de Clientes")
        st.dataframe(df_f[['CLIENTE', target, 'SUCURSAL', 'CATEGORÍA DE EVALUACIÓN']].sort_values(target,
                                                                                                  ascending=False).reset_index(
            drop=True),
                     use_container_width=True)

        st.divider()
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("Distribución por Categoría")
            st.plotly_chart(px.pie(df_f, names='CATEGORÍA DE EVALUACIÓN', hole=0.4, title="Clientes Registrados"),
                            use_container_width=True)
        with col_g2:
            st.subheader("Puntajes por Categoría")
            st_cat = df_f.groupby('CATEGORÍA DE EVALUACIÓN')[target].agg(['sum', 'mean']).reset_index()
            st_cat.columns = ['Categoría', 'Puntaje Total', 'Puntaje Promedio']
            st.plotly_chart(
                px.bar(st_cat.melt(id_vars='Categoría'), x='Categoría', y='value', color='variable', barmode='group',
                       text_auto='.1f', title="Comparativa de Desempeño"), use_container_width=True)

        st.divider()
        st.subheader("🏢 Análisis por Sucursal")
        st_suc = df_f.groupby('SUCURSAL')[target].agg(['sum', 'mean']).reset_index()
        st_suc.columns = ['Sucursal', 'Puntaje Total', 'Puntaje Promedio']
        st.plotly_chart(
            px.bar(st_suc.melt(id_vars='Sucursal'), x='Sucursal', y='value', color='variable', barmode='group',
                   text_auto='.1f', title="Total vs Promedio por Sucursal"), use_container_width=True)

        st.divider()
        st.subheader("📋 Resumen Estadístico")
        res = df_f.groupby('SUCURSAL').agg(
            Inscriptos=('ID CLIENTE', 'count'),
            Puntaje_Total=(target, 'sum'),
            Puntaje_Promedio=(target, 'mean')
        ).reset_index()
        st.table(res.style.format({'Puntaje_Total': '{:.0f}', 'Puntaje_Promedio': '{:.2f}'}))
    else:
        st.info("💡 Aún no hay datos para mostrar en el análisis. Registre un cliente para comenzar.")