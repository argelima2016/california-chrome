import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import osimport streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import re
import base64
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from pypdf import PdfReader
from streamlit_autorefresh import st_autorefresh

# Configuración de pantalla completa
st.set_page_config(page_title="WOLF READY TO RUN", layout="wide", page_icon="🐺")

# --- AUTOREFRESH (3 SEGUNDOS) ---
try:
    st_autorefresh(interval=3000, key="datarefresh_en_vivo")
except Exception:
    pass

# --- HORA LOCAL DE VENEZUELA ---
def obtener_hora_venezuela_local():
    try:
        zona_venezuela = ZoneInfo("America/Caracas")
        return datetime.now(zona_venezuela).replace(tzinfo=None)
    except Exception:
        pass
    tz_venezuela = timezone(timedelta(hours=-4))
    return datetime.now(tz_venezuela).replace(tzinfo=None)

# --- ESCALA DE PUJAS ---
ESCALA_PUJAS = [
    50, 100, 150, 200, 250, 300, 350, 400, 500, 600, 700, 800, 900, 1000,
    1200, 1400, 1600, 1800, 2000, 2500, 3000, 3500, 4000, 4500, 5000,
    5500, 6000, 6500, 7000, 7500, 8000, 8500, 9000, 9500, 10000
] + list(range(11000, 1000001, 1000))

def obtener_siguientes_montos(monto_actual):
    siguientes = [m for m in ESCALA_PUJAS if m > monto_actual]
    if not siguientes:
        ultimo = ESCALA_PUJAS[-1] if ESCALA_PUJAS else max(monto_actual, 10000)
        siguientes = [ultimo + i * 1000 for i in range(1, 50)]
    return siguientes

# --- LECTOR DE LOGOTIPO LOCAL ---
def get_image_base64(nombres_posibles):
    ruta_directorio = os.path.dirname(os.path.abspath(__file__))
    for nombre_archivo in nombres_posibles:
        try:
            ruta_imagen = os.path.join(ruta_directorio, nombre_archivo)
            if os.path.exists(ruta_imagen):
                with open(ruta_imagen, "rb") as img_file:
                    return base64.b64encode(img_file.read()).decode('utf-8')
        except Exception:
            continue
    return ""

nombres_archivos = [
    "1001394095_preview_rev_1_2.png",
    "1001394095_preview_rev_1_2.jpg",
    "logo.png",
    "logo.jpg"
]

img_b64 = get_image_base64(nombres_archivos)

if img_b64:
    logo_display = f'<img src="data:image/png;base64,{img_b64}" class="header-logo-img" />'
else:
    logo_display = '<span style="color: #f1c40f; font-size: 16px; font-weight: 900; font-style: italic;">WOLF READY TO RUN</span>'

