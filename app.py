import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import re
import base64
import requests
import io
import json
import time
from bs4 import BeautifulSoup
from datetime import datetime, time as dtime, timedelta, timezone
from zoneinfo import ZoneInfo
from pypdf import PdfReader

# Configuración de pantalla completa
st.set_page_config(page_title="WOLF READY TO RUN", layout="wide", page_icon="🐺")

# --- HORA LOCAL DE VENEZUELA ---
def obtener_hora_venezuela_local():
    try:
        zona_venezuela = ZoneInfo("America/Caracas")
        return datetime.now(zona_venezuela).replace(tzinfo=None)
    except Exception:
        pass
    tz_venezuela = timezone(timedelta(hours=-4))
    return datetime.now(tz_venezuela).replace(tzinfo=None)

def formatear_bs(monto):
    numero_formateado = f"{monto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"Bs. {numero_formateado}"

# --- SISTEMA DE PERSISTENCIA GLOBAL (JSON) PARA SINCRONIZAR A TODOS LOS USUARIOS ---
DB_FILE = "state_db.json"

def cargar_estado_global(forzar_recarga=False):
    default_state = {
        'menu_principal_opcion': "Remates",
        'sub_remate_opcion': "En Vivo",
        'sub_dupleta_opcion': "Dupleta",
        'usuario_activo': "CASA",
        'lista_usuarios': ["CASA"],
        'banco_caballos_por_carrera': {},
        'remates_por_modalidad': {"Adelantados": {}, "Ciegos": {}, "En Vivo": {}},
        'historial_ganadores_por_modalidad': {"Adelantados": {}, "Ciegos": {}, "En Vivo": {}},
        'ejemplares_retirados': {},
        'ejemplares_no_valido': {},
        'detalles_carreras': {},
        'carreras_cerradas_remate': {},
        'remates_cargados_en_cuentas': {},
        'fechas_horas_inicio_remate_modalidad': {},
        'fechas_horas_cierre_remate_modalidad': {},
        'fechas_horas_inicio_modalidad_multiple': {},
        'fechas_horas_cierre_modalidad_multiple': {},
        'estado_conteo_carrera_modalidad': {},
        'tiempo_inicio_conteo_modalidad': {},
        'cuentas': {"CASA": {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}},
        'historial_jugadas': [],
        'ganancia_casa': 0.0,
        'dupletas_tickets': [],
        'tripleta_tickets': [],
        'polla_tickets': [],
        'carreras_habilitadas_dupleta': [],
        'carreras_habilitadas_tripleta': [],
        'carreras_habilitadas_polla': [],
        'config_montos_especiales': {"Dupleta": 500.0, "Tripleta": 500.0, "6 En Linea": 1000.0},
        'dupleta_bloqueada': False,
        'carreras_activas_remate': [],
        'carreras_por_modalidad': {"Adelantados": [], "Ciegos": [], "En Vivo": []},
        'total_carreras_semana': 10,
        'url_video_en_vivo': "",
        'admin_tab_seleccionada': "✍️ Caballos",
        'imagenes_carreras': {},
        'mapeo_ciegos_carreras': {}
    }
    
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in default_state.items():
                    if k not in st.session_state or forzar_recarga:
                        val_cargado = data.get(k, v)
                        if k in ['fechas_horas_inicio_remate_modalidad', 'fechas_horas_cierre_remate_modalidad', 'fechas_horas_inicio_modalidad_multiple', 'fechas_horas_cierre_modalidad_multiple', 'tiempo_inicio_conteo_modalidad'] and isinstance(val_cargado, dict):
                            dict_restaurado = {}
                            for sub_k, sub_v in val_cargado.items():
                                if isinstance(sub_v, str):
                                    try:
                                        dict_restaurado[sub_k] = datetime.fromisoformat(sub_v)
                                    except Exception:
                                        dict_restaurado[sub_k] = sub_v
                                else:
                                    dict_restaurado[sub_k] = sub_v
                            st.session_state[k] = dict_restaurado
                        else:
                            st.session_state[k] = val_cargado
        except Exception:
            for k, v in default_state.items():
                if k not in st.session_state:
                    st.session_state[k] = v
    else:
        for k, v in default_state.items():
            if k not in st.session_state:
                st.session_state[k] = v

def guardar_estado_global():
    keys_to_save = [
        'menu_principal_opcion', 'sub_remate_opcion', 'sub_dupleta_opcion', 'usuario_activo',
        'lista_usuarios', 'banco_caballos_por_carrera', 'remates_por_modalidad', 'historial_ganadores_por_modalidad',
        'ejemplares_retirados', 'ejemplares_no_valido', 'detalles_carreras', 'carreras_cerradas_remate',
        'remates_cargados_en_cuentas', 'fechas_horas_inicio_remate_modalidad', 'fechas_horas_cierre_remate_modalidad',
        'fechas_horas_inicio_modalidad_multiple', 'fechas_horas_cierre_modalidad_multiple', 
        'estado_conteo_carrera_modalidad', 'tiempo_inicio_conteo_modalidad', 'cuentas', 'historial_jugadas', 'ganancia_casa',
        'dupletas_tickets', 'tripleta_tickets', 'polla_tickets', 'carreras_habilitadas_dupleta',
        'carreras_habilitadas_tripleta', 'carreras_habilitadas_polla', 'config_montos_especiales',
        'dupleta_bloqueada', 'carreras_activas_remate', 'carreras_por_modalidad',
        'total_carreras_semana', 'url_video_en_vivo', 'imagenes_carreras', 'admin_tab_seleccionada',
        'mapeo_ciegos_carreras'
    ]
    data = {}
    for k in keys_to_save:
        if k in st.session_state:
            val = st.session_state[k]
            if isinstance(val, dict):
                dict_limpio = {}
                for sub_k, sub_v in val.items():
                    if isinstance(sub_v, datetime):
                        dict_limpio[sub_k] = sub_v.isoformat()
                    else:
                        dict_limpio[sub_k] = sub_v
                data[k] = dict_limpio
            elif isinstance(val, datetime):
                data[k] = val.isoformat()
            else:
                data[k] = val
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

cargar_estado_global()

# --- SCRIPT JS PARA AUTO-ACTUALIZACIÓN Y CONTROL DE BARRA LATERAL ---
usuario_actual_sesion = st.session_state.get("usuario_activo", "CASA")

if usuario_actual_sesion == "CASA":
    components.html("""
        <script>
            function sincronizacionEnVivo() {
                const doc = window.parent.document;
                const selectors = [
                    'header[data-testid="stHeader"]',
                    'footer',
                    '.stDeployButton',
                    'div[data-testid="stStatusWidget"]',
                    '[data-testid="stToolbar"]',
                    '#MainMenu',
                    'a[href*="streamlit.io"]'
                ];
                selectors.forEach(selector => {
                    doc.querySelectorAll(selector).forEach(el => {
                        if (el) {
                            el.style.display = 'none';
                            el.style.visibility = 'hidden';
                            el.style.opacity = '0';
                            el.remove();
                        }
                    });
                });

                let tuercaBtn = doc.getElementById('custom-tuerca-sidebar-btn');
                if (!tuercaBtn) {
                    tuercaBtn = doc.createElement('button');
                    tuercaBtn.id = 'custom-tuerca-sidebar-btn';
                    tuercaBtn.innerHTML = '⚙️';
                    tuercaBtn.title = 'Abrir / Cerrar Barra Lateral';
                    
                    tuercaBtn.style.position = 'fixed';
                    tuercaBtn.style.top = '10px';
                    tuercaBtn.style.right = '15px';
                    tuercaBtn.style.zIndex = '999999';
                    tuercaBtn.style.background = '#161b22';
                    tuercaBtn.style.border = '1px solid #30363d';
                    tuercaBtn.style.borderRadius = '8px';
                    tuercaBtn.style.fontSize = '20px';
                    tuercaBtn.style.width = '42px';
                    tuercaBtn.style.height = '42px';
                    tuercaBtn.style.cursor = 'pointer';
                    tuercaBtn.style.display = 'flex';
                    tuercaBtn.style.alignItems = 'center';
                    tuercaBtn.style.justifyContent = 'center';
                    tuercaBtn.style.boxShadow = '0px 4px 12px rgba(0,0,0,0.5)';
                    tuercaBtn.style.transition = 'transform 0.2s ease, background 0.2s ease';

                    tuercaBtn.onclick = function() {
                        const nativeToggle = doc.querySelector('[data-testid="stSidebarCollapseButton"] button') || 
                                             doc.querySelector('[data-testid="collapsedControl"] button') ||
                                             doc.querySelector('button[aria-label="Close sidebar"]') ||
                                             doc.querySelector('button[aria-label="Open sidebar"]');
                        
                        if (nativeToggle) {
                            nativeToggle.click();
                        } else {
                            const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
                            if (sidebar) {
                                const isHidden = window.getComputedStyle(sidebar).display === 'none' || 
                                                 sidebar.style.transform.includes('-100%');
                                if (isHidden) {
                                    sidebar.style.transform = 'none';
                                    sidebar.style.visibility = 'visible';
                                    sidebar.style.display = 'block';
                                } else {
                                    sidebar.style.transform = 'translateX(-100%)';
                                    sidebar.style.visibility = 'hidden';
                                }
                            }
                        }
                    };

                    doc.body.appendChild(tuercaBtn);
                }
            }
            setInterval(sincronizacionEnVivo, 200);
        </script>
    """, height=0, width=0)
