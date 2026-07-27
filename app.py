import streamlit as st
import streamlit.components.v1 as componentsimport streamlit as st
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

# --- ESTILOS CSS (DISEÑO HORIZONTAL PARA MÓVIL) ---
st.markdown("""
    <style>
    .stApp {
        background-color: #080a0f;
        color: #f0f6fc;
    }
    div[data-testid="stTabs"] {
        display: none !important;
    }
    
    /* Adaptación horizontal de radios en móviles */
    div[data-testid="stRadio"] > div {
        display: flex !important;
        flex-direction: row !important;
        overflow-x: auto !important;
        white-space: nowrap !important;
        gap: 6px !important;
        padding-bottom: 4px !important;
        -webkit-overflow-scrolling: touch;
    }
    
    div[data-testid="stRadio"] label {
        background-color: #161b22 !important;
        color: #f0f6fc !important;
        border: 1px solid #30363d !important;
        padding: 6px 14px !important;
        border-radius: 20px !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        cursor: pointer;
        flex-shrink: 0;
        margin: 0 !important;
    }
    
    div[data-testid="stRadio"] label:has(input:checked) {
        background-color: #ff4757 !important;
        color: #ffffff !important;
        border-color: #ff4757 !important;
    }

    /* Ocultar botones de radio reales de Streamlit */
    div[data-testid="stRadio"] input[type="radio"] {
        display: none;
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
    .subasta-header {
        font-size: clamp(14px, 3.5vw, 18px);
        font-weight: 800;
        color: #f1e05a;
        margin-bottom: 3px;
        border-bottom: 2px solid #f1e05a;
        padding-bottom: 2px;
    }
    </style>
""", unsafe_allow_html=True)

# --- CABECERA SUPERIOR ---
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
        st.session_state.menu_principal_opcion = "🏇 REMATES"
    if 'sub_remate_opcion' not in st.session_state:
        st.session_state.sub_remate_opcion = "⚡ En Vivo"
    if 'carrera_seleccionada' not in st.session_state:
        st.session_state.carrera_seleccionada = "C1"
    if 'usuario_activo' not in st.session_state:
        st.session_state.usuario_activo = "LUIS"
    if 'lista_jugadores' not in st.session_state:
        st.session_state.lista_jugadores = cargar_jugadores_base()

inicializar_estado_global()

# --- MENÚ PRINCIPAL HORIZONTAL ---
menu_opciones = ["🏇 REMATES", "🎟️ DUPLETAS", "📊 CUENTAS"]
menu_seleccionado = st.radio(
    "",
    options=menu_opciones,
    horizontal=True,
    key="menu_principal_radio",
    label_visibility="collapsed"
)

# --- SUBMENU HORIZONTAL (SI ESTÁ EN REMATES) ---
if "REMATES" in menu_seleccionado:
    submenu_opciones = ["⏱️ Adelantados", "🙈 Ciegos", "⚡ En Vivo"]
    sub_seleccionado = st.radio(
        "",
        options=submenu_opciones,
        horizontal=True,
        key="sub_remate_radio",
        label_visibility="collapsed"
    )
    
    st.markdown(f"<div class='subasta-header'>🐴 Modo de Remate: {sub_seleccionado.upper()}</div>", unsafe_allow_html=True)

    # --- SELECCIÓN DE CARRERA HORIZONTAL (DESLIZANTE) ---
    st.markdown("<small style='color: #8b949e; font-weight: 700;'>Seleccionar Carrera:</small>", unsafe_allow_html=True)
    carreras_disponibles = [f"C{i}" for i in range(1, 11)]
    
    carrera_activa = st.radio(
        "",
        options=carreras_disponibles,
        horizontal=True,
        key="carrera_selector_radio",
        label_visibility="collapsed"
    )

    st.info(f"Carrera activa: **{carrera_activa}** | Modo: **{sub_seleccionado}**")

elif "DUPLETAS" in menu_seleccionado:
    st.subheader("🎟️ Módulo de Dupletas")
    st.write("Configuración e historial de apuestas dobles.")

elif "CUENTAS" in menu_seleccionado:
    st.subheader("📊 Módulo de Cuentas")
    st.write("Resumen de saldos, premios y abonos.")
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