ahora_dt = obtener_hora_venezuela_local()
fecha_hora_texto = ahora_dt.strftime('%d/%m/%Y - %I:%M:%S %p')

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stApp {
        background-color: #080a0f;
        color: #f0f6fc;
    }
    div[data-testid="stTabs"] {
        display: none !important;
    }
    .header-container {
        background: linear-gradient(180deg, #000000 0%, #11141d 100%) !important;
        width: 100% !important;
        padding: 8px 12px !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        border-bottom: 2px solid #21262d !important;
        margin: -1rem -1rem 0 -1rem !important;
        box-sizing: border-box !important;
        gap: 6px;
    }
    .header-top-row {
        width: 100% !important;
        display: flex !important;
        flex-direction: row !important;
        justify-content: space-between !important;
        align-items: center !important;
    }
    .menu-icon-box {
        background-color: #161b22 !important;
        color: #f1c40f !important;
        font-size: 18px !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
        padding: 4px 10px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    .header-logo-img {
        max-height: 40px !important;
        width: auto !important;
        object-fit: contain !important;
        display: block !important;
    }
    .top-clock-pill {
        background: #0d1117;
        border: 1px solid #30363d;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11px;
        color: #58a6ff;
        font-weight: 700;
        text-align: center;
        letter-spacing: 0.3px;
    }
    .user-info-container {
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        padding: 4px 10px !important;
        border-radius: 20px !important;
    }
    .user-text-info {
        display: flex !important;
        flex-direction: column !important;
        text-align: right !important;
        line-height: 1.1 !important;
    }
    .user-name {
        color: #ffffff !important;
        font-size: 11px !important;
        font-weight: 900 !important;
    }
    .user-balance {
        color: #58a6ff !important;
        font-size: 11px !important;
        font-weight: 800 !important;
    }
    .user-avatar {
        background-color: #f1c40f !important;
        color: #000000 !important;
        border-radius: 50% !important;
        width: 26px !important;
        height: 26px !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        font-size: 12px !important;
        font-weight: bold !important;
    }
    .block-container {
        padding-top: 0.6rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }
    .stButton button {
        width: 100% !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        padding: 0.3rem 0.4rem !important;
        min-height: 38px !important;
        font-size: 11px !important;
        letter-spacing: 0.3px;
        white-space: nowrap !important;
    }
    .subasta-header {
        font-size: clamp(16px, 4vw, 20px);
        font-weight: 800;
        color: #f1e05a;
        margin-bottom: 4px;
        border-bottom: 2px solid #f1e05a;
        padding-bottom: 4px;
    }
    .timer-box {
        background-color: #161b22;
        border: 2px solid #ff4757;
        padding: 8px;
        border-radius: 8px;
        text-align: center;
        font-size: clamp(14px, 3.5vw, 18px);
        font-weight: bold;
        color: #ff4757;
        margin-bottom: 10px;
    }
    .cierre-info-box {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 6px;
        border-radius: 6px;
        text-align: center;
        font-size: 13px;
        color: #f0f6fc;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- CABECERA SUPERIOR MÓVIL ESTÉTICA ---
st.markdown(f"""
    <div class="header-container">
        <div class="header-top-row">
            <div class="menu-icon-box">☰</div>
            <div style="display: flex; align-items: center; justify-content: center; overflow: hidden; padding: 0 4px;">
                {logo_display}
            </div>
            <div class="user-info-container">
                <span style="color: #f1c40f !important; font-size: 16px !important;">🛢️</span>
                <div class="user-text-info">
                    <span class="user-name">ADMIN</span>
                    <span class="user-balance">Bs. 50k</span>
                </div>
                <div class="user-avatar">👤</div>
            </div>
        </div>
        <div class="top-clock-pill">
            <span>🕒</span> <b>{fecha_hora_texto}</b>
        </div>
    </div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- JUGADORES BASE ---
@st.cache_data
def cargar_jugadores_base():
    return ["CASA", "SOMBI", "LUIS", "CARLOS", "RAMON", "ALDEA", "ANGEL", "ALFONSO", "MACANO", "MIGUEL", "TOCAYO", "EL GOCHO", "PAPIRO", "CHAYO", "ALEXIS"]

# --- INICIALIZACIÓN GLOBAL DE ESTADOS ---
def inicializar_estado_global():
    if 'menu_principal_opcion' not in st.session_state:
        st.session_state.menu_principal_opcion = "Remates"
    if 'lista_jugadores' not in st.session_state:
        st.session_state.lista_jugadores = cargar_jugadores_base()
    if 'banco_caballos_por_carrera' not in st.session_state:
        st.session_state.banco_caballos_por_carrera = {}
    if 'remates' not in st.session_state:
        st.session_state.remates = {}
    if 'historial_ganadores' not in st.session_state:
        st.session_state.historial_ganadores = {}
    if 'carreras_cerradas_remate' not in st.session_state:
        st.session_state.carreras_cerradas_remate = {}
    if 'remates_cargados_en_cuentas' not in st.session_state:
        st.session_state.remates_cargados_en_cuentas = {}
    if 'fechas_horas_cierre_remate' not in st.session_state:
        st.session_state.fechas_horas_cierre_remate = {}
    if 'estado_conteo_carrera' not in st.session_state:
        st.session_state.estado_conteo_carrera = {}
    if 'tiempo_inicio_conteo' not in st.session_state:
        st.session_state.tiempo_inicio_conteo = {}
    if 'cuentas' not in st.session_state:
        st.session_state.cuentas = {j: {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0} for j in st.session_state.lista_jugadores}
    if 'ganancia_casa' not in st.session_state:
        st.session_state.ganancia_casa = 0.0
    if 'historial_transacciones' not in st.session_state:
        st.session_state.historial_transacciones = []
    if 'dupletas_tickets' not in st.session_state:
        st.session_state.dupletas_tickets = []
    if 'carreras_habilitadas_dupleta' not in st.session_state:
        st.session_state.carreras_habilitadas_dupleta = []
    if 'dupleta_bloqueada' not in st.session_state:
        st.session_state.dupleta_bloqueada = False
    if 'carreras_activas_remate' not in st.session_state:
        st.session_state.carreras_activas_remate = []
    if 'programa_pdf_bytes' not in st.session_state:
        st.session_state.programa_pdf_bytes = None
    if 'programa_pdf_nombre' not in st.session_state:
        st.session_state.programa_pdf_nombre = None
    if 'texto_completo_pdf' not in st.session_state:
        st.session_state.texto_completo_pdf = ""
    if 'imagenes_carreras' not in st.session_state:
        st.session_state.imagenes_carreras = {}

inicializar_estado_global()

def formatear_bs(monto):
    numero_formateado = f"{monto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"Bs. {numero_formateado}"

def obtener_abreviatura_carrera(nombre_carrera):
    match = re.search(r'\d+', nombre_carrera)
    if match:
        return f"C{match.group(0)}"
    return nombre_carrera[:3].upper()

def generar_tabla_html_remate(remates_dict):
    html = """
    <style>
        .tabla-referencia {
            width: 100%;
            border-collapse: collapse;
            font-family: sans-serif;
            background-color: #ffffff;
            color: #000000;
            margin-bottom: 15px;
        }
        .tabla-referencia th {
            border-top: 3px solid #dfc729;
            border-bottom: 2px solid #dfc729;
            padding: 8px 4px;
            text-align: left;
            font-weight: 800;
            background-color: #ffffff;
            color: #000000;
            font-size: 13px;
        }
        .tabla-referencia td {
            border-bottom: 1px solid #dfc729;
            padding: 6px 4px;
            background-color: #fbfbfb;
            color: #111111;
            font-size: 12px;
            vertical-align: middle;
        }
        .badge-numero {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 22px;
            height: 22px;
            font-weight: bold;
            font-size: 12px;
            border-radius: 2px;
            box-sizing: border-box;
        }
        .badge-1 { background-color: #e3242b; color: #ffffff; }
        .badge-2 { background-color: #ffffff; color: #000000; border: 2px solid #000000; }
        .badge-3 { background-color: #1d11c0; color: #ffffff; }
        .badge-4 { background-color: #f1c40f; color: #000000; }
        .badge-5 { background-color: #28a745; color: #ffffff; }
        .badge-6 { background-color: #000000; color: #ffffff; }
        .badge-7 { background-color: #fd7e14; color: #ffffff; }
        .badge-default { background-color: #6c757d; color: #ffffff; }
    </style>
    <div style="background-color: #ffffff; padding: 4px; border-radius: 8px; overflow-x: auto;">
        <table class="tabla-referencia">
            <thead>
                <tr>
                    <th style="width: 8%;">No</th>
                    <th style="width: 37%;">Ejemplar</th>
                    <th style="width: 27%;">Comprador</th>
                    <th style="width: 28%;">Monto Actual</th>
                </tr>
            </thead>
            <tbody>
    """
    for cab, info in remates_dict.items():
        match_num = re.match(r'^(\d+)', cab)
        if match_num:
            num = int(match_num.group(1))
            nombre_solo = cab.split(" - ", 1)[1] if " - " in cab else cab
        else:
            num = 0
            nombre_solo = cab
            
        if num == 1: badge_class = "badge-1"
        elif num == 2: badge_class = "badge-2"
        elif num == 3: badge_class = "badge-3"
        elif num == 4: badge_class = "badge-4"
        elif num == 5: badge_class = "badge-5"
        elif num == 6: badge_class = "badge-6"
        elif num == 7: badge_class = "badge-7"
        else: badge_class = "badge-default"
        
        html += f"""
                <tr>
                    <td><span class="badge-numero {badge_class}">{num}</span></td>
                    <td style="font-weight: 800; font-size: 13px;">{nombre_solo.upper()}</td>
                    <td>{info['jugador']}</td>
                    <td style="font-weight: bold; color: #000000;">{formatear_bs(info['monto'])}</td>
                </tr>
        """
    html += """
            </tbody>
        </table>
    </div>
    """
    return html

def extraer_texto_pdf(archivo_pdf):
    try:
        bytes_data = archivo_pdf.getvalue()
        st.session_state.programa_pdf_bytes = bytes_data
        st.session_state.programa_pdf_nombre = getattr(archivo_pdf, "name", "Inscritos_Semana.pdf")
        lector_pdf = PdfReader(archivo_pdf)
        texto_extraido = ""
        for pagina in lector_pdf.pages:
            t_pag = pagina.extract_text()
            if t_pag:
                texto_extraido += t_pag + "\n"
        st.session_state.texto_completo_pdf = texto_extraido
        return True
    except Exception as e:
        st.sidebar.error(f"Error al leer PDF: {e}")
    return False

def procesar_texto_para_remates(texto_a_procesar):
    try:
        lineas = texto_a_procesar.split('\n')
        carrera_actual_detectada = None
        banco_temporal = {}
        patron_carrera = re.compile(
            r'(?:carrera|primera|segunda|tercera|cuarta|quinta|sexta|septima|octava|novena|decima|\d+)\s*(?:ª|º|\.)?\s*carrera', 
            re.IGNORECASE
        )
        for linea in lineas:
            linea_limpia = linea.strip()
            if not linea_limpia:
                continue
            match_carr = patron_carrera.search(linea_limpia)
            if match_carr or ("carrera" in linea_limpia.lower() and len(linea_limpia) < 35):
                for c_n in range(1, 15):
                    if str(c_n) in linea_limpia or f"carrera {c_n}" in linea_limpia.lower() or f"{c_n}ra" in linea_limpia.lower() or f"{c_n}da" in linea_limpia.lower() or f"{c_n}ta" in linea_limpia.lower():
                        carrera_actual_detectada = f"Carrera {c_n}"
                        if carrera_actual_detectada not in banco_temporal:
                            banco_temporal[carrera_actual_detectada] = []
                        break
            if carrera_actual_detectada:
                match_ejemplar = re.match(r'^(?:[Pp][Oo][Ss]\.?\s*)?(\d{1,2})[\s\-\.\)]+(.+)', linea_limpia)
                if match_ejemplar:
                    num_pos = int(match_ejemplar.group(1))
                    nom_ej = match_ejemplar.group(2).strip()
                    palabras_excluir = ['retirado', 'jinete', 'entrenador', 'distancia', 'premio', 'propietario', 'condicion', 'hipodromo', 'metros', 'haras', 'stud', 'aprox']
                    if 1 <= num_pos <= 25 and len(nom_ej) > 1 and not any(p in nom_ej.lower() for p in palabras_excluir):
                        formato_ej = f"{num_pos} - {nom_ej.title()}"
                        if formato_ej not in banco_temporal[carrera_actual_detectada]:
                            banco_temporal[carrera_actual_detectada].append(formato_ej)

        if banco_temporal:
            for c_key in banco_temporal:
                banco_temporal[c_key].sort(key=lambda x: int(re.match(r'^(\d+)', x).group(1)))
            st.session_state.banco_caballos_por_carrera = banco_temporal
            for c_key, c_vals in banco_temporal.items():
                if c_key not in st.session_state.remates:
                    st.session_state.remates[c_key] = {}
                for ev in c_vals:
                    if ev not in st.session_state.remates[c_key]:
                        st.session_state.remates[c_key][ev] = {"jugador": "Sin Postor", "monto": 0.0}
            todas_carr = list(banco_temporal.keys())
            st.session_state.carreras_activas_remate = list(todas_carr)
            st.session_state.carreras_habilitadas_dupleta = list(todas_carr)
            return True
    except Exception as e:
        st.error(f"Error procesando el segmento: {e}")
    return False

if not st.session_state.remates:
    for i in range(1, 11):
        carr_nombre = f"Carrera {i}"
        st.session_state.banco_caballos_por_carrera[carr_nombre] = [f"{j} - Ejemplar {j}" for j in range(1, 11)]
        st.session_state.remates[carr_nombre] = {f"{j} - Ejemplar {j}": {"jugador": "Sin Postor", "monto": 0.0} for j in range(1, 11)}

lista_carreras_disponibles = list(st.session_state.remates.keys())

if not st.session_state.carreras_activas_remate and lista_carreras_disponibles:
    st.session_state.carreras_activas_remate = list(lista_carreras_disponibles)

if not st.session_state.carreras_habilitadas_dupleta and lista_carreras_disponibles:
    st.session_state.carreras_habilitadas_dupleta = list(lista_carreras_disponibles)

# --- MENÚ PRINCIPAL HORIZONTAL ---
col_menu1, col_menu2, col_menu3, col_menu4 = st.columns(4, gap="small")

with col_menu1:
    if st.button("🔒 ADMIN", key="menu_btn_admin_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "🔒 Zona Admin" else "secondary"):
        st.session_state.menu_principal_opcion = "🔒 Zona Admin"
        st.rerun()

with col_menu2:
    if st.button("🏇 REMATES", key="menu_btn_remates_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Remates" else "secondary"):
        st.session_state.menu_principal_opcion = "Remates"
        st.rerun()

with col_menu3:
    if st.button("🎟️ DUPLETAS", key="menu_btn_dupletas_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Dupletas" else "secondary"):
        st.session_state.menu_principal_opcion = "Dupletas"
        st.rerun()

with col_menu4:
    if st.button("📊 CUENTAS", key="menu_btn_cuentas_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Cuentas" else "secondary"):
        st.session_state.menu_principal_opcion = "Cuentas"
        st.rerun()

st.markdown("<hr style='margin: 0.8rem 0; border-color: #21262d;'>", unsafe_allow_html=True)

# --- BARRA LATERAL ---
st.sidebar.header("barra lateral")
ahora_dt = obtener_hora_venezuela_local()
st.sidebar.markdown(f"🕒 **Hora:** `{ahora_dt.strftime('%I:%M:%S %p')}`")

with st.sidebar.expander("⚡ Carreras Activas para Remate", expanded=True):
    carreras_seleccionadas_activas = st.multiselect(
        "Carreras Activas",
        options=lista_carreras_disponibles,
        default=[c for c in st.session_state.carreras_activas_remate if c in lista_carreras_disponibles],
        key="sb_multiselect_carreras_activas"
    )
    if carreras_seleccionadas_activas != st.session_state.carreras_activas_remate:
        st.session_state.carreras_activas_remate = carreras_seleccionadas_activas
        st.rerun()

with st.sidebar.expander("🏠 Retención de la Casa", expanded=False):
    porcentaje_casa = st.slider("Retención (%)", 0, 50, 30, key="sb_slider_retencion_casa")

with st.sidebar.expander("📅⏰ Cierres Estrictos por Carrera", expanded=False):
    carrera_config_sel = st.selectbox("Seleccionar Carrera", lista_carreras_disponibles, key="sb_selector_carrera_config")
    fecha_sel = st.date_input("Fecha de Cierre", value=ahora_dt.date(), key=f"sb_sel_f_{carrera_config_sel}")
    periodo_sel = st.radio("Periodo", ["AM", "PM"], key=f"sb_radio_p_{carrera_config_sel}", horizontal=True)
    hora_12 = st.selectbox("Hora", list(range(1, 13)), key=f"sb_sel_h_{carrera_config_sel}")
    minuto_sel = st.selectbox("Minutos", list(range(0, 60)), key=f"sb_sel_m_{carrera_config_sel}")
    
    h_24_conv = int(hora_12)
    if periodo_sel == "PM" and h_24_conv < 12: h_24_conv += 12
    elif periodo_sel == "AM" and h_24_conv == 12: h_24_conv = 0
    
    hora_seleccionada = time(h_24_conv, int(minuto_sel))
    dt_cierre_completo = datetime.combine(fecha_sel, hora_seleccionada)
    
    col_bh1, col_bh2 = st.sidebar.columns(2)
    with col_bh1:
        if st.button("💾 Guardar", key=f"sb_btn_guardar_cierre_{carrera_config_sel}"):
            st.session_state.fechas_horas_cierre_remate[carrera_config_sel] = dt_cierre_completo
            st.session_state.estado_conteo_carrera[carrera_config_sel] = "INACTIVO"
            st.toast(f"✅ Cierre guardado para {carrera_config_sel}")
            st.rerun()
    with col_bh2:
        if st.button("🗑️ Borrar", key=f"sb_btn_borrar_cierre_{carrera_config_sel}"):
            if carrera_config_sel in st.session_state.fechas_horas_cierre_remate:
                del st.session_state.fechas_horas_cierre_remate[carrera_config_sel]
            st.session_state.estado_conteo_carrera[carrera_config_sel] = "INACTIVO"
            st.toast("🗑️ Cierre removido")
            st.rerun()

with st.sidebar.expander("🔒 Estado Dupletas", expanded=False):
    if st.session_state.dupleta_bloqueada:
        st.markdown("<p style='color: #ff4757; font-weight: bold;'>🔴 BLOQUEADAS</p>", unsafe_allow_html=True)
        if st.button("🔓 Desbloquear", key="sb_btn_desbloquear_dupleta"):
            st.session_state.dupleta_bloqueada = False
            st.rerun()
    else:
        st.markdown("<p style='color: #00d2d3; font-weight: bold;'>🟢 ABIERTAS</p>", unsafe_allow_html=True)
        if st.button("🔒 Bloquear", key="sb_btn_bloquear_dupleta"):
            st.session_state.dupleta_bloqueada = True
            st.rerun()

if st.sidebar.button("🗑️ Reiniciar Jornada", key="sb_btn_reiniciar_jornada", use_container_width=True):
    for key in list(st.session_state.keys()):
        if key != 'banco_caballos_por_carrera':
            del st.session_state[key]
    st.toast("🚨 Jornada reiniciada.")
    st.rerun()

menu_principal_opcion = st.session_state.menu_principal_opcion

# =========================================================================
# 1. MÓDULO DE REMATES
# =========================================================================
if menu_principal_opcion == "Remates":
    if not lista_carreras_disponibles:
        st.warning("⚠️ No hay carreras cargadas en el sistema.")
    else:
        carreras_filtradas_visibles = [
            c for c in lista_carreras_disponibles 
            if (c in st.session_state.carreras_activas_remate) or st.session_state.carreras_cerradas_remate.get(c, False)
        ]
        
        if not carreras_filtradas_visibles:
            st.info("ℹ️ No hay carreras activas ni cerradas para mostrar. Selecciona carreras en el menú lateral.")
        else:
            if "carrera_remate_activa_seleccionada" not in st.session_state or st.session_state["carrera_remate_activa_seleccionada"] not in carreras_filtradas_visibles:
                carr_activa = carreras_filtradas_visibles[0]
                st.session_state["carrera_remate_activa_seleccionada"] = carr_activa
            else:
                carr_activa = st.session_state["carrera_remate_activa_seleccionada"]

            st.markdown("🔹 **Seleccionar Carrera:**")
            cols_carreras = st.columns(len(carreras_filtradas_visibles))
            for idx, c_nombre in enumerate(carreras_filtradas_visibles):
                abreviatura = obtener_abreviatura_carrera(c_nombre)
                es_activa = (c_nombre == carr_activa)
                with cols_carreras[idx]:
                    if st.button(abreviatura, key=f"rem_btn_sel_carr_{idx}", use_container_width=True, type="primary" if es_activa else "secondary"):
                        st.session_state["carrera_remate_activa_seleccionada"] = c_nombre
                        st.rerun()

            st.markdown(f"---")

            # --- RENDERIZAR IMAGEN DE LA CARRERA SI EXISTE ---
            if carr_activa in st.session_state.imagenes_carreras:
                st.image(st.session_state.imagenes_carreras[carr_activa], caption=f"Imagen oficial - {carr_activa}", use_container_width=True)

            carrera_cerrada = st.session_state.carreras_cerradas_remate.get(carr_activa, False)
            if carrera_cerrada:
                st.error(f"🔴 La carrera **{carr_activa}** se encuentra **CERRADA** para nuevas pujas.")
            else:
                st.success(f"🟢 Panel activo y abierto para: **{carr_activa}**")

            st.markdown(f"### 🏁 {carr_activa}")
            dt_limite = st.session_state.fechas_horas_cierre_remate.get(carr_activa)
            estado_conteo = st.session_state.estado_conteo_carrera.get(carr_activa, "INACTIVO")
            
            if dt_limite:
                st.markdown(f"<div class='cierre-info-box'>⏰ Cierre Estricto: <b>{dt_limite.strftime('%d/%m/%Y - %I:%M %p')}</b></div>", unsafe_allow_html=True)

            if dt_limite and not carrera_cerrada:
                diferencia_segundos = (dt_limite - ahora_dt).total_seconds()
                if estado_conteo == "INACTIVO":
                    if 0 < diferencia_segundos <= 10:
                        st.session_state.estado_conteo_carrera[carr_activa] = "CONTEO_10S"
                        st.session_state.tiempo_inicio_conteo[carr_activa] = ahora_dt
                        st.rerun()
                    elif diferencia_segundos <= 0:
                        st.session_state.carreras_cerradas_remate[carr_activa] = True
                        st.session_state.estado_conteo_carrera[carr_activa] = "CERRADO"
                        st.rerun()
                elif estado_conteo == "CONTEO_10S":
                    tiempo_inicio = st.session_state.tiempo_inicio_conteo.get(carr_activa, ahora_dt)
                    transcurridos = (ahora_dt - tiempo_inicio).total_seconds()
                    if transcurridos >= 12:
                        st.session_state.carreras_cerradas_remate[carr_activa] = True
                        st.session_state.estado_conteo_carrera[carr_activa] = "CERRADO"
                        st.rerun()
                    else:
                        restantes_10s = max(0, 10 - int(transcurridos))
                        if restantes_10s > 0:
                            st.markdown(f"<div class='timer-box'>⚠️ CIERRE EN: <b>{restantes_10s}s</b> ({carr_activa})</div>", unsafe_allow_html=True)

            tabla_html = generar_tabla_html_remate(st.session_state.remates[carr_activa])
            cantidad_filas = len(st.session_state.remates[carr_activa])
            altura_dinamica = min(max(180, (cantidad_filas * 45) + 80), 550)
            components.html(tabla_html, height=altura_dinamica, scrolling=True)
            
            total_pote = sum([info['monto'] for info in st.session_state.remates[carr_activa].values()])
            monto_casa = total_pote * (porcentaje_casa / 100)
            pote_neto_base = total_pote - monto_casa

            c_m1, c_m2 = st.columns(2)
            c_m1.metric(f"💰 Pote ({carr_activa})", formatear_bs(total_pote))
            pote_incentivo_extra = c_m2.number_input("🎁 Extra", min_value=0.0, value=0.0, step=50.0, key=f"rem_pote_inc_{carr_activa}")
            premio_total_calculado = pote_neto_base + pote_incentivo_extra
            st.metric(f"🏆 Premio Total ({carr_activa})", formatear_bs(premio_total_calculado))

            with st.container(border=True):
                st.markdown(f"⚡ **Registro Rápido de Puja - {carr_activa}**")
                lista_caballos_activos = list(st.session_state.remates[carr_activa].keys())
                
                if not lista_caballos_activos:
                    st.warning("Sin ejemplares inscritos en esta carrera.")
                else:
                    k_sel_cab = f"rem_caballo_activo_click_{carr_activa}"
                    if k_sel_cab not in st.session_state or st.session_state[k_sel_cab] not in lista_caballos_activos:
                        st.session_state[k_sel_cab] = lista_caballos_activos[0]
                        
                    st.markdown(f"🔹 **1. Seleccionar Ejemplar (Total inscritos: {len(lista_caballos_activos)}):**")
                    cantidad_ejemplares = len(lista_caballos_activos)
                    cols_ejemplares = min(4, cantidad_ejemplares) if cantidad_ejemplares > 0 else 1
                    num_filas = (cantidad_ejemplares + cols_ejemplares - 1) // cols_ejemplares
                    
                    idx_cab = 0
                    for f in range(num_filas):
                        cols_fila = st.columns(cols_ejemplares)
                        for c in range(cols_ejemplares):
                            if idx_cab < cantidad_ejemplares:
                                cab_item = lista_caballos_activos[idx_cab]
                                num_parte = cab_item.split(" - ")[0]
                                with cols_fila[c]:
                                    if st.button(f"#{num_parte}", key=f"rem_btn_cab_{carr_activa}_{idx_cab}", use_container_width=True):
                                        st.session_state[k_sel_cab] = cab_item
                                idx_cab += 1
                    
                    caballo_seleccionado = st.session_state[k_sel_cab]
                    st.info(f"Ejemplar activo en {carr_activa}: **{caballo_seleccionado}**")

                    puja_actual = st.session_state.remates[carr_activa][caballo_seleccionado]['monto']
                    opciones_escala = obtener_siguientes_montos(puja_actual)
                    monto_puja = st.selectbox("💰 **2. Monto de Puja**", opciones_escala, format_func=lambda x: formatear_bs(x), key=f"rem_sel_monto_{carr_activa}_{caballo_seleccionado}")
                    
                    if carrera_cerrada:
                        st.button(f"🔨 Confirmar Puja ({carr_activa})", key=f"rem_btn_confirmar_{carr_activa}", use_container_width=True, type="primary", disabled=True)
                    else:
                        if st.button(f"🔨 Confirmar Puja ({carr_activa})", key=f"rem_btn_confirmar_{carr_activa}", use_container_width=True, type="primary"):
                            if monto_puja <= puja_actual:
                                st.error("El monto debe ser mayor a la puja actual.")
                            else:
                                st.session_state.remates[carr_activa][caballo_seleccionado] = {"jugador": "Sin Postor", "monto": monto_puja}
                                if estado_conteo == "CONTEO_10S":
                                    st.session_state.tiempo_inicio_conteo[carr_activa] = obtener_hora_venezuela_local()
                                st.success("✅ ¡Puja registrada correctamente y conteo reiniciado!")
                                st.rerun()

# =========================================================================
# 2. MÓDULO DE DUPLETAS (Con bloqueo de combinaciones iguales y visualizador)
# =========================================================================
elif menu_principal_opcion == "Dupletas":
    st.markdown("<div class='subasta-header'>🎟️ Módulo de Dupletas</div>", unsafe_allow_html=True)
    if st.session_state.dupleta_bloqueada:
        st.error("🔒 **BLOQUEADO:** Emisión cerrada.")

    pote_total_dupletas = sum([t['monto'] for t in st.session_state.dupletas_tickets])
    st.metric("💰 Pote Acumulado Dupletas", formatear_bs(pote_total_dupletas))

    with st.container(border=True):
        jugador_dupleta = st.selectbox("👤 Jugador", st.session_state.lista_jugadores, key="dup_input_jugador")
        monto_dupleta = st.number_input("💰 Monto (Bs.)", min_value=50.0, value=500.0, step=50.0, key="dup_input_monto")
        num_legs = st.radio("Cantidad de Selecciones:", [2, 3, 4, 5, 6], horizontal=True, key="dup_radio_legs")

    with st.container(border=True):
        seleccion_legs = []
        carreras_usadas_en_ticket = set()
        valido_legs = True
        carreras_habilitadas = st.session_state.carreras_habilitadas_dupleta
        
        for i in range(num_legs):
            c_leg, cb_leg_col = st.columns(2)
            with c_leg:
                carr_leg = st.selectbox(f"Carrera {i+1}", carreras_habilitadas, key=f"dup_sel_carrera_{i}")
                # Mostrar imagen de la carrera si se cargó previamente
                if carr_leg in st.session_state.imagenes_carreras:
                    st.image(st.session_state.imagenes_carreras[carr_leg], width=120)
            with cb_leg_col:
                caballos_in_carr = list(st.session_state.remates.get(carr_leg, {}).keys())
                cab_leg = st.selectbox(f"Ejemplar {i+1}", caballos_in_carr if caballos_in_carr else ["Sin Caballos"], key=f"dup_sel_ejemplar_{i}")
            
            if carr_leg in carreras_usadas_en_ticket:
                valido_legs = False
            carreras_usadas_en_ticket.add(carr_leg)
            seleccion_legs.append({"carrera": carr_leg, "ejemplar": cab_leg})

    if not st.session_state.dupleta_bloqueada:
        if st.button("🚀 Emitir Ticket de Dupleta", key="dup_btn_emitir", use_container_width=True, type="primary"):
            if not valido_legs:
                st.error("⚠️ No puedes repetir carreras en el mismo ticket.")
            else:
                # Ordenar las selecciones por nombre de carrera para que la combinación sea única sin importar el orden en que se seleccionaron
                legs_ordenadas = sorted(seleccion_legs, key=lambda x: x['carrera'])
                firma_combinacion = tuple((l['carrera'], l['ejemplar']) for l in legs_ordenadas)

                # Comprobar si ya existe un ticket exactamente igual
                duplicado = False
                for t in st.session_state.dupletas_tickets:
                    t_legs_ordenadas = sorted(t['legs'], key=lambda x: x['carrera'])
                    t_firma = tuple((l['carrera'], l['ejemplar']) for l in t_legs_ordenadas)
                    if t_firma == firma_combinacion:
                        duplicado = True
                        break

                if duplicado:
                    st.error("❌ **BLOQUEADO:** Ya existe un ticket con exactamente esta misma combinación de ejemplares y carreras. No se permiten combinaciones repetidas.")
                else:
                    ticket_id = f"DUP-{len(st.session_state.dupletas_tickets) + 1:04d}"
                    st.session_state.dupletas_tickets.append({
                        "id": ticket_id, "jugador": jugador_dupleta, "monto": monto_dupleta,
                        "legs": seleccion_legs, "estado": "Pendiente", "fecha": ahora_dt.strftime('%d/%m %I:%M %p')
                    })
                    if jugador_dupleta not in st.session_state.cuentas:
                        st.session_state.cuentas[jugador_dupleta] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                    st.session_state.cuentas[jugador_dupleta]['Pujas'] += monto_dupleta
                    st.success(f"✅ ¡Ticket {ticket_id} emitido con éxito!")
                    st.rerun()

    # --- SECCIÓN: VISUALIZADOR DE TICKETS EMITIDOS ---
    st.markdown("---")
    st.markdown("### 📋 Tickets de Dupletas Emitidos en la Jornada")
    if not st.session_state.dupletas_tickets:
        st.info("No hay tickets emitidos todavía.")
    else:
        for t in reversed(st.session_state.dupletas_tickets):
            with st.container(border=True):
                col_t1, col_t2, col_t3 = st.columns([2, 2, 2])
                col_t1.markdown(f"🏷️ **Ticket:** `{t['id']}`")
                col_t2.markdown(f"👤 **Jugador:** `{t['jugador']}`")
                col_t3.markdown(f"💰 **Monto:** `{formatear_bs(t['monto'])}`")
                
                st.markdown("🔍 **Selecciones:**")
                detalles_legs = " ➔ ".join([f"**{l['carrera']}**: {l['ejemplar']}" for l in t['legs']])
                st.markdown(f"> {detalles_legs}")
                st.caption(f"Emitido el: {t['fecha']}")

# =========================================================================
# 3. MÓDULO DE CUENTAS
# =========================================================================
elif menu_principal_opcion == "Cuentas":
    st.markdown("<div class='subasta-header'>📊 Cuentas y Balances</div>", unsafe_allow_html=True)
    datos_cuentas = []
    tot_pujas_gen = 0.0
    for jugador, vals in st.session_state.cuentas.items():
        pujas, premios, abonos = vals['Pujas'], vals['Premios'], vals['Abonos']
        balance_neto = pujas - abonos - premios
        tot_pujas_gen += pujas
        datos_cuentas.append({"Jugador": jugador, "Compras": formatear_bs(pujas), "Premios": formatear_bs(premios), "Neto": formatear_bs(balance_neto)})
    st.dataframe(pd.DataFrame(datos_cuentas), use_container_width=True, hide_index=True)
    st.metric("Ganancia Casa", formatear_bs(st.session_state.ganancia_casa))

# =========================================================================
# 4. ZONA DE ADMINISTRADOR
# =========================================================================
elif menu_principal_opcion == "🔒 Zona Admin":
    st.markdown("<div class='subasta-header'>🔒 Zona de Administrador</div>", unsafe_allow_html=True)
    sub_banco, sub_cierre, sub_hist, sub_pdf, sub_img = st.tabs(["✍️ Banco", "🏁 Cierre", "🧾 Historial", "📄 PDF", "🖼️ Imágenes Carrera"])
    
    with sub_banco:
        st.markdown("### ✍️ Banco de Caballos por Carrera")
        carr_banco_sel = st.selectbox("Seleccionar Carrera", lista_carreras_disponibles, key="adm_banco_sel_carrera")
        
        if carr_banco_sel not in st.session_state.banco_caballos_por_carrera:
            st.session_state.banco_caballos_por_carrera[carr_banco_sel] = []
            
        with st.container(border=True):
            nuevo_nom_banco = st.text_input("Nombre del Ejemplar", placeholder="Ej: Rey David", key=f"adm_banco_input_{carr_banco_sel}")
            if st.button("💾 Agregar al Banco", key=f"adm_banco_btn_add_{carr_banco_sel}", use_container_width=True, type="primary"):
                nom_limp = nuevo_nom_banco.strip().title()
                if nom_limp:
                    nums = [int(re.match(r'^(\d+)', e).group(1)) for e in st.session_state.banco_caballos_por_carrera[carr_banco_sel] if re.match(r'^(\d+)', e)]
                    sig_num = 1
                    while sig_num in nums and sig_num <= 25: sig_num += 1
                    formato_nuevo = f"{sig_num} - {nom_limp}"
                    
                    if formato_nuevo not in st.session_state.banco_caballos_por_carrera[carr_banco_sel]:
                        st.session_state.banco_caballos_por_carrera[carr_banco_sel].append(formato_nuevo)
                        st.session_state.banco_caballos_por_carrera[carr_banco_sel].sort(key=lambda x: int(re.match(r'^(\d+)', x).group(1)))

                    if carr_banco_sel not in st.session_state.remates:
                        st.session_state.remates[carr_banco_sel] = {}
                    if formato_nuevo not in st.session_state.remates[carr_banco_sel]:
                        st.session_state.remates[carr_banco_sel][formato_nuevo] = {"jugador": "Sin Postor", "monto": 0.0}
                    st.toast("✅ ¡Agregado con éxito y ordenado por posición!")
                    st.rerun()

        for idx_b, ej_item in enumerate(st.session_state.banco_caballos_por_carrera[carr_banco_sel]):
            col_ib1, col_ib2 = st.columns([5, 1])
            with col_ib1: st.text(ej_item)
            with col_ib2:
                if st.button("🗑️", key=f"adm_banco_del_{carr_banco_sel}_{idx_b}", use_container_width=True):
                    st.session_state.banco_caballos_por_carrera[carr_banco_sel].pop(idx_b)
                    if carr_banco_sel in st.session_state.remates and ej_item in st.session_state.remates[carr_banco_sel]:
                        del st.session_state.remates[carr_banco_sel][ej_item]
                    st.rerun()

    with sub_cierre:
        st.markdown("### 🏁 Cierre y Liquidación")
        carr_seleccionada_liq = st.selectbox("Gestionar Carrera", lista_carreras_disponibles, key="adm_liq_sel_carrera")

        with st.container(border=True):
            c_cerrada_actual = st.session_state.carreras_cerradas_remate.get(carr_seleccionada_liq, False)
            
            if not c_cerrada_actual:
                if st.button("🔒 Cerrar Remate", key=f"adm_liq_cerrar_{carr_seleccionada_liq}", use_container_width=True):
                    st.session_state.carreras_cerradas_remate[carr_seleccionada_liq] = True
                    st.session_state.estado_conteo_carrera[carr_seleccionada_liq] = "CERRADO"
                    
                    if not st.session_state.remates_cargados_en_cuentas.get(carr_seleccionada_liq, False):
                        for cab, info in st.session_state.remates[carr_seleccionada_liq].items():
                            if info['jugador'] != "Sin Postor" and info['monto'] > 0:
                                if info['jugador'] not in st.session_state.cuentas:
                                    st.session_state.cuentas[info['jugador']] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                                st.session_state.cuentas[info['jugador']]['Pujas'] += info['monto']
                        st.session_state.remates_cargados_en_cuentas[carr_seleccionada_liq] = True
                    st.rerun()
            else:
                if st.button("🔓 Reabrir Remate", key=f"adm_liq_reabrir_{carr_seleccionada_liq}", use_container_width=True):
                    st.session_state.carreras_cerradas_remate[carr_seleccionada_liq] = False
                    st.session_state.remates_cargados_en_cuentas[carr_seleccionada_liq] = False
                    st.rerun()

            if carr_seleccionada_liq in st.session_state.historial_ganadores:
                st.success("✅ Carrera ya liquidada.")
            else:
                pote_carr_total = sum([info['monto'] for info in st.session_state.remates[carr_seleccionada_liq].values()])
                monto_casa_calc = pote_carr_total * (porcentaje_casa / 100)
                premio_final_liq = pote_carr_total - monto_casa_calc + st.session_state.get(f"rem_pote_inc_{carr_seleccionada_liq}", 0.0)
                
                caballo_ganador_elegido = st.selectbox("Ganador", list(st.session_state.remates[carr_seleccionada_liq].keys()), key=f"adm_liq_ganador_{carr_seleccionada_liq}")
                
                if st.button("🎯 Liquidar Premio", key=f"adm_liq_btn_{carr_seleccionada_liq}", use_container_width=True, type="primary"):
                    info_g = st.session_state.remates[carr_seleccionada_liq][caballo_ganador_elegido]
                    if info_g['jugador'] != "Sin Postor":
                        if info_g['jugador'] not in st.session_state.cuentas:
                            st.session_state.cuentas[info_g['jugador']] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                        st.session_state.cuentas[info_g['jugador']]['Premios'] += premio_final_liq
                    st.session_state.ganancia_casa += monto_casa_calc
                    st.session_state.historial_ganadores[carr_seleccionada_liq] = {"Ganador": info_g['jugador'], "Premio": formatear_bs(premio_final_liq)}
                    st.success("¡Liquidado!")
                    st.rerun()

    with sub_hist:
        st.markdown("### 🧾 Historial de Transacciones")
        if not st.session_state.historial_transacciones:
            st.info("Sin transacciones.")
        else:
            st.dataframe(pd.DataFrame(st.session_state.historial_transacciones), use_container_width=True, hide_index=True)

    with sub_pdf:
        st.markdown("### 📄 Lector PDF e Importador Organizado por Posición")
        pdf_subido = st.file_uploader("Sube el programa oficial en PDF", type=["pdf"], key="adm_pdf_uploader")
        if pdf_subido is not None:
            if st.button("📥 Cargar PDF en Memoria", key="adm_pdf_btn_cargar", use_container_width=True):
                if extraer_texto_pdf(pdf_subido):
                    st.success("✅ ¡PDF cargado correctamente! Ya puedes procesarlo abajo.")
                    st.rerun()

        if st.session_state.programa_pdf_bytes is not None:
            st.markdown("---")
            st.markdown("### ✂️ Segmento Específico y Ordenamiento Estricto")
            texto_seleccion_usuario = st.text_area(
                "Texto del segmento específico a sincronizar:",
                value=st.session_state.texto_completo_pdf[:2000] if st.session_state.texto_completo_pdf else "",
                height=250,
                key="adm_pdf_text_area_segmento",
                placeholder="Ejemplo:\nPRIMERA CARRERA. CONDICIÓN: ...\n1 REY DAVID\n2 GRAN AMIGO..."
            )
            col_ps1, col_ps2 = st.columns(2)
            with col_ps1:
                if st.button("🚀 Sincronizar y Ordenar por Posición", key="adm_pdf_btn_sync", use_container_width=True, type="primary"):
                    if procesar_texto_para_remates(texto_seleccion_usuario):
                        st.success("✅ ¡Segmento procesado, ordenado por posición y sincronizado con éxito!")
                        st.rerun()
            with col_ps2:
                if st.button("⚡ Procesar PDF Completo Organizado", key="adm_pdf_btn_completo", use_container_width=True):
                    if procesar_texto_para_remates(st.session_state.texto_completo_pdf):
                        st.success("✅ ¡Programa completo procesado y ordenado por posición!")
                        st.rerun()

    with sub_img:
        st.markdown("### 🖼️ Cargar Imagen Representativa por Carrera")
        carr_img_sel = st.selectbox("Seleccionar Carrera para Imagen", lista_carreras_disponibles, key="adm_img_sel_carr")
        
        imagen_subida = st.file_uploader(f"Subir imagen para {carr_img_sel}", type=["png", "jpg", "jpeg"], key=f"file_img_{carr_img_sel}")
        if imagen_subida is not None:
            if st.button(f"💾 Guardar Imagen para {carr_img_sel}", key=f"btn_save_img_{carr_img_sel}", use_container_width=True, type="primary"):
                st.session_state.imagenes_carreras[carr_img_sel] = imagen_subida
                st.toast(f"✅ Imagen asignada correctamente a {carr_img_sel}")
                st.rerun()

        if carr_img_sel in st.session_state.imagenes_carreras:
            st.markdown("---")
            st.markdown("**Imagen actual asignada:**")
            st.image(st.session_state.imagenes_carreras[carr_img_sel], width=300)
            if st.button("🗑️ Eliminar Imagen", key=f"btn_del_img_{carr_img_sel}", use_container_width=True):
                del st.session_state.imagenes_carreras[carr_img_sel]
                st.toast("🗑️ Imagen removida")
                st.rerun()
import re
import base64
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from pypdf import PdfReader
from streamlit_autorefresh import st_autorefresh

# Configuración de pantalla completa (Responsive perfecto para Móviles y PC)
st.set_page_config(page_title="WOLF READY TO RUN", layout="wide", page_icon="🐺")

# --- AUTOREFRESH (3 SEGUNDOS) ---
try:
    st_autorefresh(interval=3000, key="datarefresh_en_vivo")
except Exception:
    pass

# --- HORA LOCAL DE VENEZUELA ---
def obtener_hora_venezuela_local():
    try:
        zona_venezuela = ZoneInfo("America/Caracas")
        return datetime.now(zona_venezuela).replace(tzinfo=None)
    except Exception:
        pass
    tz_venezuela = timezone(timedelta(hours=-4))
    return datetime.now(tz_venezuela).replace(tzinfo=None)

# --- ESCALA DE PUJAS ---
ESCALA_PUJAS = [
    50, 100, 150, 200, 250, 300, 350, 400, 500, 600, 700, 800, 900, 1000,
    1200, 1400, 1600, 1800, 2000, 2500, 3000, 3500, 4000, 4500, 5000,
    5500, 6000, 6500, 7000, 7500, 8000, 8500, 9000, 9500, 10000
] + list(range(11000, 1000001, 1000))

def obtener_siguientes_montos(monto_actual):
    siguientes = [m for m in ESCALA_PUJAS if m > monto_actual]
    if not siguientes:
        ultimo = ESCALA_PUJAS[-1] if ESCALA_PUJAS else max(monto_actual, 10000)
        siguientes = [ultimo + i * 1000 for i in range(1, 50)]
    return siguientes

# --- LECTOR DE LOGOTIPO LOCAL ---
def get_image_base64(nombres_posibles):
    ruta_directorio = os.path.dirname(os.path.abspath(__file__))
    for nombre_archivo in nombres_posibles:
        try:
            ruta_imagen = os.path.join(ruta_directorio, nombre_archivo)
            if os.path.exists(ruta_imagen):
                with open(ruta_imagen, "rb") as img_file:
                    return base64.b64encode(img_file.read()).decode('utf-8')
        except Exception:
            continue
    return ""

nombres_archivos = [
    "1001394095_preview_rev_1_2.png",
    "1001394095_preview_rev_1_2.jpg",
    "logo.png",
    "logo.jpg"
]

img_b64 = get_image_base64(nombres_archivos)

if img_b64:
    logo_display = f'<img src="data:image/png;base64,{img_b64}" class="header-logo-img" />'
else:
    logo_display = '<span style="color: #f1c40f; font-size: 16px; font-weight: 900; font-style: italic;">WOLF READY TO RUN</span>'

# --- HORA ACTUAL ---
ahora_dt = obtener_hora_venezuela_local()
fecha_hora_texto = ahora_dt.strftime('%d/%m/%Y - %I:%M:%S %p')

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stApp {
        background-color: #080a0f;
        color: #f0f6fc;
    }
    div[data-testid="stTabs"] {
        display: none !important;
    }
    .header-container {
        background: linear-gradient(180deg, #000000 0%, #11141d 100%) !important;
        width: 100% !important;
        padding: 8px 12px !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        border-bottom: 2px solid #21262d !important;
        margin: -1rem -1rem 0 -1rem !important;
        box-sizing: border-box !important;
        gap: 6px;
    }
    .header-top-row {
        width: 100% !important;
        display: flex !important;
        flex-direction: row !important;
        justify-content: space-between !important;
        align-items: center !important;
    }
    .menu-icon-box {
        background-color: #161b22 !important;
        color: #f1c40f !important;
        font-size: 18px !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
        padding: 4px 10px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    .header-logo-img {
        max-height: 40px !important;
        width: auto !important;
        object-fit: contain !important;
        display: block !important;
    }
    .top-clock-pill {
        background: #0d1117;
        border: 1px solid #30363d;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11px;
        color: #58a6ff;
        font-weight: 700;
        text-align: center;
        letter-spacing: 0.3px;
    }
    .user-info-container {
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        padding: 4px 10px !important;
        border-radius: 20px !important;
    }
    .user-text-info {
        display: flex !important;
        flex-direction: column !important;
        text-align: right !important;
        line-height: 1.1 !important;
    }
    .user-name {
        color: #ffffff !important;
        font-size: 11px !important;
        font-weight: 900 !important;
    }
    .user-balance {
        color: #58a6ff !important;
        font-size: 11px !important;
        font-weight: 800 !important;
    }
    .user-avatar {
        background-color: #f1c40f !important;
        color: #000000 !important;
        border-radius: 50% !important;
        width: 26px !important;
        height: 26px !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        font-size: 12px !important;
        font-weight: bold !important;
    }
    .block-container {
        padding-top: 0.6rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }
    .stButton button {
        width: 100% !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        padding: 0.3rem 0.4rem !important;
        min-height: 38px !important;
        font-size: 11px !important;
        letter-spacing: 0.3px;
        white-space: nowrap !important;
    }
    .carreras-scroll-container {
        display: flex;
        overflow-x: auto;
        gap: 8px;
        padding-bottom: 8px;
        scrollbar-width: thin;
        scrollbar-color: #f1c40f #161b22;
        width: 100%;
        -webkit-overflow-scrolling: touch;
    }
    .subasta-header {
        font-size: clamp(16px, 4vw, 20px);
        font-weight: 800;
        color: #f1e05a;
        margin-bottom: 4px;
        border-bottom: 2px solid #f1e05a;
        padding-bottom: 4px;
    }
    .timer-box {
        background-color: #161b22;
        border: 2px solid #ff4757;
        padding: 8px;
        border-radius: 8px;
        text-align: center;
        font-size: clamp(14px, 3.5vw, 18px);
        font-weight: bold;
        color: #ff4757;
        margin-bottom: 10px;
    }
    .cierre-info-box {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 6px;
        border-radius: 6px;
        text-align: center;
        font-size: 13px;
        color: #f0f6fc;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- CABECERA SUPERIOR MÓVIL ESTÉTICA ---
st.markdown(f"""
    <div class="header-container">
        <div class="header-top-row">
            <div class="menu-icon-box">☰</div>
            <div style="display: flex; align-items: center; justify-content: center; overflow: hidden; padding: 0 4px;">
                {logo_display}
            </div>
            <div class="user-info-container">
                <span style="color: #f1c40f !important; font-size: 16px !important;">🛢️</span>
                <div class="user-text-info">
                    <span class="user-name">ADMIN</span>
                    <span class="user-balance">Bs. 50k</span>
                </div>
                <div class="user-avatar">👤</div>
            </div>
        </div>
        <div class="top-clock-pill">
            <span>🕒</span> <b>{fecha_hora_texto}</b>
        </div>
    </div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- JUGADORES BASE ---
@st.cache_data
def cargar_jugadores_base():
    return ["CASA", "SOMBI", "LUIS", "CARLOS", "RAMON", "ALDEA", "ANGEL", "ALFONSO", "MACANO", "MIGUEL", "TOCAYO", "EL GOCHO", "PAPIRO", "CHAYO", "ALEXIS"]

# --- INICIALIZACIÓN GLOBAL AISLADA DE ESTADOS ---
def inicializar_estado_global():
    if 'menu_principal_opcion' not in st.session_state:
        st.session_state.menu_principal_opcion = "Remates"
    if 'lista_jugadores' not in st.session_state:
        st.session_state.lista_jugadores = cargar_jugadores_base()
    if 'banco_caballos_por_carrera' not in st.session_state:
        st.session_state.banco_caballos_por_carrera = {}
    if 'remates' not in st.session_state:
        st.session_state.remates = {}
    if 'historial_ganadores' not in st.session_state:
        st.session_state.historial_ganadores = {}
    if 'carreras_cerradas_remate' not in st.session_state:
        st.session_state.carreras_cerradas_remate = {}
    if 'remates_cargados_en_cuentas' not in st.session_state:
        st.session_state.remates_cargados_en_cuentas = {}
    if 'fechas_horas_cierre_remate' not in st.session_state:
        st.session_state.fechas_horas_cierre_remate = {}
    if 'estado_conteo_carrera' not in st.session_state:
        st.session_state.estado_conteo_carrera = {}
    if 'tiempo_inicio_conteo' not in st.session_state:
        st.session_state.tiempo_inicio_conteo = {}
    if 'cuentas' not in st.session_state:
        st.session_state.cuentas = {j: {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0} for j in st.session_state.lista_jugadores}
    if 'ganancia_casa' not in st.session_state:
        st.session_state.ganancia_casa = 0.0
    if 'historial_transacciones' not in st.session_state:
        st.session_state.historial_transacciones = []
    if 'dupletas_tickets' not in st.session_state:
        st.session_state.dupletas_tickets = []
    if 'carreras_habilitadas_dupleta' not in st.session_state:
        st.session_state.carreras_habilitadas_dupleta = []
    if 'dupleta_bloqueada' not in st.session_state:
        st.session_state.dupleta_bloqueada = False
    if 'carreras_activas_remate' not in st.session_state:
        st.session_state.carreras_activas_remate = []
    if 'programa_pdf_bytes' not in st.session_state:
        st.session_state.programa_pdf_bytes = None
    if 'programa_pdf_nombre' not in st.session_state:
        st.session_state.programa_pdf_nombre = None
    if 'texto_completo_pdf' not in st.session_state:
        st.session_state.texto_completo_pdf = ""

inicializar_estado_global()

def formatear_bs(monto):
    numero_formateado = f"{monto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"Bs. {numero_formateado}"

def obtener_abreviatura_carrera(nombre_carrera):
    match = re.search(r'\d+', nombre_carrera)
    if match:
        return f"C{match.group(0)}"
    return nombre_carrera[:3].upper()

# --- FORMATO HTML DE TABLA ---
def generar_tabla_html_remate(remates_dict):
    html = """
    <style>
        .tabla-referencia {
            width: 100%;
            border-collapse: collapse;
            font-family: sans-serif;
            background-color: #ffffff;
            color: #000000;
            margin-bottom: 15px;
        }
        .tabla-referencia th {
            border-top: 3px solid #dfc729;
            border-bottom: 2px solid #dfc729;
            padding: 8px 4px;
            text-align: left;
            font-weight: 800;
            background-color: #ffffff;
            color: #000000;
            font-size: 13px;
        }
        .tabla-referencia td {
            border-bottom: 1px solid #dfc729;
            padding: 6px 4px;
            background-color: #fbfbfb;
            color: #111111;
            font-size: 12px;
            vertical-align: middle;
        }
        .badge-numero {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 22px;
            height: 22px;
            font-weight: bold;
            font-size: 12px;
            border-radius: 2px;
            box-sizing: border-box;
        }
        .badge-1 { background-color: #e3242b; color: #ffffff; }
        .badge-2 { background-color: #ffffff; color: #000000; border: 2px solid #000000; }
        .badge-3 { background-color: #1d11c0; color: #ffffff; }
        .badge-4 { background-color: #f1c40f; color: #000000; }
        .badge-5 { background-color: #28a745; color: #ffffff; }
        .badge-6 { background-color: #000000; color: #ffffff; }
        .badge-7 { background-color: #fd7e14; color: #ffffff; }
        .badge-default { background-color: #6c757d; color: #ffffff; }
    </style>
    <div style="background-color: #ffffff; padding: 4px; border-radius: 8px; overflow-x: auto;">
        <table class="tabla-referencia">
            <thead>
                <tr>
                    <th style="width: 8%;">No</th>
                    <th style="width: 37%;">Ejemplar</th>
                    <th style="width: 27%;">Comprador</th>
                    <th style="width: 28%;">Monto Actual</th>
                </tr>
            </thead>
            <tbody>
    """
    for cab, info in remates_dict.items():
        match_num = re.match(r'^(\d+)', cab)
        if match_num:
            num = int(match_num.group(1))
            nombre_solo = cab.split(" - ", 1)[1] if " - " in cab else cab
        else:
            num = 0
            nombre_solo = cab
            
        if num == 1: badge_class = "badge-1"
        elif num == 2: badge_class = "badge-2"
        elif num == 3: badge_class = "badge-3"
        elif num == 4: badge_class = "badge-4"
        elif num == 5: badge_class = "badge-5"
        elif num == 6: badge_class = "badge-6"
        elif num == 7: badge_class = "badge-7"
        else: badge_class = "badge-default"
        
        html += f"""
                <tr>
                    <td><span class="badge-numero {badge_class}">{num}</span></td>
                    <td style="font-weight: 800; font-size: 13px;">{nombre_solo.upper()}</td>
                    <td>{info['jugador']}</td>
                    <td style="font-weight: bold; color: #000000;">{formatear_bs(info['monto'])}</td>
                </tr>
        """
    html += """
            </tbody>
        </table>
    </div>
    """
    return html

# --- EXTRACCIÓN DE PDF ---
def extraer_texto_pdf(archivo_pdf):
    try:
        bytes_data = archivo_pdf.getvalue()
        st.session_state.programa_pdf_bytes = bytes_data
        st.session_state.programa_pdf_nombre = getattr(archivo_pdf, "name", "Inscritos_Semana.pdf")
        
        lector_pdf = PdfReader(archivo_pdf)
        texto_extraido = ""
        for pagina in lector_pdf.pages:
            t_pag = pagina.extract_text()
            if t_pag:
                texto_extraido += t_pag + "\n"
        
        st.session_state.texto_completo_pdf = texto_extraido
        return True
    except Exception as e:
        st.sidebar.error(f"Error al leer PDF: {e}")
    return False

def procesar_texto_para_remates(texto_a_procesar):
    try:
        lineas = texto_a_procesar.split('\n')
        carrera_actual_detectada = None
        banco_temporal = {}
        
        patron_carrera = re.compile(
            r'(?:carrera|primera|segunda|tercera|cuarta|quinta|sexta|septima|octava|novena|decima|\d+)\s*(?:ª|º|\.)?\s*carrera', 
            re.IGNORECASE
        )
        
        for linea in lineas:
            linea_limpia = linea.strip()
            if not linea_limpia:
                continue
            
            match_carr = patron_carrera.search(linea_limpia)
            if match_carr or ("carrera" in linea_limpia.lower() and len(linea_limpia) < 35):
                for c_n in range(1, 15):
                    if str(c_n) in linea_limpia or f"carrera {c_n}" in linea_limpia.lower() or f"{c_n}ra" in linea_limpia.lower() or f"{c_n}da" in linea_limpia.lower() or f"{c_n}ta" in linea_limpia.lower():
                        carrera_actual_detectada = f"Carrera {c_n}"
                        if carrera_actual_detectada not in banco_temporal:
                            banco_temporal[carrera_actual_detectada] = []
                        break
            
            if carrera_actual_detectada:
                match_ejemplar = re.match(r'^(?:[Pp][Oo][Ss]\.?\s*)?(\d{1,2})[\s\-\.\)]+(.+)', linea_limpia)
                if match_ejemplar:
                    num_pos = int(match_ejemplar.group(1))
                    nom_ej = match_ejemplar.group(2).strip()
                    palabras_excluir = ['retirado', 'jinete', 'entrenador', 'distancia', 'premio', 'propietario', 'condicion', 'hipodromo', 'metros', 'haras', 'stud', 'aprox']
                    if 1 <= num_pos <= 25 and len(nom_ej) > 1 and not any(p in nom_ej.lower() for p in palabras_excluir):
                        formato_ej = f"{num_pos} - {nom_ej.title()}"
                        if formato_ej not in banco_temporal[carrera_actual_detectada]:
                            banco_temporal[carrera_actual_detectada].append(formato_ej)

        if banco_temporal:
            for c_key in banco_temporal:
                banco_temporal[c_key].sort(key=lambda x: int(re.match(r'^(\d+)', x).group(1)))

            st.session_state.banco_caballos_por_carrera = banco_temporal
            for c_key, c_vals in banco_temporal.items():
                if c_key not in st.session_state.remates:
                    st.session_state.remates[c_key] = {}
                for ev in c_vals:
                    if ev not in st.session_state.remates[c_key]:
                        st.session_state.remates[c_key][ev] = {"jugador": "Sin Postor", "monto": 0.0}
            
            todas_carr = list(banco_temporal.keys())
            st.session_state.carreras_activas_remate = list(todas_carr)
            st.session_state.carreras_habilitadas_dupleta = list(todas_carr)
            return True
    except Exception as e:
        st.error(f"Error procesando el segmento: {e}")
    return False

if not st.session_state.remates:
    for i in range(1, 11):
        carr_nombre = f"Carrera {i}"
        st.session_state.banco_caballos_por_carrera[carr_nombre] = [f"{j} - Ejemplar {j}" for j in range(1, 11)]
        st.session_state.remates[carr_nombre] = {f"{j} - Ejemplar {j}": {"jugador": "Sin Postor", "monto": 0.0} for j in range(1, 11)}

lista_carreras_disponibles = list(st.session_state.remates.keys())

if not st.session_state.carreras_activas_remate and lista_carreras_disponibles:
    st.session_state.carreras_activas_remate = list(lista_carreras_disponibles)

if not st.session_state.carreras_habilitadas_dupleta and lista_carreras_disponibles:
    st.session_state.carreras_habilitadas_dupleta = list(lista_carreras_disponibles)

# --- MENÚ PRINCIPAL HORIZONTAL (4 BOTONES EN FILA) ---
col_menu1, col_menu2, col_menu3, col_menu4 = st.columns(4, gap="small")

with col_menu1:
    if st.button("🔒 ADMIN", key="menu_btn_admin_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "🔒 Zona Admin" else "secondary"):
        st.session_state.menu_principal_opcion = "🔒 Zona Admin"
        st.rerun()

with col_menu2:
    if st.button("🏇 REMATES", key="menu_btn_remates_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Remates" else "secondary"):
        st.session_state.menu_principal_opcion = "Remates"
        st.rerun()

with col_menu3:
    if st.button("🎟️ DUPLETAS", key="menu_btn_dupletas_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Dupletas" else "secondary"):
        st.session_state.menu_principal_opcion = "Dupletas"
        st.rerun()

with col_menu4:
    if st.button("📊 CUENTAS", key="menu_btn_cuentas_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Cuentas" else "secondary"):
        st.session_state.menu_principal_opcion = "Cuentas"
        st.rerun()

st.markdown("<hr style='margin: 0.8rem 0; border-color: #21262d;'>", unsafe_allow_html=True)

# --- BARRA LATERAL AISLADA ---
st.sidebar.header("barra lateral")
ahora_dt = obtener_hora_venezuela_local()
st.sidebar.markdown(f"🕒 **Hora:** `{ahora_dt.strftime('%I:%M:%S %p')}`")

with st.sidebar.expander("⚡ Carreras Activas para Remate", expanded=True):
    st.markdown("Selecciona cuáles carreras están disponibles y activas en el panel principal:")
    carreras_seleccionadas_activas = st.multiselect(
        "Carreras Activas",
        options=lista_carreras_disponibles,
        default=[c for c in st.session_state.carreras_activas_remate if c in lista_carreras_disponibles],
        key="sb_multiselect_carreras_activas"
    )
    if carreras_seleccionadas_activas != st.session_state.carreras_activas_remate:
        st.session_state.carreras_activas_remate = carreras_seleccionadas_activas
        st.rerun()

with st.sidebar.expander("🏠 Retención de la Casa", expanded=False):
    porcentaje_casa = st.slider("Retención (%)", 0, 50, 30, key="sb_slider_retencion_casa")

with st.sidebar.expander("📅⏰ Cierres Estrictos por Carrera", expanded=False):
    carrera_config_sel = st.selectbox("Seleccionar Carrera", lista_carreras_disponibles, key="sb_selector_carrera_config")
    fecha_sel = st.date_input("Fecha de Cierre", value=ahora_dt.date(), key=f"sb_sel_f_{carrera_config_sel}")
    periodo_sel = st.radio("Periodo", ["AM", "PM"], key=f"sb_radio_p_{carrera_config_sel}", horizontal=True)
    hora_12 = st.selectbox("Hora", list(range(1, 13)), key=f"sb_sel_h_{carrera_config_sel}")
    minuto_sel = st.selectbox("Minutos", list(range(0, 60)), key=f"sb_sel_m_{carrera_config_sel}")
    
    h_24_conv = int(hora_12)
    if periodo_sel == "PM" and h_24_conv < 12: h_24_conv += 12
    elif periodo_sel == "AM" and h_24_conv == 12: h_24_conv = 0
    
    hora_seleccionada = time(h_24_conv, int(minuto_sel))
    dt_cierre_completo = datetime.combine(fecha_sel, hora_seleccionada)
    
    col_bh1, col_bh2 = st.sidebar.columns(2)
    with col_bh1:
        if st.button("💾 Guardar", key=f"sb_btn_guardar_cierre_{carrera_config_sel}"):
            st.session_state.fechas_horas_cierre_remate[carrera_config_sel] = dt_cierre_completo
            st.session_state.estado_conteo_carrera[carrera_config_sel] = "INACTIVO"
            st.toast(f"✅ Cierre guardado para {carrera_config_sel}")
            st.rerun()
    with col_bh2:
        if st.button("🗑️ Borrar", key=f"sb_btn_borrar_cierre_{carrera_config_sel}"):
            if carrera_config_sel in st.session_state.fechas_horas_cierre_remate:
                del st.session_state.fechas_horas_cierre_remate[carrera_config_sel]
            st.session_state.estado_conteo_carrera[carrera_config_sel] = "INACTIVO"
            st.toast("🗑️ Cierre removido")
            st.rerun()

with st.sidebar.expander("🔒 Estado Dupletas", expanded=False):
    if st.session_state.dupleta_bloqueada:
        st.markdown("<p style='color: #ff4757; font-weight: bold;'>🔴 BLOQUEADAS</p>", unsafe_allow_html=True)
        if st.button("🔓 Desbloquear", key="sb_btn_desbloquear_dupleta"):
            st.session_state.dupleta_bloqueada = False
            st.rerun()
    else:
        st.markdown("<p style='color: #00d2d3; font-weight: bold;'>🟢 ABIERTAS</p>", unsafe_allow_html=True)
        if st.button("🔒 Bloquear", key="sb_btn_bloquear_dupleta"):
            st.session_state.dupleta_bloqueada = True
            st.rerun()

if st.sidebar.button("🗑️ Reiniciar Jornada", key="sb_btn_reiniciar_jornada", use_container_width=True):
    for key in list(st.session_state.keys()):
        if key != 'banco_caballos_por_carrera':
            del st.session_state[key]
    st.toast("🚨 Jornada reiniciada.")
    st.rerun()

menu_principal_opcion = st.session_state.menu_principal_opcion

# =========================================================================
# 1. MÓDULO DE REMATES
# =========================================================================
if menu_principal_opcion == "Remates":
    if not lista_carreras_disponibles:
        st.warning("⚠️ No hay carreras cargadas en el sistema.")
    else:
        carreras_filtradas_visibles = [
            c for c in lista_carreras_disponibles 
            if (c in st.session_state.carreras_activas_remate) or st.session_state.carreras_cerradas_remate.get(c, False)
        ]
        
        if not carreras_filtradas_visibles:
            st.info("ℹ️ No hay carreras activas ni cerradas para mostrar. Selecciona carreras en el menú lateral de control.")
        else:
            if "carrera_remate_activa_seleccionada" not in st.session_state or st.session_state["carrera_remate_activa_seleccionada"] not in carreras_filtradas_visibles:
                carr_activa = carreras_filtradas_visibles[0]
                st.session_state["carrera_remate_activa_seleccionada"] = carr_activa
            else:
                carr_activa = st.session_state["carrera_remate_activa_seleccionada"]

            st.markdown("🔹 **Seleccionar Carrera:**")
            cols_carreras = st.columns(len(carreras_filtradas_visibles))
            for idx, c_nombre in enumerate(carreras_filtradas_visibles):
                abreviatura = obtener_abreviatura_carrera(c_nombre)
                es_activa = (c_nombre == carr_activa)
                with cols_carreras[idx]:
                    if st.button(abreviatura, key=f"rem_btn_sel_carr_{idx}", use_container_width=True, type="primary" if es_activa else "secondary"):
                        st.session_state["carrera_remate_activa_seleccionada"] = c_nombre
                        st.rerun()

            st.markdown(f"---")
            carrera_cerrada = st.session_state.carreras_cerradas_remate.get(carr_activa, False)
            
            if carrera_cerrada:
                st.error(f"🔴 La carrera **{carr_activa}** se encuentra **CERRADA** para nuevas pujas.")
            else:
                st.success(f"🟢 Panel activo y abierto para: **{carr_activa}**")

            st.markdown(f"### 🏁 {carr_activa}")
            dt_limite = st.session_state.fechas_horas_cierre_remate.get(carr_activa)
            estado_conteo = st.session_state.estado_conteo_carrera.get(carr_activa, "INACTIVO")
            
            if dt_limite:
                st.markdown(f"<div class='cierre-info-box'>⏰ Cierre Estricto: <b>{dt_limite.strftime('%d/%m/%Y - %I:%M %p')}</b></div>", unsafe_allow_html=True)

            if dt_limite and not carrera_cerrada:
                diferencia_segundos = (dt_limite - ahora_dt).total_seconds()
                if estado_conteo == "INACTIVO":
                    if 0 < diferencia_segundos <= 10:
                        st.session_state.estado_conteo_carrera[carr_activa] = "CONTEO_10S"
                        st.session_state.tiempo_inicio_conteo[carr_activa] = ahora_dt
                        st.rerun()
                    elif diferencia_segundos <= 0:
                        st.session_state.carreras_cerradas_remate[carr_activa] = True
                        st.session_state.estado_conteo_carrera[carr_activa] = "CERRADO"
                        st.rerun()
                elif estado_conteo == "CONTEO_10S":
                    tiempo_inicio = st.session_state.tiempo_inicio_conteo.get(carr_activa, ahora_dt)
                    transcurridos = (ahora_dt - tiempo_inicio).total_seconds()
                    if transcurridos >= 12:
                        st.session_state.carreras_cerradas_remate[carr_activa] = True
                        st.session_state.estado_conteo_carrera[carr_activa] = "CERRADO"
                        st.rerun()
                    else:
                        restantes_10s = max(0, 10 - int(transcurridos))
                        if restantes_10s > 0:
                            st.markdown(f"<div class='timer-box'>⚠️ CIERRE EN: <b>{restantes_10s}s</b> ({carr_activa})</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div class='timer-box'>⚠️ ULTIMOS SEGUNDOS ANTES DE CIERRE ({carr_activa})</div>", unsafe_allow_html=True)

            tabla_html = generar_tabla_html_remate(st.session_state.remates[carr_activa])
            cantidad_filas = len(st.session_state.remates[carr_activa])
            altura_dinamica = min(max(180, (cantidad_filas * 45) + 80), 550)
            components.html(tabla_html, height=altura_dinamica, scrolling=True)
            
            total_pote = sum([info['monto'] for info in st.session_state.remates[carr_activa].values()])
            monto_casa = total_pote * (porcentaje_casa / 100)
            pote_neto_base = total_pote - monto_casa

            c_m1, c_m2 = st.columns(2)
            c_m1.metric(f"💰 Pote ({carr_activa})", formatear_bs(total_pote))
            pote_incentivo_extra = c_m2.number_input("🎁 Extra", min_value=0.0, value=0.0, step=50.0, key=f"rem_pote_inc_{carr_activa}")
            premio_total_calculado = pote_neto_base + pote_incentivo_extra
            st.metric(f"🏆 Premio Total ({carr_activa})", formatear_bs(premio_total_calculado))

            with st.container(border=True):
                st.markdown(f"⚡ **Registro Rápido de Puja - {carr_activa}**")
                lista_caballos_activos = list(st.session_state.remates[carr_activa].keys())
                
                if not lista_caballos_activos:
                    st.warning("Sin ejemplares inscritos en esta carrera.")
                else:
                    k_sel_cab = f"rem_caballo_activo_click_{carr_activa}"
                    if k_sel_cab not in st.session_state or st.session_state[k_sel_cab] not in lista_caballos_activos:
                        st.session_state[k_sel_cab] = lista_caballos_activos[0]
                        
                    st.markdown(f"🔹 **1. Seleccionar Ejemplar (Total inscritos: {len(lista_caballos_activos)}):**")
                    cantidad_ejemplares = len(lista_caballos_activos)
                    cols_ejemplares = min(4, cantidad_ejemplares) if cantidad_ejemplares > 0 else 1
                    num_filas = (cantidad_ejemplares + cols_ejemplares - 1) // cols_ejemplares
                    
                    idx_cab = 0
                    for f in range(num_filas):
                        cols_fila = st.columns(cols_ejemplares)
                        for c in range(cols_ejemplares):
                            if idx_cab < cantidad_ejemplares:
                                cab_item = lista_caballos_activos[idx_cab]
                                num_parte = cab_item.split(" - ")[0]
                                with cols_fila[c]:
                                    if st.button(f"#{num_parte}", key=f"rem_btn_cab_{carr_activa}_{idx_cab}", use_container_width=True):
                                        st.session_state[k_sel_cab] = cab_item
                                idx_cab += 1
                    
                    caballo_seleccionado = st.session_state[k_sel_cab]
                    st.info(f"Ejemplar activo en {carr_activa}: **{caballo_seleccionado}**")

                    puja_actual = st.session_state.remates[carr_activa][caballo_seleccionado]['monto']
                    opciones_escala = obtener_siguientes_montos(puja_actual)
                    monto_puja = st.selectbox("💰 **2. Monto de Puja**", opciones_escala, format_func=lambda x: formatear_bs(x), key=f"rem_sel_monto_{carr_activa}_{caballo_seleccionado}")
                    
                    if carrera_cerrada:
                        st.button(f"🔨 Confirmar Puja ({carr_activa})", key=f"rem_btn_confirmar_{carr_activa}", use_container_width=True, type="primary", disabled=True)
                    else:
                        if st.button(f"🔨 Confirmar Puja ({carr_activa})", key=f"rem_btn_confirmar_{carr_activa}", use_container_width=True, type="primary"):
                            if monto_puja <= puja_actual:
                                st.error("El monto debe ser mayor a la puja actual.")
                            else:
                                st.session_state.remates[carr_activa][caballo_seleccionado] = {"jugador": "Sin Postor", "monto": monto_puja}
                                if estado_conteo == "CONTEO_10S":
                                    st.session_state.tiempo_inicio_conteo[carr_activa] = obtener_hora_venezuela_local()
                                st.success("✅ ¡Puja registrada correctamente y conteo reiniciado!")
                                st.rerun()

# =========================================================================
# 2. MÓDULO DE DUPLETAS
# =========================================================================
elif menu_principal_opcion == "Dupletas":
    st.markdown("<div class='subasta-header'>🎟️ Módulo de Dupletas</div>", unsafe_allow_html=True)
    if st.session_state.dupleta_bloqueada:
        st.error("🔒 **BLOQUEADO:** Emisión cerrada.")

    pote_total_dupletas = sum([t['monto'] for t in st.session_state.dupletas_tickets])
    st.metric("💰 Pote Acumulado Dupletas", formatear_bs(pote_total_dupletas))

    with st.container(border=True):
        jugador_dupleta = st.selectbox("👤 Jugador", st.session_state.lista_jugadores, key="dup_input_jugador")
        monto_dupleta = st.number_input("💰 Monto (Bs.)", min_value=50.0, value=500.0, step=50.0, key="dup_input_monto")
        num_legs = st.radio("Cantidad de Selecciones:", [2, 3, 4, 5, 6], horizontal=True, key="dup_radio_legs")

    with st.container(border=True):
        seleccion_legs = []
        carreras_usadas_en_ticket = set()
        valido_legs = True
        carreras_habilitadas = st.session_state.carreras_habilitadas_dupleta
        
        for i in range(num_legs):
            c_leg, cb_leg_col = st.columns(2)
            with c_leg:
                carr_leg = st.selectbox(f"Carrera {i+1}", carreras_habilitadas, key=f"dup_sel_carrera_{i}")
            with cb_leg_col:
                caballos_in_carr = list(st.session_state.remates.get(carr_leg, {}).keys())
                cab_leg = st.selectbox(f"Ejemplar {i+1}", caballos_in_carr if caballos_in_carr else ["Sin Caballos"], key=f"dup_sel_ejemplar_{i}")
            
            if carr_leg in carreras_usadas_en_ticket:
                valido_legs = False
            carreras_usadas_en_ticket.add(carr_leg)
            seleccion_legs.append({"carrera": carr_leg, "ejemplar": cab_leg})

    if not st.session_state.dupleta_bloqueada:
        if st.button("🚀 Emitir Ticket de Dupleta", key="dup_btn_emitir", use_container_width=True, type="primary"):
            if not valido_legs:
                st.error("⚠️ No puedes repetir carreras en el mismo ticket.")
            else:
                ticket_id = f"DUP-{len(st.session_state.dupletas_tickets) + 1:04d}"
                st.session_state.dupletas_tickets.append({
                    "id": ticket_id, "jugador": jugador_dupleta, "monto": monto_dupleta,
                    "legs": seleccion_legs, "estado": "Pendiente", "fecha": ahora_dt.strftime('%d/%m %I:%M %p')
                })
                if jugador_dupleta not in st.session_state.cuentas:
                    st.session_state.cuentas[jugador_dupleta] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                st.session_state.cuentas[jugador_dupleta]['Pujas'] += monto_dupleta
                st.success(f"✅ Ticket {ticket_id} emitido")
                st.rerun()

# =========================================================================
# 3. MÓDULO DE CUENTAS
# =========================================================================
elif menu_principal_opcion == "Cuentas":
    st.markdown("<div class='subasta-header'>📊 Cuentas y Balances</div>", unsafe_allow_html=True)
    datos_cuentas = []
    tot_pujas_gen = 0.0
    for jugador, vals in st.session_state.cuentas.items():
        pujas, premios, abonos = vals['Pujas'], vals['Premios'], vals['Abonos']
        balance_neto = pujas - abonos - premios
        tot_pujas_gen += pujas
        datos_cuentas.append({"Jugador": jugador, "Compras": formatear_bs(pujas), "Premios": formatear_bs(premios), "Neto": formatear_bs(balance_neto)})
    st.dataframe(pd.DataFrame(datos_cuentas), use_container_width=True, hide_index=True)
    st.metric("Ganancia Casa", formatear_bs(st.session_state.ganancia_casa))

# =========================================================================
# 4. ZONA DE ADMINISTRADOR
# =========================================================================
elif menu_principal_opcion == "🔒 Zona Admin":
    st.markdown("<div class='subasta-header'>🔒 Zona de Administrador</div>", unsafe_allow_html=True)
    sub_banco, sub_cierre, sub_hist, sub_pdf = st.tabs(["✍️ Banco", "🏁 Cierre", "🧾 Historial", "📄 PDF"])
    
    with sub_banco:
        st.markdown("### ✍️ Banco de Caballos por Carrera")
        carr_banco_sel = st.selectbox("Seleccionar Carrera", lista_carreras_disponibles, key="adm_banco_sel_carrera")
        
        if carr_banco_sel not in st.session_state.banco_caballos_por_carrera:
            st.session_state.banco_caballos_por_carrera[carr_banco_sel] = []
            
        with st.container(border=True):
            nuevo_nom_banco = st.text_input("Nombre del Ejemplar", placeholder="Ej: Rey David", key=f"adm_banco_input_{carr_banco_sel}")
            if st.button("💾 Agregar al Banco", key=f"adm_banco_btn_add_{carr_banco_sel}", use_container_width=True, type="primary"):
                nom_limp = nuevo_nom_banco.strip().title()
                if nom_limp:
                    nums = [int(re.match(r'^(\d+)', e).group(1)) for e in st.session_state.banco_caballos_por_carrera[carr_banco_sel] if re.match(r'^(\d+)', e)]
                    sig_num = 1
                    while sig_num in nums and sig_num <= 25: sig_num += 1
                    formato_nuevo = f"{sig_num} - {nom_limp}"
                    
                    if formato_nuevo not in st.session_state.banco_caballos_por_carrera[carr_banco_sel]:
                        st.session_state.banco_caballos_por_carrera[carr_banco_sel].append(formato_nuevo)
                        st.session_state.banco_caballos_por_carrera[carr_banco_sel].sort(key=lambda x: int(re.match(r'^(\d+)', x).group(1)))

                    if carr_banco_sel not in st.session_state.remates:
                        st.session_state.remates[carr_banco_sel] = {}
                    if formato_nuevo not in st.session_state.remates[carr_banco_sel]:
                        st.session_state.remates[carr_banco_sel][formato_nuevo] = {"jugador": "Sin Postor", "monto": 0.0}
                    st.toast("✅ ¡Agregado con éxito y ordenado por posición!")
                    st.rerun()

        for idx_b, ej_item in enumerate(st.session_state.banco_caballos_por_carrera[carr_banco_sel]):
            col_ib1, col_ib2 = st.columns([5, 1])
            with col_ib1: st.text(ej_item)
            with col_ib2:
                if st.button("🗑️", key=f"adm_banco_del_{carr_banco_sel}_{idx_b}", use_container_width=True):
                    st.session_state.banco_caballos_por_carrera[carr_banco_sel].pop(idx_b)
                    if carr_banco_sel in st.session_state.remates and ej_item in st.session_state.remates[carr_banco_sel]:
                        del st.session_state.remates[carr_banco_sel][ej_item]
                    st.rerun()

    with sub_cierre:
        st.markdown("### 🏁 Cierre y Liquidación")
        carr_seleccionada_liq = st.selectbox("Gestionar Carrera", lista_carreras_disponibles, key="adm_liq_sel_carrera")

        with st.container(border=True):
            c_cerrada_actual = st.session_state.carreras_cerradas_remate.get(carr_seleccionada_liq, False)
            
            if not c_cerrada_actual:
                if st.button("🔒 Cerrar Remate", key=f"adm_liq_cerrar_{carr_seleccionada_liq}", use_container_width=True):
                    st.session_state.carreras_cerradas_remate[carr_seleccionada_liq] = True
                    st.session_state.estado_conteo_carrera[carr_seleccionada_liq] = "CERRADO"
                    
                    if not st.session_state.remates_cargados_en_cuentas.get(carr_seleccionada_liq, False):
                        for cab, info in st.session_state.remates[carr_seleccionada_liq].items():
                            if info['jugador'] != "Sin Postor" and info['monto'] > 0:
                                if info['jugador'] not in st.session_state.cuentas:
                                    st.session_state.cuentas[info['jugador']] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                                st.session_state.cuentas[info['jugador']]['Pujas'] += info['monto']
                        st.session_state.remates_cargados_en_cuentas[carr_seleccionada_liq] = True
                    st.rerun()
            else:
                if st.button("🔓 Reabrir Remate", key=f"adm_liq_reabrir_{carr_seleccionada_liq}", use_container_width=True):
                    st.session_state.carreras_cerradas_remate[carr_seleccionada_liq] = False
                    st.session_state.remates_cargados_en_cuentas[carr_seleccionada_liq] = False
                    st.rerun()

            if carr_seleccionada_liq in st.session_state.historial_ganadores:
                st.success("✅ Carrera ya liquidada.")
            else:
                pote_carr_total = sum([info['monto'] for info in st.session_state.remates[carr_seleccionada_liq].values()])
                monto_casa_calc = pote_carr_total * (porcentaje_casa / 100)
                premio_final_liq = pote_carr_total - monto_casa_calc + st.session_state.get(f"rem_pote_inc_{carr_seleccionada_liq}", 0.0)
                
                caballo_ganador_elegido = st.selectbox("Ganador", list(st.session_state.remates[carr_seleccionada_liq].keys()), key=f"adm_liq_ganador_{carr_seleccionada_liq}")
                
                if st.button("🎯 Liquidar Premio", key=f"adm_liq_btn_{carr_seleccionada_liq}", use_container_width=True, type="primary"):
                    info_g = st.session_state.remates[carr_seleccionada_liq][caballo_ganador_elegido]
                    if info_g['jugador'] != "Sin Postor":
                        if info_g['jugador'] not in st.session_state.cuentas:
                            st.session_state.cuentas[info_g['jugador']] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                        st.session_state.cuentas[info_g['jugador']]['Premios'] += premio_final_liq
                    st.session_state.ganancia_casa += monto_casa_calc
                    st.session_state.historial_ganadores[carr_seleccionada_liq] = {"Ganador": info_g['jugador'], "Premio": formatear_bs(premio_final_liq)}
                    st.success("¡Liquidado!")
                    st.rerun()

    with sub_hist:
        st.markdown("### 🧾 Historial de Transacciones")
        if not st.session_state.historial_transacciones:
            st.info("Sin transacciones.")
        else:
            st.dataframe(pd.DataFrame(st.session_state.historial_transacciones), use_container_width=True, hide_index=True)

    with sub_pdf:
        st.markdown("### 📄 Lector PDF e Importador Organizado por Posición")
        
        pdf_subido = st.file_uploader("Sube el programa oficial en PDF", type=["pdf"], key="adm_pdf_uploader")
        if pdf_subido is not None:
            if st.button("📥 Cargar PDF en Memoria", key="adm_pdf_btn_cargar", use_container_width=True):
                if extraer_texto_pdf(pdf_subido):
                    st.success("✅ ¡PDF cargado correctamente! Ya puedes procesarlo abajo.")
                    st.rerun()

        if st.session_state.programa_pdf_bytes is not None:
            st.markdown("---")
            st.markdown("### ✂️ Segmento Específico y Ordenamiento Estricto")
            st.markdown("Pega aquí abajo el texto seleccionado o la sección que deseas procesar. El sistema extraerá de forma automática la **Carrera N**, ordenando cada ejemplar por su **Número de Posición / Ejemplar** de menor a mayor:")
            
            texto_seleccion_usuario = st.text_area(
                "Texto del segmento específico a sincronizar:",
                value=st.session_state.texto_completo_pdf[:2000] if st.session_state.texto_completo_pdf else "",
                height=250,
                key="adm_pdf_text_area_segmento",
                placeholder="Ejemplo:\nPRIMERA CARRERA. CONDICIÓN: ...\n1 REY DAVID\n2 GRAN AMIGO..."
            )
            
            col_ps1, col_ps2 = st.columns(2)
            with col_ps1:
                if st.button("🚀 Sincronizar y Ordenar por Posición", key="adm_pdf_btn_sync", use_container_width=True, type="primary"):
                    if procesar_texto_para_remates(texto_seleccion_usuario):
                        st.success("✅ ¡Segmento procesado, ordenado por posición y sincronizado con éxito!")
                        st.rerun()
                    else:
                        st.error("⚠️ No se pudo extraer la estructura correcta. Revisa que el texto contenga el nombre de la carrera y los números de posición.")
            with col_ps2:
                if st.button("⚡ Procesar PDF Completo Organizado", key="adm_pdf_btn_completo", use_container_width=True):
                    if procesar_texto_para_remates(st.session_state.texto_completo_pdf):
                        st.success("✅ ¡Programa completo procesado y ordenado por posición!")
                        st.rerun()
                    else:
                        st.error("⚠️ No se pudo procesar automáticamente el documento.")