else:
    components.html("""
        <script>
            const doc = window.parent.document;
            let tuercaBtn = doc.getElementById('custom-tuerca-sidebar-btn');
            if (tuercaBtn) { tuercaBtn.remove(); }
            const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
            if (sidebar) {
                sidebar.setAttribute('aria-expanded', 'false');
                sidebar.style.transform = 'translateX(-100%)';
                sidebar.style.visibility = 'hidden';
                sidebar.style.display = 'none';
            }
        </script>
    """, height=0, width=0)

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
    "1001397336_preview_rev_1.png",
    "1001397336_preview_rev_1.jpg",
    "1001397336.jpg",
    "1001397336.png",
    "1001394095_preview_rev_1_2.png",
    "1001394095_preview_rev_1_2.jpg",
    "logo.png",
    "logo.jpg"
]

img_b64 = get_image_base64(nombres_archivos)

if img_b64:
    logo_display = f'<img src="data:image/png;base64,{img_b64}" class="header-logo-img" />'
else:
    logo_display = '<span style="color: #f1c40f; font-size: 38px; font-weight: 900; font-style: italic; letter-spacing: 1.5px;">CALIFORNIA CHROME</span>'

# --- ESTILOS CSS GENERALES ---
st.markdown("""
    <style>
    * { box-sizing: border-box !important; }
    .stApp { background-color: #080a0f; color: #f0f6fc; overflow-x: hidden !important; }
    [data-testid="stSidebar"] { min-width: 360px !important; max-width: 360px !important; }
    [data-testid="stSidebar"] > div:first-child { width: 360px !important; padding-left: 1.2rem !important; padding-right: 1.2rem !important; }
    [data-testid="stToolbar"] { display: none !important; visibility: hidden !important; opacity: 0 !important; pointer-events: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    footer, #MainMenu { visibility: hidden !important; display: none !important; }
    .block-container { padding-top: 0.4rem !important; padding-bottom: 2rem !important; padding-left: 0.5rem !important; padding-right: 0.5rem !important; max-width: 100% !important; margin: 0 auto !important; overflow-x: hidden !important; }
    div[data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; overflow-x: auto !important; overflow-y: hidden !important; -webkit-overflow-scrolling: touch !important; width: 100% !important; gap: 6px !important; padding-bottom: 6px !important; scrollbar-width: thin; }
    div[data-testid="stHorizontalBlock"] > div { flex: 0 0 auto !important; width: auto !important; min-width: 110px !important; max-width: none !important; }
    .carreras-scroll-container div[data-testid="stHorizontalBlock"] > div { min-width: 55px !important; width: 55px !important; }
    div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"]:has(button) { gap: 4px !important; margin-top: -18px !important; margin-bottom: -18px !important; }
    div[data-testid="column"]:has(button) { padding: 0px 2px !important; }
    .stButton button { border-radius: 6px !important; font-weight: 700 !important; padding: 0.2rem 0.4rem !important; min-height: 38px !important; font-size: 12px !important; letter-spacing: 0.2px; white-space: nowrap !important; width: 100% !important; }
    .subasta-header { font-size: clamp(14px, 3.5vw, 18px); font-weight: 800; color: #f1e05a; margin-bottom: 4px; border-bottom: 2px solid #f1e05a; padding-bottom: 3px; }
    .timer-box { background-color: #161b22; border: 1px solid #ff4757; padding: 6px; border-radius: 6px; text-align: center; font-size: clamp(12px, 3vw, 15px); font-weight: bold; color: #ff4757; margin-bottom: 8px; }
    .carrera-condicion-card { background-color: #161b22; border: 1px solid #30363d; padding: 8px 12px; border-radius: 6px; font-size: 12px; color: #f0f6fc; margin-bottom: 10px; line-height: 1.4; word-break: break-word; }
    .incentivo-llamativo { background: linear-gradient(135deg, #1f1c2c 0%, #923d41 100%); border: 2px dashed #00ffff; padding: 10px 16px; border-radius: 12px; text-align: center; margin: 10px 0; box-shadow: 0px 0px 15px rgba(0, 255, 255, 0.4); }
    .incentivo-llamativo-monto { color: #ffffff; font-size: 22px; font-weight: 900; letter-spacing: 0.5px; text-shadow: 2px 2px 4px #000000; }
    @keyframes parpadeoGanador { 0% { transform: scale(1); box-shadow: 0 0 15px #f1c40f, inset 0 0 15px #f1c40f; } 50% { transform: scale(1.02); box-shadow: 0 0 35px #00ffff, inset 0 0 25px #00ffff; } 100% { transform: scale(1); box-shadow: 0 0 15px #f1c40f, inset 0 0 15px #f1c40f; } }
    .ganador-banner-epic { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); border: 3px solid #f1c40f; border-radius: 14px; padding: 16px; text-align: center; margin: 12px 0; animation: parpadeoGanador 2s infinite ease-in-out; }
    .ganador-titulo-epic { color: #00ffff; font-size: 14px; font-weight: 900; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 6px; text-shadow: 0 0 8px rgba(0, 255, 255, 0.8); }
    .ganador-nombre-epic { color: #f1c40f; font-size: 24px; font-weight: 900; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 4px; text-shadow: 2px 2px 6px #000000, 0 0 12px rgba(241, 196, 15, 0.9); }
    .ganador-premio-epic { color: #2ed573; font-size: 18px; font-weight: 900; text-shadow: 1px 1px 4px #000000; }
    .ticket-jugador-card { background: #0d1117; border: 2px solid #30363d; border-radius: 10px; padding: 12px 16px; margin-bottom: 10px; box-shadow: 0px 4px 12px rgba(0,0,0,0.5); }
    .ticket-header-row { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #30363d; padding-bottom: 6px; margin-bottom: 8px; font-size: 12px; font-weight: 800; color: #f1c40f; }
    .ticket-body-row { font-size: 13px; color: #f0f6fc; margin-bottom: 4px; font-weight: 600; }
    .header-container-modern { background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); border: 1px solid #30363d; border-radius: 12px; padding: 14px 18px; margin-bottom: 10px; box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.6); display: flex; flex-direction: column; gap: 14px; width: 100%; box-sizing: border-box; }
    .header-top-row { display: flex; justify-content: space-between; align-items: center; width: 100%; gap: 8px; }
    .header-clock-box { display: flex; flex-direction: column; background: #080a0f; border: 1px solid #21262d; padding: 5px 10px; border-radius: 8px; }
    .h-time { color: #00ffff; font-size: 13px; font-weight: 900; letter-spacing: 0.5px; }
    .h-date { color: #8b949e; font-size: 10px; font-weight: 700; }
    .header-user-card { display: flex; align-items: center; gap: 8px; background: #080a0f; border: 1px solid #30363d; padding: 5px 10px; border-radius: 8px; }
    .user-details { display: flex; flex-direction: column; text-align: right; }
    .u-name { color: #f0f6fc; font-size: 12px; font-weight: 800; }
    .u-bal { font-size: 10px; font-weight: 700; }
    .u-avatar-badge { width: 28px; height: 28px; background: #1f6feb; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; }
    .header-bottom-row-logo { text-align: center; border-top: 1px solid #21262d; padding-top: 12px; }
    .header-logo-img { max-height: 120px; width: auto; object-fit: contain; }
    @keyframes pulsoLed { 0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(46, 213, 115, 0.6); } 70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(0, 0, 0, 0); } 100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 0, 0, 0); } }
    .punto-led-pro { width: 8px; height: 8px; background-color: #2ed573; border-radius: 50%; display: inline-block; animation: pulsoLed 2s infinite; }
    .pote-llamativo-box { background: linear-gradient(135deg, #11141d 0%, #1f2937 100%); border: 2px solid #f1c40f; border-radius: 12px; padding: 14px; text-align: center; margin-bottom: 14px; box-shadow: 0px 0px 20px rgba(241, 196, 15, 0.3); }
    .pote-llamativo-titulo { color: #00ffff; font-size: 12px; font-weight: 900; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 4px; }
    .pote-llamativo-monto { color: #f1c40f; font-size: 26px; font-weight: 900; letter-spacing: 0.5px; text-shadow: 2px 2px 6px #000000; }
    </style>
""", unsafe_allow_html=True)

