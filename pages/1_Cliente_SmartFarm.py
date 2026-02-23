import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
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

# EVALUATION_MAP se mantiene igual (es tu configuración de entrada)
EVALUATION_MAP = {
    "Granos": {
        "worksheet": "Granos",
        "items": [
            ("Item 1: Organización y estandarización de lotes.", 5, "Campos con límites / Campos totales  **-> Consideraciones:** En el caso de organizaciones con menos del 60% fuera del estándar, la puntuación de este ítem se restablece a cero. Caso contrario se otorgará el puntaje proporcional correspondiente: 60 a 70 % 1 punto | 70 a 80 % 2 puntos | 80 a 90% 3 puntos | 90 a 95 % 4 puntos | más de 95 % 5 puntos."),
            ("Item 2: Línea de guiado.", 5, "Campos con guiado / Campos totales **-> Consideraciones:** Será requisito que al menos 40% de los lotes cuenten con guiado | 40 a 60 % 1 punto | 60 a 70 % 2 puntos | 70 a 80 % 3 puntos | 80 a 90 % 4 puntos | más del 90 % 5 puntos."),
            ("Item 3: Organización altamente conectada.", 10, "Al menos un campo con tres tipos de labores cargadas."),
            ("Item 4: Uso de planificador de trabajo.", 15,
             "Video demostrativo de los Planes de Trabajo enviados entre el 1 de junio de 2025 a 1 de junio de 2026. **-> Consideraciones:** En los últimos 12 meses tener al menos una operación de cada una de las 3 etapas (siembra - pulverización - cosecha) en la cual se haya utilizando el planificador de trabajo. El trabajo necesariamente debe haber sido enviado al equipo y debe tener al menos un 20% de avance. Cada etapa contabiliza 5 puntos, siendo posible acumular 15 puntos al utilizar el planificador de trabajo en las 3 etapas."),
            ("Item 5: Uso de Operations Center Mobile.", 10, "Grabación de video que demuestre la navegación en la plataforma Móvil, capturando la pantalla inicial y demostrando información de al menos un equipo y un mapa agronómico de la campaña 25/26 y la vista del planificador de trabajo. La ausencia de cualquiera de los ítems descritos anteriormente se considerará puntuación cero para este ítem."),
            ("Item 6: JDLink.", 5, "Captura de pantalla desde Operations Center de la pestaña Equipo, que demuestre el Servicio de Conectividad JDLink; y Captura pantalla sin fitro, donde se visualice el total de máquinas. **-> Consideraciones:** En el caso de organizaciones con menos del 30% de máquinas con servicio de conectividad activado, la puntuación de este ítem se restablece a cero. Se otorgará el puntaje proporcional correspondiente: 40 a 50 % 1 punto | 50 a 60% 2 puntos | 60 a 70% 3 puntos | 70 a 80 % 4 puntos | más de 80% 5 puntos. Los dispositivos pendientes de transferencia y/o inactivos no se contarán."),
            ("Item 7: Envío remoto. Mezcla de tanque.", 5, "Captura de pantalla desde Operations Center donde se vea una mezcla de tanque generada con fecha actualizada anterior a febrero de 2026; o Captura de pantalla desde SIA evidenciando uso de ordenes de trabajo. **-> Consideraciones:** Para el caso de SIA los puntajes impactarán según se detalla a continuación: 20 a 30% 1 puntos | 30 a 40% 2 puntos | 40 a 50 % 3 puntos | más de 50% 5 puntos."),
            ("Item 8: % uso de autotrac en Tractor.", 10, "Captura de pantalla en analizador de máquina/ uso de tecnología donde se muestren todos los equipos de la organización. Filtro de fecha del 1 jun 2025 a 1 de jun 2026. **-> Consideraciones:** Se solicitará en promedio, un 40% de uso de autotrac en tractores de mas de 140 hp."),
            ("Item 9: % uso autotrac Cosecha.", 10, "Captura de pantalla en analizador de máquina/ uso de tecnología donde se muestren todos los equipos de la organización. Filtro de fecha del 1 jun 2025 a 1 de jun 2026. **-> Consideraciones:** Se solicitará en promedio, un 70% de uso de autotrac en cosechadoras."),
            ("Item 10: % uso autotrac Pulverización.", 10, "Captura de pantalla en analizador de máquina/ uso de tecnología donde se muestren todos los equipos de la organización. Filtro de fecha del 1 de jun 2025 a 1 de jun 2026 **-> Consideraciones:** Se solicitará en promedio, un 70% de uso de autotrac en pulverizadoras."),
            ("Item 11: Uso de funcionalidades avanzadas.", 15, "Autopath, ATTA, Guiado Pasivo y Machine Sync. Analizador de máquina - vista guiado - filtro del 1 de jun 2025 a 1 de jun 2026. **-> Consideraciones:** Uso de alguna de las funcionalidades mencionadas: 5 puntos. | Uso superior a 50 % en algún equipo para alguna de las funcionalidades mencionadas: 10 puntos adicionales."),
            ("Item 12: Uso de tecnologías integradas.", 15, "PGSA, PSA, ATA, Combine Advisor, Active Yield, Pulsación, Control de sección. Analizador de máquina - filtro de fecha del 1 jun 2025 al 1 jun 2026. **-> Consideraciones:** Para algunas de las funcionalidades mencionadas en Cosecha: 5 puntos, Pulverización: 5 puntos. Uso superior a 50 % en algún equipo para alguna de las funcionalidades mencionadas: 5 puntos adicionales."),
            ("Item 13: Señal de corrección StarFire.", 10, "Captura de pantalla desde Operations Center en Analizador de máquina/uso de tecnología. **-> Consideraciones:** Señal de corrección StarFire y/o RTK (SF2, SF3, SF-RTK y RTK) en al menos en una etapa del ciclo productivo: 5 puntos. Se obtendrá 5 puntos extra si se utiliza señal SF-RTK."),
            ("Item 14: Paquete CSC.", 5, "Factura del paquete contratado."),
            ("Item 15: Vinculación de API.", 5, "Captura de pantalla desde Operations Center: Configuración / Conexiones / Seleccionar la herramienta conectada / Administrar / Organizaciones conectadas. **-> Consideraciones:** La fecha de conexión, que debe ser mayor a 4 meses desde la fecha de envío del informe."),
            ("Item 16: JDLink en otra marca.", 15, "Captura de pantalla desde <Equipos> en Operations Center. PLA no se considera otra marca."),
        ]
    },
    "Ganadería": {
        "worksheet": "Ganadería",
        "items": [
            ("Item 1: Organización y estandarización de lotes.", 10, "Captura de pantalla desde Operations Center: Configuración/ Campos / Campos / Vista tabla. Excel o PDF de vista anterior. **-> Consideraciones:** En el caso de organizaciones con menos del 60% fuera del estándar, la puntuación de este ítem se restablece a cero. Caso contrario se otorgará el puntaje proporcional correspondiente: 60 a 70 % 2 puntos | 70 a 80 % 4 puntos | 80 a 90% 6 puntos | 90 a 95 % 8 puntos | más de 95 % 10 puntos."),
            ("Item 2: Labor Digitalizada", 10,"En al menos un lote tener digitalizada la capa de siembra y cosecha (mapa picado). **-> Consideraciones:** Sicuenta con las dos capas 5 puntos | adicional de 5 puntos si realizó alguna labor de manera variable (siembra / ferti)."),
            ("Item 3: Uso de planificador de trabajo.", 15, "Video demostrativo: Planes de trabajo importados entre el 1 jun 2025 a 1 jun 2026. **-> Consideraciones:** el trabajo debe haber sido enviado y tener al menos un 20 % de avance. Cada etapa contabiliza 5 puntos (5 siembra, 5 cosecha, 5 aplicación)."),
            ("Item 4: Equipo registrados en el Centro de Operaciones.", 5, "Video demostrativo de la organización donde se vea dos equipos y al menos un implemento asociado a la alimentación en cargador frontal."),
            ("Item 5: Operadores registrados en el Centro de Operaciones.", 5,
             "Captura de pantalla: Configuración -> Gestor de Equipo -> Pestaña Operadores con al menos un empleado añadido."),
            ("Item 6: Productos registrados en el Centro de Operaciones.", 5, "Captura de pantalla: Configuración -> Productos e insumos -> al menos un producto químico o variedad registrada."),
            ("Item 7: Uso de Operations Center Mobile.", 10, "Grabación de video que demuestre la navegación en la plataforma Móvil, capturando la pantalla inicial y demostrando información de al menos un equipo y un mapa agronómico de la pantalla 25/26 y la vista del planificador de trabajo. La ausencia de cualquiera de los ítems descritos anteriormente se considerará puntuación cero para este ítem."),
            ("Item 8: JDLink activado en máquinas John Deere.", 10, "Maquinas con conectividad / Maquinas totales **-> Consideraciones:** En el caso de organizaciones con menos del 40% de máquinas con servicio de conectividad activado, la puntuación de este ítem se restablece a cero. Se otorgará el puntaje proporcional correspondiente: 40 a 50 % 2 punto | 50 a 60% 4 puntos | 60 a 70% 6 puntos | 70 a 80 % 8 puntos | más de 80% 10 puntos. Los dispositivos pendientes de transferencia y/o inactivos no se contarán."),
            ("Item 9: Planes de mantenimiento en tractores.", 10, "¨Planes de Mantenimiento Personalizado para el 50 % de máquinas John Deere. **-> Consideraciones:** 50 a 60 % 2 puntos | 60 a 70 % 4 puntos | 70 a 80 % 6 puntos | 80 a 90 % 8 puntos | más del 90 % 10 puntos."),
            ("Item 10: Mapeo de constituyentes.", 15, "Captura de pantallas desde el analizador de campos mostrando las capas de picado donde se evidencia el sensado de constituyentes en la temporada 2025/26. **-> Consideraciones:** si cuenta con el sensado de constituyentes equivale a 15 puntos, sino 0."),
            ("Item 11: Mapeo de Corte o Henificación", 15,"Captura de pantalla desde el analizador de campos mostrando un mapa de corte o henificación registrado en la temporada 2025/26. **-> Consideraciones:** si cuenta con el mapa equivale a 15 puntos, sino 0."),
            ("Item 12: Conectividad alimentación.", 20, "Al menos un tractor con conectividad visible en Operations Center. Evidencia captura de pantalla o video demostrando el recorrido en el patio de comida."),
            ("Item 13: Alertas Personalizables", 15, "Captura de pantalla: Mapa -> Equipos donde muestra alguna alerta personalizable (ralenti, velocidad, nivel de cobustible). **-> Consideraciones:** la fecha de la alerta debe ser anterior o igual al 31/01/2026."),
            ("Item 14: Paquete contratado con el concesionario (CSC).", 5, "Factura del paquete contratado."),
        ]
    },
    "Cultivos de Alto Valor": {
        "worksheet": "Cultivos de Alto Valor",
        "items": [
            ("Item 1: Organización y estandarización de lotes.", 15, "Campos con  límites / Campos totales **-> Consideraciones:** En el caso de organizaciones con menos del 60% fuera del estándar, la puntuación de este ítem se restablece a cero. Caso contrario se otorgará el puntaje proporcional correspondiente: 60 a 70 % 3 punto | 70 a 80 % 6 puntos | 80 a 90% 9 puntos | 90 a 95 % 12 puntos | más de 95 % 15 puntos."),
            ("Item 2: Labor Digitalizada.", 10, "Tener una operación digitalizada. Presentar el pdf del informe del Analizador de Trabajo de cualquier operación, ya sea preparación de suelo, siembra, pulverización o cosecha que se haya realizado."),
            ("Item 3: Uso del Operations Center Mobile.", 10, "Grabación de video que demuestre la navegación en la plataforma móvil, capturando la pantalla inicial y demostrando información de al menos un equipo y un mapa agronómico de la campaña 25/26 y la vista de planificador de trabajo. **-> Consideraciones:** La ausencia de cualquiera de los ítems descritos se considerará puntuación 0."),
            ("Item 4: JDLink activado en máquinas John Deere.", 10, "Equipos con conectividad / Total equipos. **-> Consideraciones:** En caso de organizaciones con menos del 40 % de máquinas con servicio de conectividad, la puntuación se restablece a cero. Del 40 a 50 % 2 puntos | 50 a 60 % 4 puntos | 60 a 70 % 6 puntos | 70 a 80 % 8 puntos | más del 80 % 10 puntos. Los dispositivos pendientes de transferencia y/o inactivos, no se considerarán."),
            ("Item 5: Lineas de guiado", 5, "Campos con guiado / Campos totales. **-> Consideraciones:** Será requisito que al menos el 20 % de los campos cuenten con guiado. De 20 a 40 % 1 punto | 40 a 50 % 2 puntos | 50 a 60 % 3 puntos | 60 a 80 % 4 puntos | más de 80 % 5 puntos."),
            ("Item 6: % uso de Autotrac en Tractor", 20, "Analizador de máquina - Guiado donde se muestren todos los equipos. Filtro de fechas entre el 1 jun 2025 a 1 jun 2026. **-> Consideraciones:** se solicitará un promedio de 30% de uso de Autotrac en tractores de menos de 140 hp"),
            ("Item 7: Uso de funcionalidades avanzadas: Guiado Pasivo de Implemento", 20, "Analizador de máquina - vista guiado. **-> Consideraciones:** al menos un equipo con la utilización de Guiado Pasivo del Implemento."),
            ("Item 8: Señal de corrección StarFire.", 10, "Analizador de máquina - métricas StarFire. Filtro de fechas entre el 1 jun 2025 a 1 jun 2026 **-> Consideraciones:** señal de corrección StarFire y/o RTK (SF2, SF3, SF-RTK, RTK) en al menos una etapa del ciclo productivo. Se obtendrán 5 puntos extra si se utiliza señal SF-RTK."),
            ("Item 9: Paquete contratado con el concesionario (CSC).", 5, "Factura del paquete contratado."),
            ("Item 10: Equipos Registrados en Operations Center.", 5, "Video demostrativo: Configuración -> Equipo -> pestaña Máquina y pestaña Apero donde debe verse 2 equipos y al menos 1 implemento."),
            ("Item 11: Operadores registrados en Operations Center.", 5, "Captura de pantalla: Configuración -> Gestor de Equipo -> Pestaña Operadores donde debe verse al menos un empleado añadido."),
            ("Item 12: Productos registrados en el Operations Center.", 5, "Captura de pantalla: Configuración -> Productos e insumos -> al menos un producto químico o variedad registrada."),
            ("Item 13: Alertas Personalizables.", 15, "Captura de pantalla: Mapa -> Equipos -> pestaña Avisos, debe mostrarse al menos alguna alerta personalizable (ralenti, velocidad, nivel de combustible). La fecha de la alerta debe ser anterior o igual al 31/01/2026."),
            ("Item 14: Uso del planificador de trabajo para alguna operacion.", 15, "Captura de pantalla: Planificador de trabajo con al menos un trabajo en estado importado, entre el 1 junio 2025 y 1 junio 2026."),
        ]
    }
}