# --- ESTILOS CSS (DISEÑO HORIZONTAL PARA MÓVIL) ---
st.markdown("""
    <style>
    .stApp {
        background-color: #080a0f;
        color: #f0f6fc;
    }
    div[data-testid="stTabs"] {
        display: none !important;
    }
    
    /* Adaptación horizontal de radios en móviles */
    div[data-testid="stRadio"] > div {
        display: flex !important;
        flex-direction: row !important;
        overflow-x: auto !important;
        white-space: nowrap !important;
        gap: 6px !important;
        padding-bottom: 4px !important;
        -webkit-overflow-scrolling: touch;
    }
    
    div[data-testid="stRadio"] label {
        background-color: #161b22 !important;
        color: #f0f6fc !important;
        border: 1px solid #30363d !important;
        padding: 6px 14px !important;
        border-radius: 20px !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        cursor: pointer;
        flex-shrink: 0;
        margin: 0 !important;
    }
    
    div[data-testid="stRadio"] label:has(input:checked) {
        background-color: #ff4757 !important;
        color: #ffffff !important;
        border-color: #ff4757 !important;
    }

    /* Ocultar botones de radio reales de Streamlit */
    div[data-testid="stRadio"] input[type="radio"] {
        display: none;
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
    .subasta-header {
        font-size: clamp(14px, 3.5vw, 18px);
        font-weight: 800;
        color: #f1e05a;
        margin-bottom: 3px;
        border-bottom: 2px solid #f1e05a;
        padding-bottom: 2px;
    }
    </style>
""", unsafe_allow_html=True)

# --- CABECERA SUPERIOR ---
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
        st.session_state.menu_principal_opcion = "🏇 REMATES"
    if 'sub_remate_opcion' not in st.session_state:
        st.session_state.sub_remate_opcion = "⚡ En Vivo"
    if 'carrera_seleccionada' not in st.session_state:
        st.session_state.carrera_seleccionada = "C1"
    if 'usuario_activo' not in st.session_state:
        st.session_state.usuario_activo = "LUIS"
    if 'lista_jugadores' not in st.session_state:
        st.session_state.lista_jugadores = cargar_jugadores_base()

inicializar_estado_global()

# --- MENÚ PRINCIPAL HORIZONTAL ---
menu_opciones = ["🏇 REMATES", "🎟️ DUPLETAS", "📊 CUENTAS"]
menu_seleccionado = st.radio(
    "",
    options=menu_opciones,
    horizontal=True,
    key="menu_principal_radio",
    label_visibility="collapsed"
)

# --- SUBMENU HORIZONTAL (SI ESTÁ EN REMATES) ---
if "REMATES" in menu_seleccionado:
    submenu_opciones = ["⏱️ Adelantados", "🙈 Ciegos", "⚡ En Vivo"]
    sub_seleccionado = st.radio(
        "",
        options=submenu_opciones,
        horizontal=True,
        key="sub_remate_radio",
        label_visibility="collapsed"
    )
    
    st.markdown(f"<div class='subasta-header'>🐴 Modo de Remate: {sub_seleccionado.upper()}</div>", unsafe_allow_html=True)

    # --- SELECCIÓN DE CARRERA HORIZONTAL (DESLIZANTE) ---
    st.markdown("<small style='color: #8b949e; font-weight: 700;'>Seleccionar Carrera:</small>", unsafe_allow_html=True)
    carreras_disponibles = [f"C{i}" for i in range(1, 11)]
    
    carrera_activa = st.radio(
        "",
        options=carreras_disponibles,
        horizontal=True,
        key="carrera_selector_radio",
        label_visibility="collapsed"
    )

    st.info(f"Carrera activa: **{carrera_activa}** | Modo: **{sub_seleccionado}**")

elif "DUPLETAS" in menu_seleccionado:
    st.subheader("🎟️ Módulo de Dupletas")
    st.write("Configuración e historial de apuestas dobles.")

elif "CUENTAS" in menu_seleccionado:
    st.subheader("📊 Módulo de Cuentas")
    st.write("Resumen de saldos, premios y abonos.")