# --- ENCABEZADO DINÁMICO EN TIEMPO REAL (1 SEGUNDO) ---
@st.fragment(run_every=1.0)
def renderizar_encabezado_tiempo_real():
    cargar_estado_global(forzar_recarga=True)
    usuario_en_sesion = st.session_state.usuario_activo
    if usuario_en_sesion not in st.session_state.cuentas:
        st.session_state.cuentas[usuario_en_sesion] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}

    vals_sesion = st.session_state.cuentas[usuario_en_sesion]
    neto_usuario = vals_sesion['Pujas'] - vals_sesion['Abonos'] - vals_sesion['Premios']

    if neto_usuario > 0:
        etiqueta_balance = f"Deuda: {formatear_bs(neto_usuario)}"
        color_balance = "#ff4757"
    elif neto_usuario < 0:
        etiqueta_balance = f"Premio: {formatear_bs(abs(neto_usuario))}"
        color_balance = "#2ed573"
    else:
        etiqueta_balance = "Al día: Bs. 0,00"
        color_balance = "#58a6ff"

    ahora_dt = obtener_hora_venezuela_local()
    hora_texto = ahora_dt.strftime('%I:%M:%S %p')
    fecha_texto = ahora_dt.strftime('%d/%m/%Y')

    header_html = f"""
        <div class="header-container-modern">
            <div class="header-top-row">
                <div class="header-clock-box">
                    <span class="h-time">⚡ {hora_texto}</span>
                    <span class="h-date">📅 {fecha_texto}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div class="header-user-card">
                        <div class="user-details">
                            <div style="display: flex; align-items: center; justify-content: flex-end; gap: 5px;">
                                <span class="u-name">{usuario_en_sesion}</span>
                                <span class="punto-led-pro" title="En Línea"></span>
                            </div>
                            <span class="u-bal" style="color: {color_balance};">{etiqueta_balance}</span>
                        </div>
                        <div class="u-avatar-badge">🐺</div>
                    </div>
                </div>
            </div>
            <div class="header-bottom-row-logo">
                {logo_display}
            </div>
        </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)

renderizar_encabezado_tiempo_real()

def obtener_abreviatura_carrera(nombre_carrera, modo_actual=""):
    if modo_actual == "Ciegos":
        carreras_ciegas = st.session_state.carreras_por_modalidad.get("Ciegos", [])
        if len(carreras_ciegas) >= 2:
            if nombre_carrera == carreras_ciegas[0]:
                return "1V"
            elif nombre_carrera == carreras_ciegas[1]:
                return "6V"
     
    match = re.search(r'\d+', nombre_carrera)
    if match:
        return f"C{match.group(0)}"
    return nombre_carrera[:3].upper()

def generar_tabla_html_remate(remates_dict, retirados_list, no_validos_list=[]):
    html = """
    <style>
        .tabla-referencia { width: 100%; border-collapse: collapse; font-family: sans-serif; background-color: #ffffff; color: #000000; margin-bottom: 10px; table-layout: fixed; }
        .tabla-referencia th { border-top: 2px solid #dfc729; border-bottom: 2px solid #dfc729; padding: 6px 4px; text-align: left; font-weight: 800; background-color: #ffffff; color: #000000; font-size: 11px; overflow: hidden; text-overflow: ellipsis; }
        .tabla-referencia td { border-bottom: 1px solid #dfc729; padding: 6px 4px; background-color: #fbfbfb; color: #111111; font-size: 11px; vertical-align: middle; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .badge-numero { display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; font-weight: bold; font-size: 11px; border-radius: 2px; box-sizing: border-box; }
        .badge-1 { background-color: #e3242b; color: #ffffff; }
        .badge-2 { background-color: #ffffff; color: #000000; border: 1.5px solid #000000; }
        .badge-3 { background-color: #1d11c0; color: #ffffff; }
        .badge-4 { background-color: #f1c40f; color: #000000; }
        .badge-5 { background-color: #28a745; color: #ffffff; }
        .badge-6 { background-color: #000000; color: #ffffff; }
        .badge-7 { background-color: #fd7e14; color: #ffffff; }
        .badge-default { background-color: #6c757d; color: #ffffff; }
        .retirado-row td { background-color: #ffe6e6 !important; color: #990000 !important; text-decoration: line-through; }
        .novale-row td { background-color: #fff3cd !important; color: #856404 !important; font-style: italic; }
    </style>
    <div style="background-color: #ffffff; padding: 3px; border-radius: 6px; overflow-x: auto; width: 100%;">
        <table class="tabla-referencia">
            <thead>
                <tr>
                    <th style="width: 12%;">No</th>
                    <th style="width: 35%;">Ejemplar</th>
                    <th style="width: 25%;">Comprador</th>
                    <th style="width: 28%;">Monto</th>
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
        
        es_retirado = cab in retirados_list
        es_novale = cab in no_validos_list
        
        if es_retirado:
            clase_fila = "retirado-row"
            etiqueta_estado = " (RETIRADO)"
        elif es_novale:
            clase_fila = "novale-row"
            etiqueta_estado = " (NO VALE)"
        else:
            clase_fila = ""
            etiqueta_estado = ""
        
        html += f"""
                <tr class="{clase_fila}">
                    <td><span class="badge-numero {badge_class}">{num}</span></td>
                    <td style="font-weight: 800; font-size: 12px;" title="{nombre_solo.upper()}{etiqueta_estado}">{nombre_solo.upper()}{etiqueta_estado}</td>
                    <td title="{info['jugador']}">{info['jugador']}</td>
                    <td style="font-weight: bold; color: { '#990000' if es_retirado else ('#856404' if es_novale else '#000000') };">{formatear_bs(info['monto'])}</td>
                </tr>
        """
    html += """
            </tbody>
        </table>
    </div>
    """
    return html

if not st.session_state.banco_caballos_por_carrera:
    for i in range(1, st.session_state.total_carreras_semana + 1):
        carr_nombre = f"Carrera {i}"
        st.session_state.banco_caballos_por_carrera[carr_nombre] = [f"{j} - Ejemplar {j}" for j in range(1, 11)]
        st.session_state.detalles_carreras[carr_nombre] = {
            "condicion": "Condición estándar", "distancia": "1200 mts", "hora": "02:00 PM", 
            "monto_fijo_ciego": 500.0, "incentivo_adelantados": 0.0, "incentivo_ciegos": 0.0,
            "incentivo_envivo": 0.0, "hora_cierre_real": "No registrada"
        }

for mod_key in ["Adelantados", "Ciegos", "En Vivo"]:
    if not st.session_state.remates_por_modalidad.get(mod_key):
        st.session_state.remates_por_modalidad[mod_key] = {}
        for i in range(1, st.session_state.total_carreras_semana + 1):
            carr_nombre = f"Carrera {i}"
            st.session_state.remates_por_modalidad[mod_key][carr_nombre] = {f"{j} - Ejemplar {j}": {"jugador": "Sin Postor", "monto": 0.0} for j in range(1, 11)}

lista_carreras_disponibles = list(st.session_state.banco_caballos_por_carrera.keys())

if not st.session_state.carreras_activas_remate and lista_carreras_disponibles:
    st.session_state.carreras_activas_remate = list(lista_carreras_disponibles)
else:
    for c_disp in lista_carreras_disponibles:
        if c_disp not in st.session_state.carreras_activas_remate:
            st.session_state.carreras_activas_remate.append(c_disp)

for mod in ["Adelantados", "Ciegos", "En Vivo"]:
    if not st.session_state.carreras_por_modalidad.get(mod) and lista_carreras_disponibles:
        st.session_state.carreras_por_modalidad[mod] = list(lista_carreras_disponibles)
    else:
        for c_disp in lista_carreras_disponibles:
            if c_disp not in st.session_state.carreras_por_modalidad[mod]:
                st.session_state.carreras_por_modalidad[mod].append(c_disp)

if not st.session_state.carreras_habilitadas_dupleta and lista_carreras_disponibles:
    st.session_state.carreras_habilitadas_dupleta = list(lista_carreras_disponibles)
if not st.session_state.carreras_habilitadas_tripleta and lista_carreras_disponibles:
    st.session_state.carreras_habilitadas_tripleta = list(lista_carreras_disponibles)
if not st.session_state.carreras_habilitadas_polla and lista_carreras_disponibles:
    st.session_state.carreras_habilitadas_polla = list(lista_carreras_disponibles)

# --- MENÚ PRINCIPAL HORIZONTAL ---
es_casa = (st.session_state.usuario_activo == "CASA")

st.markdown('<div class="carrusel-horizontal-box">', unsafe_allow_html=True)
if es_casa:
    col_menu1, col_menu2, col_menu3, col_menu4 = st.columns(4, gap="small")
else:
    col_menu1, col_menu2, col_menu3 = st.columns(3, gap="small")

with col_menu1:
    if st.button("REMATES", key="menu_btn_remates_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Remates" else "secondary"):
        st.session_state.menu_principal_opcion = "Remates"
        guardar_estado_global()
        st.rerun()

with col_menu2:
    if st.button("DUPLETA", key="menu_btn_dupletas_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Dupletas" else "secondary"):
        st.session_state.menu_principal_opcion = "Dupletas"
        guardar_estado_global()
        st.rerun()

with col_menu3:
    if st.button("CUENTAS", key="menu_btn_cuentas_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Cuentas" else "secondary"):
        st.session_state.menu_principal_opcion = "Cuentas"
        guardar_estado_global()
        st.rerun()

if es_casa:
    with col_menu4:
        if st.button("⚙️ CONFIG", key="menu_btn_config_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "🔒 Zona Admin" else "secondary"):
            st.session_state.menu_principal_opcion = "🔒 Zona Admin"
            guardar_estado_global()
            st.rerun()
else:
    if st.session_state.menu_principal_opcion == "🔒 Zona Admin":
        st.session_state.menu_principal_opcion = "Remates"
        guardar_estado_global()

st.markdown('</div>', unsafe_allow_html=True)
st.markdown("<hr style='margin: 0.3rem 0; border-color: #21262d;'>", unsafe_allow_html=True)

# --- BANNER MARQUESINA DINÁMICO ---
elementos_carrusel_info = []
remates_abiertos = [c for c in lista_carreras_disponibles if not st.session_state.carreras_cerradas_remate.get(c, False)]
if remates_abiertos:
    elementos_carrusel_info.append("🟢 REMATES ABIERTOS: " + " | ".join(remates_abiertos))
else:
    elementos_carrusel_info.append("🔴 TODOS LOS REMATES CERRADOS")

dupletas_hab = [c for c in st.session_state.carreras_habilitadas_dupleta if c in lista_carreras_disponibles]
if dupletas_hab:
    elementos_carrusel_info.append("🎟️ DUPLETAS DISPONIBLES EN: " + " - ".join(dupletas_hab))

ganadores_totales_global = []
for mod_g_key, h_g_dict in st.session_state.historial_ganadores_por_modalidad.items():
    for carr_g, info_g in h_g_dict.items():
        ganadores_totales_global.append(f"[{mod_g_key.upper()}] {carr_g.upper()} GANADOR: {info_g.get('Ganador', 'N/A')} ({info_g.get('Caballo', 'N/A')})")

if ganadores_totales_global:
    for tg in ganadores_totales_global:
        elementos_carrusel_info.append(f"🏆 {tg}")
else:
    elementos_carrusel_info.append("⏳ ESPERANDO PRIMEROS RESULTADOS DE GANADORES...")

if elementos_carrusel_info:
    texto_unido_marquesina = " &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ".join(elementos_carrusel_info)
    html_banner_marquesina = f"""
    <style>
        .marquee-container {{ width: 100%; background: transparent; border: none; box-shadow: none; padding: 8px 0; margin-bottom: 12px; overflow: hidden; box-sizing: border-box; display: flex; align-items: center; }}
        .marquee-text {{ display: inline-block; white-space: nowrap; animation: scrollRight 150s linear infinite !important; animation-play-state: running !important; font-family: 'Arial Black', Gadget, sans-serif; font-size: 15px; font-weight: 900; color: #00ffff; text-transform: uppercase; letter-spacing: 1.5px; text-shadow: 0px 0px 10px rgba(0, 255, 255, 0.9), 2px 2px 2px #000000; padding-right: 100%; }}
        @keyframes scrollRight {{ 0% {{ transform: translateX(-100%); }} 100% {{ transform: translateX(100%); }} }}
    </style>
    <div class="marquee-container"><div class="marquee-text">{texto_unido_marquesina}</div></div>
    """
    components.html(html_banner_marquesina, height=42)

# --- CARRUSEL AUTOMÁTICO DE IMÁGENES ---
ruta_actual_dir = os.path.dirname(os.path.abspath(__file__))
nombres_banners_posibles = ["1001398079.jpg", "1001398079.png", "1001398078.jpg", "1001398078.png", "1001398058.jpg", "1001398058.png", "rinconada.jpg", "rinconada.png"]
lista_b64_banners = []
for n_b in nombres_banners_posibles:
    r_b = os.path.join(ruta_actual_dir, n_b)
    if os.path.exists(r_b):
        try:
            with open(r_b, "rb") as f_b:
                b64_str = base64.b64encode(f_b.read()).decode('utf-8')
                lista_b64_banners.append(f"data:image/jpeg;base64,{b64_str}")
        except Exception:
            continue

if lista_b64_banners:
    js_images_array = json.dumps(lista_b64_banners)
    html_slider = f"""
    <style>
        body {{ margin: 0; padding: 0; background-color: #080a0f; overflow: hidden; }}
        .banner-slider-container {{ width: 100vw; height: 240px; margin: 0; padding: 0; overflow: hidden; position: relative; background-color: #080a0f; }}
        .banner-slide-img {{ width: 100%; height: 100%; object-fit: cover; transition: opacity 1.2s ease-in-out; display: block; }}
    </style>
    <div class="banner-slider-container"><img id="rinconada-slide" class="banner-slide-img" src="{lista_b64_banners[0]}" /></div>
    <script>
        (function() {{
            var images = {js_images_array}; var index = 0; var imgElement = document.getElementById("rinconada-slide");
            if(images.length > 1) {{
                setInterval(function() {{
                    index = (index + 1) % images.length;
                    imgElement.style.opacity = "0.15";
                    setTimeout(function() {{ imgElement.src = images[index]; imgElement.style.opacity = "1"; }}, 400);
                }}, 8000);
            }}
        }})();
    </script>
    """
    components.html(html_slider, height=245)

st.markdown("<br>", unsafe_allow_html=True)

# --- BARRA LATERAL ---
st.sidebar.header("Barra Lateral")
ahora_dt_sb = obtener_hora_venezuela_local()
st.sidebar.markdown(f"🕒 **Hora:** `{ahora_dt_sb.strftime('%I:%M:%S %p')}`")

with st.sidebar.expander("👤 Usuario Activo y Selector", expanded=True):
    usuario_seleccionado_sidebar = st.selectbox(
        "Cambiar de Usuario",
        options=st.session_state.lista_usuarios,
        index=st.session_state.lista_usuarios.index(st.session_state.usuario_activo) if st.session_state.usuario_activo in st.session_state.lista_usuarios else 0,
        key="sb_selectbox_usuario_activo"
    )
    if usuario_seleccionado_sidebar != st.session_state.usuario_activo:
        st.session_state.usuario_activo = usuario_seleccionado_sidebar
        guardar_estado_global()
        st.rerun()

with st.sidebar.expander("🏠 Retención de la Casa", expanded=False):
    porcentaje_casa = st.slider("Retención (%)", 0, 50, 30, key="sb_slider_retencion_casa")

with st.sidebar.expander("🔒 Estado Dupletas / 6 En Linea", expanded=False):
    if st.session_state.dupleta_bloqueada:
        st.markdown("<p style='color: #ff4757; font-weight: bold;'>🔴 BLOQUEADAS</p>", unsafe_allow_html=True)
        if st.button("🔓 Desbloquear", key="sb_btn_desbloquear_dupleta", use_container_width=True):
            st.session_state.dupleta_bloqueada = False
            guardar_estado_global()
            st.rerun()
    else:
        st.markdown("<p style='color: #00d2d3; font-weight: bold;'>🟢 ABIERTAS</p>", unsafe_allow_html=True)
        if st.button("🔒 Bloquear", key="sb_btn_bloquear_dupleta", use_container_width=True):
            st.session_state.dupleta_bloqueada = True
            guardar_estado_global()
            st.rerun()

with st.sidebar.expander("🏁 Cierre y Liquidación de Remates", expanded=False):
    carr_seleccionada_liq = st.selectbox("Gestionar Carrera", lista_carreras_disponibles, key="sb_liq_sel_carrera")
    c_cerrada_actual = st.session_state.carreras_cerradas_remate.get(carr_seleccionada_liq, False)
    
    st.markdown("---")
    if not c_cerrada_actual:
        if st.button("🔒 Cerrar Remate Manual", key=f"sb_liq_cerrar_{carr_seleccionada_liq}", use_container_width=True, type="primary"):
            st.session_state.carreras_cerradas_remate[carr_seleccionada_liq] = True
            st.session_state.estado_conteo_carrera_modalidad[carr_seleccionada_liq] = "CERRADO"
            st.session_state.detalles_carreras[carr_seleccionada_liq]["hora_cierre_real"] = ahora_dt_sb.strftime('%I:%M:%S %p')
            if not st.session_state.remates_cargados_en_cuentas.get(carr_seleccionada_liq, False):
                retirados_carr = st.session_state.ejemplares_retirados.get(carr_seleccionada_liq, [])
                no_val_carr = st.session_state.get('ejemplares_no_valido', {}).get(carr_seleccionada_liq, [])
                for mod_r_key in ["Adelantados", "Ciegos", "En Vivo"]:
                    remates_modalidad_dict = st.session_state.remates_por_modalidad.get(mod_r_key, {})
                    if carr_seleccionada_liq in remates_modalidad_dict:
                        for cab, info in remates_modalidad_dict[carr_seleccionada_liq].items():
                            if cab in retirados_carr or cab in no_val_carr:
                                continue
                            if info['jugador'] != "Sin Postor" and info['monto'] > 0:
                                if info['jugador'] not in st.session_state.cuentas:
                                    st.session_state.cuentas[info['jugador']] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                                st.session_state.cuentas[info['jugador']]['Pujas'] += info['monto']
                st.session_state.remates_cargados_en_cuentas[carr_seleccionada_liq] = True
            guardar_estado_global()
            st.rerun()
    else:
        if st.button("🔓 Reabrir Remate", key=f"sb_liq_reabrir_{carr_seleccionada_liq}", use_container_width=True):
            st.session_state.carreras_cerradas_remate[carr_seleccionada_liq] = False
            st.session_state.remates_cargados_en_cuentas[carr_seleccionada_liq] = False
            guardar_estado_global()
            st.rerun()

if st.sidebar.button("🗑️ Reiniciar Jornada", key="sb_btn_reiniciar_jornada", use_container_width=True):
    for key in list(st.session_state.keys()):
        if key not in ['banco_caballos_por_carrera', 'lista_usuarios']:
            del st.session_state[key]
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    st.toast("🚨 Jornada reiniciada.")
    st.rerun()

menu_principal_opcion = st.session_state.menu_principal_opcion

# =========================================================================
# BLOQUE FRAGMENTADO UNIVERSAL EN TIEMPO REAL (1 SEGUNDO) CON CONTROL DE HORARIOS
# =========================================================================
@st.fragment(run_every=1.0)
def renderizar_tiempo_real_universal():
    cargar_estado_global(forzar_recarga=True)
    ahora_dt = obtener_hora_venezuela_local()

    # 1. MÓDULO DE REMATES
    if st.session_state.menu_principal_opcion == "Remates":
        st.markdown('<div class="carrusel-horizontal-box">', unsafe_allow_html=True)
        col_so1, col_so2, col_so3 = st.columns(3, gap="small")
        with col_so1:
            if st.button("⏱️ Adelantados", key="sub_rem_adelantados", use_container_width=True, type="primary" if st.session_state.sub_remate_opcion == "Adelantados" else "secondary"):
                st.session_state.sub_remate_opcion = "Adelantados"
                guardar_estado_global()
                st.rerun()
        with col_so2:
            if st.button("🙈 Ciegos", key="sub_rem_ciegos", use_container_width=True, type="primary" if st.session_state.sub_remate_opcion == "Ciegos" else "secondary"):
                st.session_state.sub_remate_opcion = "Ciegos"
                guardar_estado_global()
                st.rerun()
        with col_so3:
            if st.button("⚡ En Vivo", key="sub_rem_envivo", use_container_width=True, type="primary" if st.session_state.sub_remate_opcion == "En Vivo" else "secondary"):
                st.session_state.sub_remate_opcion = "En Vivo"
                guardar_estado_global()
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<hr style='margin: 0.3rem 0; border-color: #21262d;'>", unsafe_allow_html=True)
        modo_actual_remate = st.session_state.sub_remate_opcion

        if modo_actual_remate == "Ciegos":
            if 'sub_ciego_opcion' not in st.session_state:
                st.session_state.sub_ciego_opcion = "1V"
            
            col_sc1, col_sc2 = st.columns(2, gap="small")
            with col_sc1:
                if st.button("🙈 Remate 1V", key="btn_ciego_1v_tab", use_container_width=True, type="primary" if st.session_state.sub_ciego_opcion == "1V" else "secondary"):
                    st.session_state.sub_ciego_opcion = "1V"
                    guardar_estado_global()
                    st.rerun()
            with col_sc2:
                if st.button("🙈 Remate 6V", key="btn_ciego_6v_tab", use_container_width=True, type="primary" if st.session_state.sub_ciego_opcion == "6V" else "secondary"):
                    st.session_state.sub_ciego_opcion = "6V"
                    guardar_estado_global()
                    st.rerun()
            st.markdown("<hr style='margin: 0.3rem 0; border-color: #21262d;'>", unsafe_allow_html=True)

            nombre_carrera_virtual = "Remate 1V" if st.session_state.sub_ciego_opcion == "1V" else "Remate 6V"
            
            if nombre_carrera_virtual not in st.session_state.remates_por_modalidad["Ciegos"]:
                st.session_state.remates_por_modalidad["Ciegos"][nombre_carrera_virtual] = {f"{j} - Ejemplar {j}": {"jugador": "Sin Postor", "monto": 0.0} for j in range(1, 15)}
                st.session_state.detalles_carreras[nombre_carrera_virtual] = {
                    "condicion": "Remate inicial ciego de 14 ejemplares", "distancia": "1200 mts", "hora": "02:00 PM",
                    "monto_fijo_ciego": 500.0, "incentivo_adelantados": 0.0, "incentivo_ciegos": 0.0, "incentivo_envivo": 0.0, "hora_cierre_real": "No registrada"
                }

            carr_activa = nombre_carrera_virtual
            carrera_cerrada = st.session_state.carreras_cerradas_remate.get(carr_activa, False)
            detalles_carr = st.session_state.detalles_carreras.get(carr_activa, {"condicion": "Remate Ciego", "distancia": "1200 mts", "hora": "02:00 PM"})

            carrera_real_asignada = st.session_state.mapeo_ciegos_carreras.get(nombre_carrera_virtual, "")
            if carrera_real_asignada and carrera_real_asignada in st.session_state.banco_caballos_por_carrera:
                caballos_reales_oficiales = st.session_state.banco_caballos_por_carrera[carrera_real_asignada]
                remates_actuales_virtuales = st.session_state.remates_por_modalidad["Ciegos"][nombre_carrera_virtual]
                remates_filtrados_nuevos = {}
                for cab_oficial in caballos_reales_oficiales:
                    if cab_oficial in remates_actuales_virtuales:
                        remates_filtrados_nuevos[cab_oficial] = remates_actuales_virtuales[cab_oficial]
                    else:
                        remates_filtrados_nuevos[cab_oficial] = {"jugador": "Sin Postor", "monto": 0.0}
                st.session_state.remates_por_modalidad["Ciegos"][nombre_carrera_virtual] = remates_filtrados_nuevos
                st.markdown(f"<div style='background:#161b22; padding:6px; border-radius:6px; margin-bottom:8px; border:1px solid #30363d; font-size:12px;'>🔗 Vinculado a: <b>{carrera_real_asignada}</b> ({len(caballos_reales_oficiales)} ejemplares activos)</div>", unsafe_allow_html=True)

            tabla_html = generar_tabla_html_remate(st.session_state.remates_por_modalidad["Ciegos"][carr_activa], st.session_state.ejemplares_retirados.get(carr_activa, []), st.session_state.ejemplares_no_valido.get(carr_activa, []))
            cantidad_filas = len(st.session_state.remates_por_modalidad["Ciegos"][carr_activa])
            altura_dinamica = min(max(140, (cantidad_filas * 35) + 50), 420)
            components.html(tabla_html, height=altura_dinamica, scrolling=True)

            total_pote = sum([info['monto'] for cab_n, info in st.session_state.remates_por_modalidad["Ciegos"][carr_activa].items()])
            monto_casa = total_pote * (porcentaje_casa / 100)
            pote_neto_base = total_pote - monto_casa
            incentivo_actual = float(detalles_carr.get('incentivo_ciegos', 0.0))
            premio_total_calculado = pote_neto_base + incentivo_actual

            st.markdown(f"""
                <div class="incentivo-llamativo">
                    <div style="font-size: 11px; font-weight: 800; color: #00ffff; text-transform: uppercase; margin-bottom: 2px;">PREMIO TOTAL</div>
                    <div class="incentivo-llamativo-monto">🎁 {formatear_bs(premio_total_calculado)}</div>
                </div>
            """, unsafe_allow_html=True)

            c_m1, c_m2 = st.columns(2)
            c_m1.metric(f"💰 Pote ({carr_activa})", formatear_bs(total_pote))
            c_m2.metric(f"🎁 Incentivo ({carr_activa})", formatear_bs(incentivo_actual))

            # Sección Ciegos - Panel didáctico de asignación
            with st.container(border=True):
                st.markdown(f"🙈 **Remate Ciego - Asignación de Ejemplar ({carr_activa})**")
                monto_fijo_carrera = detalles_carr.get('monto_fijo_ciego', 500.0)
                caballos_disponibles_ciego = [cab for cab, info in st.session_state.remates_por_modalidad["Ciegos"][carr_activa].items() if info['jugador'] == "Sin Postor" or info['monto'] <= 0]

                if not caballos_disponibles_ciego:
                    st.warning("⚠️ Todos los ejemplares disponibles de este remate ya han sido adquiridos.")
                else:
                    st.markdown("🎲 **Panel Didáctico (Elige un número para asignar):**")
                    cols_ciego_grid = st.columns(min(3, len(caballos_disponibles_ciego)), gap="small")
                    for idx_cb, cb_disp in enumerate(caballos_disponibles_ciego):
                        c_idx = idx_cb % len(cols_ciego_grid)
                        num_cb_parte = cb_disp.split(" - ")[0]
                        with cols_ciego_grid[c_idx]:
                            if carrera_cerrada:
                                st.button(f"🔒#{num_cb_parte}", key=f"btn_ciego_grid_{carr_activa}_{cb_disp}", use_container_width=True, disabled=True)
                            else:
                                if st.button(f"#{num_cb_parte}", key=f"btn_ciego_grid_{carr_activa}_{cb_disp}", use_container_width=True, type="primary"):
                                    st.session_state.remates_por_modalidad["Ciegos"][carr_activa][cb_disp] = {
                                        "jugador": st.session_state.usuario_activo, "monto": monto_fijo_carrera
                                    }
                                    st.session_state.historial_jugadas.append({
                                        "fecha": ahora_dt.strftime('%d/%m/%Y %I:%M:%S %p'), "jugador": st.session_state.usuario_activo,
                                        "tipo": f"Remate Ciego ({modo_actual_remate})", "carrera": carr_activa, "detalle": cb_disp, "monto": monto_fijo_carrera
                                    })
                                    if st.session_state.usuario_activo not in st.session_state.cuentas:
                                        st.session_state.cuentas[st.session_state.usuario_activo] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                                    st.session_state.cuentas[st.session_state.usuario_activo]['Pujas'] += monto_fijo_carrera
                                    guardar_estado_global()
                                    st.success(f"🎉 #{num_cb_parte} asignado a **{st.session_state.usuario_activo}** ({formatear_bs(monto_fijo_carrera)})!")
                                    st.rerun()

        else:
            if not lista_carreras_disponibles:
                st.warning("⚠️ No hay carreras cargadas en el sistema.")
            else:
                carreras_modalidad_permitidas = st.session_state.carreras_por_modalidad.get(modo_actual_remate, lista_carreras_disponibles)
                carreras_filtradas_visibles = [
                    c for c in lista_carreras_disponibles 
                    if c in carreras_modalidad_permitidas and ((c in st.session_state.carreras_activas_remate) or st.session_state.carreras_cerradas_remate.get(c, False))
                ]
                
                if not carreras_filtradas_visibles:
                    st.info(f"ℹ️ No hay carreras habilitadas para la modalidad **{modo_actual_remate}**.")
                else:
                    if "carrera_remate_activa_seleccionada" not in st.session_state or st.session_state["carrera_remate_activa_seleccionada"] not in carreras_filtradas_visibles:
                        carr_activa = carreras_filtradas_visibles[0]
                        st.session_state["carrera_remate_activa_seleccionada"] = carr_activa
                    else:
                        carr_activa = st.session_state["carrera_remate_activa_seleccionada"]

                    st.markdown("🔹 **Seleccionar Carrera:**")
                    carreras_totales_visibles = list(carreras_filtradas_visibles)
                    st.markdown('<div class="carreras-scroll-container">', unsafe_allow_html=True)
                    cols_carreras = st.columns(len(carreras_totales_visibles), gap="small")
                    for idx, c_nombre in enumerate(carreras_totales_visibles):
                        abreviatura = obtener_abreviatura_carrera(c_nombre, modo_actual=modo_actual_remate)
                        es_activa = (c_nombre == carr_activa)
                        with cols_carreras[idx]:
                            if st.button(abreviatura, key=f"rem_btn_sel_carr_{idx}", use_container_width=True, type="primary" if es_activa else "secondary"):
                                st.session_state["carrera_remate_activa_seleccionada"] = c_nombre
                                guardar_estado_global()
                                st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown("---")

                    if carr_activa in st.session_state.imagenes_carreras:
                        try:
                            st.image(st.session_state.imagenes_carreras[carr_activa], caption=f"Imagen oficial - {carr_activa}", use_container_width=True)
                        except Exception:
                            pass

                    # --- VERIFICACIÓN ESTRICTA DE INICIO Y CIERRE (ANTI-SNIPER Y HORARIOS) ---
                    clave_mod_carr = f"{modo_actual_remate}_{carr_activa}"
                    dt_inicio = st.session_state.fechas_horas_inicio_remate_modalidad.get(clave_mod_carr)
                    dt_limite = st.session_state.fechas_horas_cierre_remate_modalidad.get(clave_mod_carr)
                    estado_conteo = st.session_state.estado_conteo_carrera_modalidad.get(clave_mod_carr, "INACTIVO")

                    # Validación de apertura automática según la hora local de Venezuela
                    bloqueo_por_inicio = False
                    if dt_inicio and ahora_dt < dt_inicio:
                        bloqueo_por_inicio = True

                    if dt_inicio:
                        st.markdown(f"<div style='background:#161b22; padding:6px; border-radius:6px; margin-bottom:4px; border:1px solid #30363d; font-size:12px;'>🟢 Inicio Remate ({modo_actual_remate}): <b>{dt_inicio.strftime('%d/%m/%Y - %I:%M %p')}</b></div>", unsafe_allow_html=True)
                    if dt_limite:
                        st.markdown(f"<div style='background:#161b22; padding:6px; border-radius:6px; margin-bottom:8px; border:1px solid #30363d; font-size:12px;'>⏰ Cierre Estricto ({modo_actual_remate}): <b>{dt_limite.strftime('%d/%m/%Y - %I:%M %p')}</b></div>", unsafe_allow_html=True)

                    carrera_cerrada = st.session_state.carreras_cerradas_remate.get(carr_activa, False)

                    if dt_limite and not carrera_cerrada:
                        diferencia_segundos = (dt_limite - ahora_dt).total_seconds()
                        if estado_conteo == "INACTIVO":
                            if 0 < diferencia_segundos <= 10:
                                st.session_state.estado_conteo_carrera_modalidad[clave_mod_carr] = "CONTEO_10S"
                                st.session_state.tiempo_inicio_conteo_modalidad[clave_mod_carr] = ahora_dt
                                guardar_estado_global()
                                st.rerun()
                            elif diferencia_segundos <= 0:
                                st.session_state.carreras_cerradas_remate[carr_activa] = True
                                st.session_state.estado_conteo_carrera_modalidad[clave_mod_carr] = "CERRADO"
                                st.session_state.detalles_carreras[carr_activa]["hora_cierre_real"] = ahora_dt.strftime('%I:%M:%S %p')
                                guardar_estado_global()
                                st.rerun()
                        elif estado_conteo == "CONTEO_10S":
                            tiempo_inicio = st.session_state.tiempo_inicio_conteo_modalidad.get(clave_mod_carr, ahora_dt)
                            transcurridos = (ahora_dt - tiempo_inicio).total_seconds()
                            if transcurridos >= 12:
                                st.session_state.carreras_cerradas_remate[carr_activa] = True
                                st.session_state.estado_conteo_carrera_modalidad[clave_mod_carr] = "CERRADO"
                                st.session_state.detalles_carreras[carr_activa]["hora_cierre_real"] = ahora_dt.strftime('%I:%M:%S %p')
                                guardar_estado_global()
                                st.rerun()
                            else:
                                restantes_10s = max(0, 10 - int(transcurridos))
                                if restantes_10s > 0:
                                    st.markdown(f"""
                                        <div class='timer-box'>
                                            ⚠️ ¡ATENCIÓN! CIERRE INMINENTE EN: <b>{restantes_10s}s</b> 
                                            <br><span style='font-size: 10px; color: #00ffff;'>🛡️ Sistema Anti-Sniper Activo ({carr_activa} - {modo_actual_remate})</span>
                                        </div>
                                    """, unsafe_allow_html=True)

                    estado_icono = "🔴" if (carrera_cerrada or bloqueo_por_inicio) else "🟢"
                    st.markdown(f"""
                        <div style="font-size: 14px; font-weight: 800; color: #f0f6fc; display: flex; align-items: center; gap: 6px; margin-top: 8px; margin-bottom: 8px;">
                            <span>{estado_icono}</span>
                            <span>{carr_activa}</span>
                            <span style="font-size: 11px; font-weight: 600; color: #8b949e; background: #161b22; padding: 1px 6px; border-radius: 4px; border: 1px solid #30363d;">{modo_actual_remate}</span>
                        </div>
                    """, unsafe_allow_html=True)

                    detalles_carr = st.session_state.detalles_carreras.get(carr_activa, {})
                    st.markdown(f"""
                        <div class="carrera-condicion-card">
                            <b>🏁 {carr_activa}</b><br>
                            🏷️ <b>Condición:</b> {detalles_carr.get('condicion', 'N/A')}<br>
                            📏 <b>Distancia:</b> {detalles_carr.get('distancia', 'N/A')} &nbsp;|&nbsp; ⏰ <b>Hora:</b> {detalles_carr.get('hora', 'N/A')}
                        </div>
                    """, unsafe_allow_html=True)

                    tabla_html = generar_tabla_html_remate(st.session_state.remates_por_modalidad[modo_actual_remate][carr_activa], st.session_state.ejemplares_retirados.get(carr_activa, []), st.session_state.ejemplares_no_valido.get(carr_activa, []))
                    components.html(tabla_html, height=220, scrolling=True)

                    if bloqueo_por_inicio:
                        st.warning(f"⏳ **Remate no disponible:** Abre oficialmente a las {dt_inicio.strftime('%I:%M %p')}.")
                    elif carrera_cerrada:
                        st.error("🔒 **Remate Cerrado:** El tiempo límite de apuestas ha finalizado.")
                    else:
                        # Formulario de pujas activas si cumple los horarios
                        with st.container(border=True):
                            st.markdown(f"⚡ **Registro Rápido de Puja - {carr_activa}**")
                            remates_actuales_mod = st.session_state.remates_por_modalidad[modo_actual_remate][carr_activa]
                            retirados_carr_activa = st.session_state.ejemplares_retirados.get(carr_activa, [])
                            no_validos_carr_activa = st.session_state.ejemplares_no_valido.get(carr_activa, [])
                            excluidos_carr_activa = set(retirados_carr_activa) | set(no_validos_carr_activa)

                            lista_caballos_activos = [c for c in list(remates_actuales_mod.keys()) if c not in excluidos_carr_activa]
                            
                            if lista_caballos_activos:
                                k_sel_cab = f"rem_caballo_activo_click_{modo_actual_remate}_{carr_activa}"
                                if k_sel_cab not in st.session_state or st.session_state[k_sel_cab] not in lista_caballos_activos:
                                    st.session_state[k_sel_cab] = lista_caballos_activos[0]

                                caballero_seleccionado = st.selectbox("Seleccionar Ejemplar", lista_caballos_activos, key=k_sel_cab)
                                puja_actual = remates_actuales_mod[caballero_seleccionado]['monto']
                                opciones_escala = obtener_siguientes_montos(puja_actual)
                                monto_puja = st.selectbox("💰 Monto de Puja", opciones_escala, format_func=lambda x: formatear_bs(x), key=f"rem_sel_monto_{modo_actual_remate}_{carr_activa}")

                                if st.button(f"🔨 Confirmar Puja ({carr_activa})", key=f"rem_btn_confirmar_{modo_actual_remate}_{carr_activa}", use_container_width=True, type="primary"):
                                    if monto_puja <= puja_actual:
                                        st.error("El monto debe ser mayor a la puja actual.")
                                    else:
                                        st.session_state.remates_por_modalidad[modo_actual_remate][carr_activa][caballero_seleccionado] = {"jugador": st.session_state.usuario_activo, "monto": monto_puja}
                                        st.session_state.historial_jugadas.append({
                                            "fecha": ahora_dt.strftime('%d/%m/%Y %I:%M:%S %p'), "jugador": st.session_state.usuario_activo,
                                            "tipo": f"Remate ({modo_actual_remate})", "carrera": carr_activa, "detalle": caballero_seleccionado, "monto": monto_puja
                                        })
                                        if estado_conteo == "CONTEO_10S":
                                            st.session_state.tiempo_inicio_conteo_modalidad[clave_mod_carr] = obtener_hora_venezuela_local()
                                        guardar_estado_global()
                                        st.success("✅ ¡Puja registrada correctamente!")
                                        st.rerun()

renderizar_tiempo_real_universal()

# =========================================================================
# 2. MÓDULO DE DUPLETA Y 6 EN LINEA
# =========================================================================
elif menu_principal_opcion == "Dupletas":
    st.markdown('<div class="carrusel-horizontal-box">', unsafe_allow_html=True)
    col_d1, col_d2, col_d3 = st.columns(3, gap="small")
    with col_d1:
        if st.button("🎟️ Dupleta", key="sub_dup_dupleta", use_container_width=True, type="primary" if st.session_state.sub_dupleta_opcion == "Dupleta" else "secondary"):
            st.session_state.sub_dupleta_opcion = "Dupleta"
            guardar_estado_global()
            st.rerun()
    with col_d2:
        if st.button("🎟️ Tripleta", key="sub_dup_tripleta", use_container_width=True, type="primary" if st.session_state.sub_dupleta_opcion == "Tripleta" else "secondary"):
            st.session_state.sub_dupleta_opcion = "Tripleta"
            guardar_estado_global()
            st.rerun()
    with col_d3:
        if st.button("🏇 6 En Linea", key="sub_dup_polla", use_container_width=True, type="primary" if st.session_state.sub_dupleta_opcion == "6 En Linea" else "secondary"):
            st.session_state.sub_dupleta_opcion = "6 En Linea"
            guardar_estado_global()
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    sub_dup_actual = st.session_state.sub_dupleta_opcion
    st.markdown(f"<div class='subasta-header'>🎟️ Armado Visual de {sub_dup_actual}</div>", unsafe_allow_html=True)
    
    dt_inicio_m = st.session_state.fechas_horas_inicio_modalidad_multiple.get(sub_dup_actual)
    dt_cierre_m = st.session_state.fechas_horas_cierre_modalidad_multiple.get(sub_dup_actual)
    ahora_actual = obtener_hora_venezuela_local()

    bloqueo_por_horario = False
    if dt_inicio_m and ahora_actual < dt_inicio_m:
        bloqueo_por_horario = True
        st.warning(f"⏳ **AÚN NO ABRE:** Esta modalidad abre el {dt_inicio_m.strftime('%d/%m/%Y a las %I:%M %p')}.")
    elif dt_cierre_m and ahora_actual > dt_cierre_m:
        bloqueo_por_horario = True
        st.error(f"🔒 **CERRADO ESTRICTO:** El horario de emisión finalizó el {dt_cierre_m.strftime('%d/%m/%Y a las %I:%M %p')}.")

    if st.session_state.dupleta_bloqueada or bloqueo_por_horario:
        st.error("🔒 **BLOQUEADO:** Emisión cerrada temporalmente.")
    else:
        st.info("🟢 Emisión abierta con normalidad.")

# =========================================================================
# 3. MÓDULO DE CUENTAS
# =========================================================================
elif menu_principal_opcion == "Cuentas":
    st.markdown("<div class='subasta-header'>📊 Mis Cuentas y Historial de Jugador</div>", unsafe_allow_html=True)
    jugador_actual = st.session_state.usuario_activo
    st.markdown(f"👤 **Jugador en Sesión:** `{jugador_actual}`")

    if jugador_actual not in st.session_state.cuentas:
        st.session_state.cuentas[jugador_actual] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
    
    vals = st.session_state.cuentas[jugador_actual]
    pujas, premios, abonos = vals['Pujas'], vals['Premios'], vals['Abonos']
    balance_neto = pujas - abonos - premios

    col_cu1, col_cu2, col_cu3, col_cu4 = st.columns(4, gap="small")
    col_cu1.metric("🛒 Compras", formatear_bs(pujas))
    col_cu2.metric("🏆 Premios", formatear_bs(premios))
    col_cu3.metric("💳 Pagos", formatear_bs(abonos))
    col_cu4.metric("⚖️ Neto", formatear_bs(balance_neto))

# =========================================================================
# 4. ZONA DE ADMINISTRADOR
# =========================================================================
elif menu_principal_opcion == "🔒 Zona Admin" and es_casa:
    st.markdown("<div class='subasta-header'>🔒 Panel de Configuración y Administración</div>", unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["✍️ Caballos", "👥 Usuarios", "⚙️ Dupleta/6L", "📺 Video", "📊 Saldos", "🖼️ Imágenes"])

    with tab1:
        st.markdown("### ✍️ Banco de Caballos y Carreras Activas")
        carr_banco_sel = st.selectbox("Seleccionar Carrera para Editar", lista_carreras_disponibles, key="adm_banco_sel_carrera")
        
        if carr_banco_sel not in st.session_state.detalles_carreras:
            st.session_state.detalles_carreras[carr_banco_sel] = {
                "condicion": "Condición general", "distancia": "1200 mts", "hora": "02:00 PM", 
                "monto_fijo_ciego": 500.0, "incentivo_adelantados": 0.0, "incentivo_ciegos": 0.0,
                "incentivo_envivo": 0.0, "hora_cierre_real": "No registrada"
            }

        det_actuales = st.session_state.detalles_carreras[carr_banco_sel]
        with st.container(border=True):
            st.markdown(f"🛠️ **Detalles e Incentivos ({carr_banco_sel})**")
            edit_cond = st.text_input("Condición", value=det_actuales.get('condicion', ''), key=f"banco_cond_{carr_banco_sel}")
            
            if st.button("💾 Guardar Detalles", key=f"btn_save_banco_det_{carr_banco_sel}", use_container_width=True, type="primary"):
                st.session_state.detalles_carreras[carr_banco_sel]["condicion"] = edit_cond
                guardar_estado_global()
                st.toast("✅ ¡Detalles guardados!")
                st.rerun()

        with st.container(border=True):
            st.markdown(f"⏰ **Control de Horarios Individuales ({carr_banco_sel})**")
            mod_seleccionada_horarios = st.selectbox("Modalidad", ["Adelantados", "Ciegos", "En Vivo"], key=f"sel_mod_horarios_{carr_banco_sel}")
            clave_mod_carr_adm = f"{mod_seleccionada_horarios}_{carr_banco_sel}"
            
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                f_ini = st.date_input("Fecha Inicio", value=obtener_hora_venezuela_local().date(), key=f"f_ini_{clave_mod_carr_adm}")
                h_ini_val = st.number_input("Hora (1-12)", min_value=1, max_value=12, value=2, key=f"hi_h_{clave_mod_carr_adm}")
                m_ini_val = st.number_input("Min (0-59)", min_value=0, max_value=59, value=0, key=f"hi_m_{clave_mod_carr_adm}")
                ampm_ini = st.selectbox("AM/PM", ["AM", "PM"], index=1, key=f"hi_ap_{clave_mod_carr_adm}")
            with col_h2:
                f_cier = st.date_input("Fecha Cierre", value=obtener_hora_venezuela_local().date(), key=f"f_cier_{clave_mod_carr_adm}")
                h_cier_val = st.number_input("Hora (1-12)", min_value=1, max_value=12, value=2, key=f"hc_h_{clave_mod_carr_adm}")
                m_cier_val = st.number_input("Min (0-59)", min_value=0, max_value=59, value=30, key=f"hc_m_{clave_mod_carr_adm}")
                ampm_cier = st.selectbox("AM/PM", ["AM/PM"], options=["AM", "PM"], index=1, key=f"hc_ap_{clave_mod_carr_adm}")

            if st.button(f"💾 Guardar Horarios para {mod_seleccionada_horarios}", key=f"btn_save_horarios_{clave_mod_carr_adm}", use_container_width=True, type="primary"):
                h_i_24 = h_ini_val if ampm_ini == "AM" else (h_ini_val + 12 if h_ini_val < 12 else 12)
                if ampm_ini == "AM" and h_ini_val == 12: h_i_24 = 0
                h_c_24 = h_cier_val if ampm_cier == "AM" else (h_cier_val + 12 if h_cier_val < 12 else 12)
                if ampm_cier == "AM" and h_cier_val == 12: h_c_24 = 0

                dt_i_final = datetime.combine(f_ini, dtime(h_i_24, m_ini_val))
                dt_c_final = datetime.combine(f_cier, dtime(h_c_24, m_cier_val))

                st.session_state.fechas_horas_inicio_remate_modalidad[clave_mod_carr_adm] = dt_i_final
                st.session_state.fechas_horas_cierre_remate_modalidad[clave_mod_carr_adm] = dt_c_final
                guardar_estado_global()
                st.toast(f"✅ ¡Horarios guardados correctamente!")
                st.rerun()

    with tab2:
        st.markdown("### 👥 Registro de Usuarios")
        nuevo_usuario_input = st.text_input("Nuevo Usuario", placeholder="Ej: JUAN", key="input_nuevo_usuario_reg")
        if st.button("➕ Registrar", key="btn_registrar_nuevo_usuario", use_container_width=True, type="primary"):
            usuario_limpio = nuevo_usuario_input.strip().upper()
            if usuario_limpio and usuario_limpio not in st.session_state.lista_usuarios:
                st.session_state.lista_usuarios.append(usuario_limpio)
                guardar_estado_global()
                st.rerun()

# =========================================================================
# TRANSMISIÓN EN VIVO
# =========================================================================
url_live_video = st.session_state.get('url_video_en_vivo', '').strip()
if url_live_video:
    st.markdown("<br><hr style='border-color: #30363d;'>", unsafe_allow_html=True)
    st.markdown("### 📺 TRANSMISIÓN EN VIVO")
    st.video(url_live_video)