# --- FUNCIONES AUXILIARES ---
def get_row_index(worksheet, id_cliente, timestamp):
    data = worksheet.get_all_values()
    if not data: return None
    df_idx = pd.DataFrame(data[1:], columns=data[0])
    # Normalizamos columnas para búsqueda segura: 'ID CLIENTE' y 'FECHA DE REGISTRO'
    df_idx.columns = [c.strip().upper() for c in df_idx.columns]

    # IMPORTANTE: Usamos los nombres normalizados en mayúsculas
    match = df_idx[
        (df_idx['ID CLIENTE'].astype(str) == str(id_cliente)) &
        (df_idx['FECHA Y HORA'].astype(str) == str(timestamp))
        ]
    return match.index[0] + 2 if not match.empty else None


# -----------------------------------------------------------
# INTERFAZ PRINCIPAL
# -----------------------------------------------------------
st.title("🚜 Gestión de Clientes SmartFarm")

t1, t2, t3 = st.tabs(["➕ Registro", "✏️ Modificar", "📊 Análisis"])

# --- TAB 1: REGISTRO (Misma lógica) ---
with t1:
    st.header("Nuevo Registro")
    cat_seleccionada = st.selectbox("Categoría de Evaluación", EVALUATION_CATEGORIES, key="cat_reg")

    with st.form("f_reg_cliente", clear_on_submit=True):
        c1, c2 = st.columns(2)
        id_c = c1.text_input("ID Cliente (7 dígitos)", max_chars=7)
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
            if len(id_c) == 7 and nom:
                try:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    total = sum(scores.values())
                    client = get_gspread_client()
                    sh = client.open_by_key(SHEET_ID)

                    # Guardar en Hoja Principal
                    sh.worksheet(MAIN_WORKSHEET_NAME).append_row([now, cat_seleccionada, id_c, nom, suc, tip, total])
                    # Guardar en Hoja Detalle
                    sh.worksheet(EVALUATION_MAP[cat_seleccionada]["worksheet"]).append_row(
                        [now, id_c] + list(scores.values()))

                    st.success("¡Cliente registrado!")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Complete ID (7 dígitos) y Nombre.")
    st.link_button("📂 Acceder a Carpeta de Evidencias (Drive)",
                   "https://drive.google.com/drive/folders/1ojOeFXuiPof9R0qTL9BPeipig9pwOdzW?usp=sharing")

