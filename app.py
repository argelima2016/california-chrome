import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import re
import base64
import requests
import io
from bs4 import BeautifulSoup
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

# --- ESTILOS CSS (COMPACTOS PARA MÓVIL) ---
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
        padding: 6px 10px !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        border-bottom: 2px solid #21262d !important;
        margin: -1rem -1rem 0 -1rem !important;
        box-sizing: border-box !important;
        gap: 4px;
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
        font-size: 16px !important;
        border: 1px solid #30363d !important;
        border-radius: 6px !important;
        padding: 2px 8px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    .header-logo-img {
        max-height: 35px !important;
        width: auto !important;
        object-fit: contain !important;
        display: block !important;
    }
    .top-clock-pill {
        background: #0d1117;
        border: 1px solid #30363d;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 10px;
        color: #58a6ff;
        font-weight: 700;
        text-align: center;
        letter-spacing: 0.3px;
    }
    .user-info-container {
        display: flex !important;
        align-items: center !important;
        gap: 6px !important;
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        padding: 3px 8px !important;
        border-radius: 16px !important;
    }
    .user-text-info {
        display: flex !important;
        flex-direction: column !important;
        text-align: right !important;
        line-height: 1.0 !important;
    }
    .user-name {
        color: #ffffff !important;
        font-size: 10px !important;
        font-weight: 900 !important;
    }
    .user-balance {
        color: #58a6ff !important;
        font-size: 10px !important;
        font-weight: 800 !important;
    }
    .user-avatar {
        background-color: #f1c40f !important;
        color: #000000 !important;
        border-radius: 50% !important;
        width: 22px !important;
        height: 22px !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        font-size: 10px !important;
        font-weight: bold !important;
    }
    .block-container {
        padding-top: 0.4rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.4rem !important;
        padding-right: 0.4rem !important;
        max-width: 100% !important;
    }
    .stButton button {
        width: 100% !important;
        border-radius: 4px !important;
        font-weight: 600 !important;
        padding: 0.1rem 0.1rem !important;
        min-height: 24px !important;
        max-height: 28px !important;
        font-size: 9px !important;
        letter-spacing: 0.1px;
        white-space: nowrap !important;
    }
    div[data-testid="column"] {
        width: auto !important;
        flex: 1 !important;
        min-width: 0 !important;
        padding: 0 1px !important;
    }
    .subasta-header {
        font-size: clamp(14px, 3.5vw, 18px);
        font-weight: 800;
        color: #f1e05a;
        margin-bottom: 3px;
        border-bottom: 2px solid #f1e05a;
        padding-bottom: 2px;
    }
    .timer-box {
        background-color: #161b22;
        border: 2px solid #ff4757;
        padding: 6px;
        border-radius: 6px;
        text-align: center;
        font-size: clamp(12px, 3vw, 16px);
        font-weight: bold;
        color: #ff4757;
        margin-bottom: 8px;
    }
    .cierre-info-box {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 4px;
        border-radius: 4px;
        text-align: center;
        font-size: 11px;
        color: #f0f6fc;
        margin-bottom: 8px;
    }
    .carrera-condicion-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 12px;
        color: #f0f6fc;
        margin-bottom: 10px;
        line-height: 1.4;
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
                <span style="color: #f1c40f !important; font-size: 14px !important;">🛢️</span>
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
    if 'detalles_carreras' not in st.session_state:
        st.session_state.detalles_carreras = {}
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
    if 'admin_tab_seleccionada' not in st.session_state:
        st.session_state.admin_tab_seleccionada = "✍️ Banco"

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
            margin-bottom: 12px;
        }
        .tabla-referencia th {
            border-top: 3px solid #dfc729;
            border-bottom: 2px solid #dfc729;
            padding: 6px 4px;
            text-align: left;
            font-weight: 800;
            background-color: #ffffff;
            color: #000000;
            font-size: 12px;
        }
        .tabla-referencia td {
            border-bottom: 1px solid #dfc729;
            padding: 5px 4px;
            background-color: #fbfbfb;
            color: #111111;
            font-size: 11px;
            vertical-align: middle;
        }
        .badge-numero {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 20px;
            height: 20px;
            font-weight: bold;
            font-size: 11px;
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
    <div style="background-color: #ffffff; padding: 4px; border-radius: 6px; overflow-x: auto;">
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
                    <td style="font-weight: 800; font-size: 12px;">{nombre_solo.upper()}</td>
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

def procesar_texto_flexible(texto_a_procesar):
    try:
        lineas = texto_a_procesar.split('\n')
        carrera_actual_detectada = None
        banco_temporal = {}
        detalles_temporal = {}
        
        map_numeros = {
            'primera': 1, 'segunda': 2, 'tercera': 3, 'cuarta': 4,
            'quinta': 5, 'sexta': 6, 'septima': 7, 'octava': 8,
            'novena': 9, 'decima': 10, 'undecima': 11, 'duodecima': 12
        }

        for linea in lineas:
            linea_limpia = linea.strip()
            if not linea_limpia:
                continue
            
            linea_lower = linea_limpia.lower()
            
            if "carrera" in linea_lower or any(k in linea_lower for k in map_numeros.keys()):
                match_digito = re.search(r'(\d+)', linea_lower)
                if match_digito and ("carrera" in linea_lower or len(linea_limpia) < 45):
                    num_carr = int(match_digito.group(1))
                    carrera_actual_detectada = f"Carrera {num_carr}"
                else:
                    for palabra, num in map_numeros.items():
                        if palabra in linea_lower:
                            carrera_actual_detectada = f"Carrera {num}"
                            break

                if carrera_actual_detectada:
                    if carrera_actual_detectada not in banco_temporal:
                        banco_temporal[carrera_actual_detectada] = []
                    
                    cond = linea_limpia
                    dist = "Por definir"
                    hora = "Por definir"

                    match_dist = re.search(r'(\d+[\.,]?\d*\s*(?:mts|metros|mt))', linea_lower)
                    if match_dist:
                        dist = match_dist.group(1).upper()

                    match_h = re.search(r'(\d{1,2}:\d{2}\s*(?:am|pm)?)', linea_lower)
                    if match_h:
                        hora = match_h.group(1).upper()

                    detalles_temporal[carrera_actual_detectada] = {"condicion": cond, "distancia": dist, "hora": hora}
                    continue

            if carrera_actual_detectada:
                if "mts" in linea_lower or "metros" in linea_lower:
                    if detalles_temporal[carrera_actual_detectada]["distancia"] == "Por definir":
                        detalles_temporal[carrera_actual_detectada]["distancia"] = linea_limpia
                if re.search(r'\d{1,2}:\d{2}', linea_lower):
                    match_h2 = re.search(r'\d{1,2}:\d{2}\s*(?:am|pm)?', linea_lower)
                    if match_h2 and detalles_temporal[carrera_actual_detectada]["hora"] == "Por definir":
                        detalles_temporal[carrera_actual_detectada]["hora"] = match_h2.group(0).upper()

                match_ejemplar = re.match(r'^(?:[Pp][Oo][Ss]\.?\s*)?(\d{1,2})[\s\-\.\)]+(.+)', linea_limpia)
                if match_ejemplar:
                    num_pos = int(match_ejemplar.group(1))
                    nom_ej = match_ejemplar.group(2).strip()
                    palabras_excluir = ['retirado', 'jinete', 'entrenador', 'distancia', 'premio', 'propietario', 'condicion', 'hipodromo', 'metros', 'haras', 'stud', 'aprox', 'ejemplar']
                    if 1 <= num_pos <= 25 and len(nom_ej) > 1 and not any(p in nom_ej.lower() for p in palabras_excluir):
                        formato_ej = f"{num_pos} - {nom_ej.title()}"
                        if formato_ej not in banco_temporal[carrera_actual_detectada]:
                            banco_temporal[carrera_actual_detectada].append(formato_ej)

        if banco_temporal:
            for c_key in banco_temporal:
                banco_temporal[c_key].sort(key=lambda x: int(re.match(r'^(\d+)', x).group(1)))
            st.session_state.banco_caballos_por_carrera = banco_temporal
            st.session_state.detalles_carreras = detalles_temporal
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
        st.error(f"Error procesando el texto: {e}")
    return False

if not st.session_state.remates:
    for i in range(1, 11):
        carr_nombre = f"Carrera {i}"
        st.session_state.banco_caballos_por_carrera[carr_nombre] = [f"{j} - Ejemplar {j}" for j in range(1, 11)]
        st.session_state.remates[carr_nombre] = {f"{j} - Ejemplar {j}": {"jugador": "Sin Postor", "monto": 0.0} for j in range(1, 11)}
        st.session_state.detalles_carreras[carr_nombre] = {"condicion": "Condición estándar", "distancia": "1200 mts", "hora": "02:00 PM"}

lista_carreras_disponibles = list(st.session_state.remates.keys())

if not st.session_state.carreras_activas_remate and lista_carreras_disponibles:
    st.session_state.carreras_activas_remate = list(lista_carreras_disponibles)

if not st.session_state.carreras_habilitadas_dupleta and lista_carreras_disponibles:
    st.session_state.carreras_habilitadas_dupleta = list(lista_carreras_disponibles)

# --- MENÚ PRINCIPAL HORIZONTAL (MÁS COMPACTO) ---
col_menu1, col_menu2, col_menu3 = st.columns(3, gap="small")

with col_menu1:
    if st.button("🏇 REMATES", key="menu_btn_remates_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Remates" else "secondary"):
        st.session_state.menu_principal_opcion = "Remates"
        st.rerun()

with col_menu2:
    if st.button("🎟️ DUPLETAS", key="menu_btn_dupletas_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Dupletas" else "secondary"):
        st.session_state.menu_principal_opcion = "Dupletas"
        st.rerun()

with col_menu3:
    if st.button("📊 CUENTAS", key="menu_btn_cuentas_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Cuentas" else "secondary"):
        st.session_state.menu_principal_opcion = "Cuentas"
        st.rerun()

st.markdown("<hr style='margin: 0.5rem 0; border-color: #21262d;'>", unsafe_allow_html=True)

# --- BARRA LATERAL (IZQUIERDA) ---
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

with st.sidebar.expander("🔒 Zona Administrador", expanded=False):
    es_admin_activo = (st.session_state.menu_principal_opcion == "🔒 Zona Admin")
    if st.button("⚙️ Entrar a Zona Admin", key="sb_btn_ir_admin", use_container_width=True, type="primary" if es_admin_activo else "secondary"):
        st.session_state.menu_principal_opcion = "🔒 Zona Admin"
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
            
            num_carreras = len(carreras_filtradas_visibles)
            cols_carreras = st.columns(num_carreras if num_carreras > 0 else 1, gap="small")
            for idx, c_nombre in enumerate(carreras_filtradas_visibles):
                abreviatura = obtener_abreviatura_carrera(c_nombre)
                es_activa = (c_nombre == carr_activa)
                with cols_carreras[idx]:
                    if st.button(abreviatura, key=f"rem_btn_sel_carr_{idx}", use_container_width=True, type="primary" if es_activa else "secondary"):
                        st.session_state["carrera_remate_activa_seleccionada"] = c_nombre
                        st.rerun()

            st.markdown(f"---")

            if carr_activa in st.session_state.imagenes_carreras:
                st.image(st.session_state.imagenes_carreras[carr_activa], caption=f"Imagen oficial - {carr_activa}", use_container_width=True)

            carrera_cerrada = st.session_state.carreras_cerradas_remate.get(carr_activa, False)
            if carrera_cerrada:
                st.error(f"🔴 La carrera **{carr_activa}** se encuentra **CERRADA** para nuevas pujas.")
            else:
                st.success(f"🟢 Panel activo y abierto para: **{carr_activa}**")

            # --- MOSTRAR CONDICIÓN, HORA Y DISTANCIA EN LA TABLA DE REMATES ---
            detalles_carr = st.session_state.detalles_carreras.get(carr_activa, {"condicion": "Condición general", "distancia": "Por definir", "hora": "Por definir"})
            st.markdown(f"""
                <div class="carrera-condicion-card">
                    <b>🏁 {carr_activa}</b><br>
                    🏷️ <b>Condición:</b> {detalles_carr.get('condicion', 'N/A')}<br>
                    📏 <b>Distancia:</b> {detalles_carr.get('distancia', 'N/A')} &nbsp;|&nbsp; ⏰ <b>Hora:</b> {detalles_carr.get('hora', 'N/A')}
                </div>
            """, unsafe_allow_html=True)

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
            altura_dinamica = min(max(150, (cantidad_filas * 38) + 60), 450)
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
                        cols_fila = st.columns(cols_ejemplares, gap="small")
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
            st.markdown(f"---")
            col_carr, col_img, col_cab = st.columns([2, 1.2, 2])
            
            with col_carr:
                carr_leg = st.selectbox(f"Carrera {i+1}", carreras_habilitadas, key=f"dup_sel_carrera_{i}")
            
            with col_img:
                st.markdown("<p style='font-size: 11px; margin-bottom: 2px; color: #8b949e;'>Imagen Carrera</p>", unsafe_allow_html=True)
                if carr_leg in st.session_state.imagenes_carreras:
                    st.image(st.session_state.imagenes_carreras[carr_leg], use_container_width=True)
                else:
                    st.markdown("<div style='background: #161b22; border: 1px dashed #30363d; padding: 15px; text-align: center; font-size: 10px; border-radius: 4px; color: #8b949e;'>Sin Imagen</div>", unsafe_allow_html=True)
            
            with col_cab:
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
                legs_ordenadas = sorted(seleccion_legs, key=lambda x: x['carrera'])
                firma_combinacion = tuple((l['carrera'], l['ejemplar']) for l in legs_ordenadas)

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
# 3. MÓDULO DE CUENTAS (Público)
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
# 4. ZONA DE ADMINISTRADOR (Centralizada y Persistente)
# =========================================================================
elif menu_principal_opcion == "🔒 Zona Admin":
    st.markdown("<div class='subasta-header'>🔒 Zona de Administrador</div>", unsafe_allow_html=True)
    
    opciones_admin_tabs = ["✍️ Banco", "🏁 Cierre de Remates", "📊 Saldos Usuarios", "🖼️ Imágenes Carrera", "📄 Importar Web/Texto"]
    
    cols_adm_tabs = st.columns(len(opciones_admin_tabs), gap="small")
    for idx, tab_nombre in enumerate(opciones_admin_tabs):
        with cols_adm_tabs[idx]:
            es_tab_activa = (st.session_state.admin_tab_seleccionada == tab_nombre)
            if st.button(tab_nombre, key=f"adm_tab_btn_{idx}", use_container_width=True, type="primary" if es_tab_activa else "secondary"):
                st.session_state.admin_tab_seleccionada = tab_nombre
                st.rerun()

    st.markdown("<hr style='margin: 0.5rem 0; border-color: #30363d;'>", unsafe_allow_html=True)
    tab_actual = st.session_state.admin_tab_seleccionada

    if tab_actual == "✍️ Banco":
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

    elif tab_actual == "🏁 Cierre de Remates":
        st.markdown("### 🏁 Cierre Estricto y Liquidación de Remates")
        carr_seleccionada_liq = st.selectbox("Gestionar Carrera", lista_carreras_disponibles, key="adm_liq_sel_carrera")

        with st.container(border=True):
            c_cerrada_actual = st.session_state.carreras_cerradas_remate.get(carr_seleccionada_liq, False)
            
            col_cz1, col_cz2 = st.columns(2)
            with col_cz1:
                fecha_cierre_adm = st.date_input("Fecha límite", value=ahora_dt.date(), key=f"adm_f_cierre_{carr_seleccionada_liq}")
            with col_cz2:
                hora_cierre_adm = st.time_input("Hora límite", value=datetime.now().time(), key=f"adm_h_cierre_{carr_seleccionada_liq}")
            
            if st.button("💾 Guardar Hora de Cierre Estricto", key=f"adm_btn_guardar_h_{carr_seleccionada_liq}", use_container_width=True):
                dt_cierre_estricto = datetime.combine(fecha_cierre_adm, hora_cierre_adm)
                st.session_state.fechas_horas_cierre_remate[carr_seleccionada_liq] = dt_cierre_estricto
                st.session_state.estado_conteo_carrera[carr_seleccionada_liq] = "INACTIVO"
                st.toast(f"✅ Cierre estricto guardado para {carr_seleccionada_liq}")
                st.rerun()

            st.markdown("---")
            if not c_cerrada_actual:
                if st.button("🔒 Cerrar Remate Manualmente", key=f"adm_liq_cerrar_{carr_seleccionada_liq}", use_container_width=True, type="primary"):
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

            st.markdown("---")
            if carr_seleccionada_liq in st.session_state.historial_ganadores:
                st.success("✅ Esta carrera ya se encuentra liquidada.")
            else:
                pote_carr_total = sum([info['monto'] for info in st.session_state.remates[carr_seleccionada_liq].values()])
                monto_casa_calc = pote_carr_total * (porcentaje_casa / 100)
                premio_final_liq = pote_carr_total - monto_casa_calc + st.session_state.get(f"rem_pote_inc_{carr_seleccionada_liq}", 0.0)
                
                caballo_ganador_elegido = st.selectbox("Seleccionar Ejemplar Ganador", list(st.session_state.remates[carr_seleccionada_liq].keys()), key=f"adm_liq_ganador_{carr_seleccionada_liq}")
                
                if st.button("🎯 Liquidar Premio de la Carrera", key=f"adm_liq_btn_{carr_seleccionada_liq}", use_container_width=True, type="primary"):
                    info_g = st.session_state.remates[carr_seleccionada_liq][caballo_ganador_elegido]
                    if info_g['jugador'] != "Sin Postor":
                        if info_g['jugador'] not in st.session_state.cuentas:
                            st.session_state.cuentas[info_g['jugador']] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                        st.session_state.cuentas[info_g['jugador']]['Premios'] += premio_final_liq
                    st.session_state.ganancia_casa += monto_casa_calc
                    st.session_state.historial_ganadores[carr_seleccionada_liq] = {"Ganador": info_g['jugador'], "Premio": formatear_bs(premio_final_liq)}
                    st.success("¡Premio liquidado con éxito!")
                    st.rerun()

    elif tab_actual == "📊 Saldos Usuarios":
        st.markdown("### 📊 Saldos y Cuentas de Todos los Usuarios")
        datos_cuentas_adm = []
        for jugador, vals in st.session_state.cuentas.items():
            pujas, premios, abonos = vals['Pujas'], vals['Premios'], vals['Abonos']
            balance_neto = pujas - abonos - premios
            datos_cuentas_adm.append({"Jugador": jugador, "Compras": formatear_bs(pujas), "Premios": formatear_bs(premios), "Abonos/Pagos": formatear_bs(abonos), "Neto a Pagar": formatear_bs(balance_neto)})
        st.dataframe(pd.DataFrame(datos_cuentas_adm), use_container_width=True, hide_index=True)
        st.metric("Ganancia Total Casa", formatear_bs(st.session_state.ganancia_casa))

        st.markdown("---")
        st.markdown("#### 💵 Registrar Abono o Pago a Usuario")
        col_ab1, col_ab2, col_ab3 = st.columns(3, gap="small")
        with col_ab1:
            jugador_abonar = st.selectbox("Usuario", st.session_state.lista_jugadores, key="adm_abono_jugador")
        with col_ab2:
            monto_abono = st.number_input("Monto Abono (Bs.)", min_value=0.0, step=100.0, key="adm_abono_monto")
        with col_ab3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ Aplicar Abono", key="adm_btn_aplicar_abono", use_container_width=True, type="primary"):
                if jugador_abonar not in st.session_state.cuentas:
                    st.session_state.cuentas[jugador_abonar] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                st.session_state.cuentas[jugador_abonar]['Abonos'] += monto_abono
                st.toast(f"✅ Abono de {formatear_bs(monto_abono)} registrado a {jugador_abonar}")
                st.rerun()

    elif tab_actual == "🖼️ Imágenes Carrera":
        st.markdown("### 🖼️ Cargar Imagen Representativa por Carrera (Dupletas y Remates)")
        carr_img_sel = st.selectbox("Seleccionar Carrera", lista_carreras_disponibles, key="adm_img_sel_carr")
        
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
                st.toast("🗑️ Removida")
                st.rerun()

    elif tab_actual == "📄 Importar Web/Texto":
        st.markdown("### 🌐 Importar Inscritos desde una Página Web")
        url_web = st.text_input("🔗 URL de la página de inscritos:", placeholder="https://ejemplo.com/programa", key="input_url_web_bs")
        if st.button("🌐 Extraer e Importar desde la URL", key="btn_extraer_bs_url", use_container_width=True, type="primary"):
            if url_web.strip():
                try:
                    with st.spinner("Leyendo la página web..."):
                        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                        resp = requests.get(url_web.strip(), headers=headers, timeout=15)
                        if resp.status_code == 200:
                            soup = BeautifulSoup(resp.text, 'html.parser')
                            for script in soup(["script", "style"]):
                                script.extract()
                            texto_web = soup.get_text(separator='\n')
                            
                            if procesar_texto_flexible(texto_web):
                                st.success("✅ ¡Carreras y ejemplares extraídos con éxito desde la URL!")
                                st.rerun()
                            else:
                                st.warning("⚠️ No se pudieron detectar carreras automáticamente con el formato de la página. Usa el cuadro de texto de abajo para pegar el contenido copiado directamente.")
                        else:
                            st.error(f"❌ Error de acceso web. Código HTTP: {resp.status_code}")
                except Exception as e:
                    st.error(f"❌ Error al conectar: {e}")
            else:
                st.warning("⚠️ Ingresa una URL válida.")

        st.markdown("---")
        st.markdown("O pega el texto copiado de la página web:")
        texto_copiado_web = st.text_area(
            "Contenido copiado:",
            value="",
            height=200,
            key="text_area_web_copiado",
            placeholder="Primera Carrera - Condición: Clásico - 1.200 mts - 02:00 PM\n1 - Rey David\n2 - Gran Amigo"
        )
        if st.button("🚀 Procesar Contenido Pegado", key="btn_procesar_texto_pegado", use_container_width=True, type="primary"):
            if texto_copiado_web.strip():
                if procesar_texto_flexible(texto_copiado_web):
                    st.success("✅ ¡Inscritos organizados por carrera con éxito!")
                    st.rerun()
            else:
                st.warning("⚠️ El campo de texto está vacío.")