# --- TAB 2: MODIFICAR ---
with t2:
    df_m = load_data(MAIN_WORKSHEET_NAME)
    if not df_m.empty:
        df_m['LABEL'] = df_m['ID CLIENTE'].astype(str) + " - " + df_m['CLIENTE'].astype(str)
        choice = st.selectbox("Seleccione para editar", ["..."] + df_m['LABEL'].tolist())

        if choice != "...":
            sel_row = df_m[df_m['LABEL'] == choice].iloc[0]
            cat = sel_row['CATEGORÍA DE EVALUACIÓN']

            # Cargar datos de la hoja específica
            df_detail = load_data(EVALUATION_MAP[cat]["worksheet"])

            detail_match = df_detail[
                (df_detail['ID CLIENTE'].astype(str) == str(sel_row['ID CLIENTE'])) &
                (df_detail['FECHA Y HORA'].astype(str) == str(sel_row['FECHA Y HORA']))
                ]

            if not detail_match.empty:
                ev_row = detail_match.iloc[0]
                with st.form("f_mod_cliente"):
                    st.subheader(f"Editando: {sel_row['CLIENTE']}")
                    c1, c2 = st.columns(2)
                    new_nom = c1.text_input("Nombre", sel_row['CLIENTE'])
                    new_suc = c2.selectbox("Sucursal", BRANCHES, index=BRANCHES.index(sel_row['SUCURSAL']))

                    st.divider()
                    new_scores = {}
                    cols_ed = st.columns(2)

                    # AQUÍ ESTÁ LA CORRECCIÓN:
                    # Traemos nombre, puntaje máximo Y la descripción (desc)
                    for i, (name, max_s, desc) in enumerate(EVALUATION_MAP[cat]["items"]):
                        col_name = name.strip().upper()
                        val = int(ev_row.get(col_name, 0))

                        with cols_ed[i % 2]:
                            # Mostramos el Slider
                            new_scores[name] = st.slider(name, 0, max_s, val, key=f"mod_{i}")
                            # Agregamos el expander de ayuda igual que en el Registro
                            with st.expander("Ayuda"):
                                st.write(desc)

                    if st.form_submit_button("💾 Actualizar"):
                        # ... (el resto del código de guardado se mantiene igual)
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
                                        col_idx = headers.index(k.strip().upper()) + 1
                                        ws2.update_cell(idx2, col_idx, v)

                            st.success("¡Datos actualizados!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

    st.link_button("📂 Acceder a Carpeta de Evidencias (Drive)",
                   "https://drive.google.com/drive/folders/1ojOeFXuiPof9R0qTL9BPeipig9pwOdzW?usp=sharing")

# --- TAB 3: DASHBOARD ---
with t3:
    df_a = load_data(MAIN_WORKSHEET_NAME)
    if not df_a.empty:
        # Normalizamos nombres de columnas técnicos
        target = COL_PUNTAJE.upper()  # "PUNTAJE TOTAL SMARTFARM"
        col_cat = 'CATEGORÍA DE EVALUACIÓN'
        col_suc = 'SUCURSAL'
        META_CERTIFICACION = 105

        df_a[target] = pd.to_numeric(df_a[target], errors='coerce').fillna(0)

        # Filtros rápidos
        c1, c2 = st.columns(2)
        f_cat = c1.multiselect("Filtrar por Categorías", EVALUATION_CATEGORIES, default=EVALUATION_CATEGORIES)
        f_suc = c2.multiselect("Filtrar por Sucursales", BRANCHES, default=BRANCHES)

        df_f = df_a[df_a[col_cat].isin(f_cat) & df_a[col_suc].isin(f_suc)]

        if not df_f.empty:
            # 1. Gráfico de Ranking Individual
            st.plotly_chart(
                px.bar(df_f.sort_values(target, ascending=True),
                       x=target, y='CLIENTE', color=col_cat,
                       orientation='h', height=500,
                       title="🏆 Ranking Individual de Clientes"), use_container_width=True)

            st.divider()

            # --- ANÁLISIS POR CATEGORÍA ---
            st.subheader("📊 Análisis por Categoría")
            col_g1, col_g2 = st.columns(2)

            with col_g1:
                fig_pie = px.pie(df_f, names=col_cat, title="📦 Inscriptos por Categoría",
                                 hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_g2:
                stats_cat = df_f.groupby(col_cat)[target].agg(['sum', 'mean']).reset_index()
                stats_cat.columns = [col_cat, 'Puntaje Acumulado', 'Puntaje Promedio']
                fig_bar_cat = px.bar(stats_cat, x=col_cat, y=['Puntaje Acumulado', 'Puntaje Promedio'],
                                     barmode='group', title="📈 Rendimiento por Categoría")
                st.plotly_chart(fig_bar_cat, use_container_width=True)

            st.divider()

            # --- NUEVA SECCIÓN: DESEMPEÑO Y CERTIFICACIÓN POR SUCURSAL ---
            st.subheader("🏢 Desempeño y Certificación por Sucursal")

            # 1. Creamos una columna booleana para saber quién certificó
            df_f['CERTIFICA'] = df_f[target] >= META_CERTIFICACION

            # 2. Agrupamos y calculamos las métricas
            stats_suc = df_f.groupby(col_suc).agg(
                Cantidad_Inscriptos=(target, 'count'),
                Puntaje_Promedio=(target, 'mean'),
                Cant_Certificados=('CERTIFICA', 'sum')  # Suma los True como 1
            ).reset_index()

            # 3. Calculamos el % de certificación
            stats_suc['% Certificación'] = (
                        stats_suc['Cant_Certificados'] / stats_suc['Cantidad_Inscriptos'] * 100).round(1)

            # 4. Renombramos para la visualización final
            stats_suc.columns = [
                "Sucursal",
                "Clientes Inscriptos",
                "Promedio Pts",
                "Certificados (>=105 pts)",
                "% de Certificación"
            ]

            # 5. Mostramos la tabla con estilo de barra de progreso para el %
            st.dataframe(
                stats_suc.sort_values("% de Certificación", ascending=False),
                column_config={
                    "% de Certificación": st.column_config.ProgressColumn(
                        "% de Certificación",
                        help="Porcentaje de clientes que superan los 105 puntos",
                        format="%f%%",
                        min_value=0,
                        max_value=100,
                    ),
                    "Promedio Pts": st.column_config.NumberColumn(format="%.1f")
                },
                use_container_width=True,
                hide_index=True
            )

            # Métrica destacada de la red
            total_red = len(df_f)
            total_cert = df_f['CERTIFICA'].sum()
            porc_red = (total_cert / total_red * 100) if total_red > 0 else 0

            st.info(
                f"💡 **Estado de la Red:** Se han certificado **{total_cert}** de **{total_red}** clientes totales (**{porc_red:.1f}%** de efectividad).")

        else:
            st.info("No hay datos que coincidan con los filtros seleccionados.")
    else:
        st.info("Registre clientes para habilitar el panel de análisis.")

