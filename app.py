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
    "1001397336_preview_rev_1.png", "1001397336_preview_rev_1.jpg", "1001397336.jpg",
    "1001397336.png", "1001394095_preview_rev_1_2.png", "1001394095_preview_rev_1_2.jpg",
    "logo.png", "logo.jpg"
]

img_b64 = get_image_base64(nombres_archivos)
logo_display = f'<img src="data:image/png;base64,{img_b64}" class="header-logo-img" />' if img_b64 else '<span style="color: #f1c40f; font-size: 38px; font-weight: 900; font-style: italic; letter-spacing: 1.5px;">CALIFORNIA CHROME</span>'

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
    .stButton button { border-radius: 6px !important; font-weight: 700 !important; padding: 0.2rem 0.4rem !important; min-height: 38px !important; font-size: 12px !important; width: 100% !important; }
    .subasta-header { font-size: clamp(14px, 3.5vw, 18px); font-weight: 800; color: #f1e05a; margin-bottom: 4px; border-bottom: 2px solid #f1e05a; padding-bottom: 3px; }
    .timer-box { background-color: #161b22; border: 1px solid #ff4757; padding: 6px; border-radius: 6px; text-align: center; font-size: clamp(12px, 3vw, 15px); font-weight: bold; color: #ff4757; margin-bottom: 8px; }
    .carrera-condicion-card { background-color: #161b22; border: 1px solid #30363d; padding: 8px 12px; border-radius: 6px; font-size: 12px; color: #f0f6fc; margin-bottom: 10px; line-height: 1.4; word-break: break-word; }
    .incentivo-llamativo { background: linear-gradient(135deg, #1f1c2c 0%, #923d41 100%); border: 2px dashed #00ffff; padding: 10px 16px; border-radius: 12px; text-align: center; margin: 10px 0; box-shadow: 0px 0px 15px rgba(0, 255, 255, 0.4); }
    .incentivo-llamativo-monto { color: #ffffff; font-size: 22px; font-weight: 900; letter-spacing: 0.5px; text-shadow: 2px 2px 4px #000000; }
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
            if nombre_carrera == carreras_ciegas[0]: return "1V"
            elif nombre_carrera == carreras_ciegas[1]: return "6V"
    match = re.search(r'\d+', nombre_carrera)
    if match: return f"C{match.group(0)}"
    return nombre_carrera[:3].upper()

def generar_tabla_html_remate(remates_dict, retirados_list, no_validos_list=[]):
    html = """
    <style>
        .tabla-referencia {
            width: 100%;
            border-collapse: collapse;
            font-family: sans-serif;
            background-color: #ffffff;
            color: #000000;
            margin-bottom: 10px;
            table-layout: fixed;
        }
        .tabla-referencia th {
            border-top: 2px solid #dfc729;
            border-bottom: 2px solid #dfc729;
            padding: 6px 4px;
            text-align: left;
            font-weight: 800;
            background-color: #ffffff;
            color: #000000;
            font-size: 11px;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .tabla-referencia td {
            border-bottom: 1px solid #dfc729;
            padding: 6px 4px;
            background-color: #fbfbfb;
            color: #111111;
            font-size: 11px;
            vertical-align: middle;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
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
        .badge-2 { background-color: #ffffff; color: #000000; border: 1.5px solid #000000; }
        .badge-3 { background-color: #1d11c0; color: #ffffff; }
        .badge-4 { background-color: #f1c40f; color: #000000; }
        .badge-5 { background-color: #28a745; color: #ffffff; }
        .badge-6 { background-color: #000000; color: #ffffff; }
        .badge-7 { background-color: #fd7e14; color: #ffffff; }
        .badge-default { background-color: #6c757d; color: #ffffff; }
        .retirado-row td {
            background-color: #ffe6e6 !important;
            color: #990000 !important;
            text-decoration: line-through;
        }
        .novale-row td {
            background-color: #fff3cd !important;
            color: #856404 !important;
            font-style: italic;
        }
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

for mod in ["Adelantados", "Ciegos", "En Vivo"]:
    if not st.session_state.carreras_por_modalidad.get(mod) and lista_carreras_disponibles:
        st.session_state.carreras_por_modalidad[mod] = list(lista_carreras_disponibles)

if not st.session_state.carreras_habilitadas_dupleta and lista_carreras_disponibles:
    st.session_state.carreras_habilitadas_dupleta = list(lista_carreras_disponibles)
if not st.session_state.carreras_habilitadas_tripleta and lista_carreras_disponibles:
    st.session_state.carreras_habilitadas_tripleta = list(lista_carreras_disponibles)
if not st.session_state.carreras_habilitadas_polla and lista_carreras_disponibles:
    st.session_state.carreras_habilitadas_polla = list(lista_carreras_disponibles)

# --- MENÚ PRINCIPAL HORIZONTAL ---
es_casa = (st.session_state.usuario_activo == "CASA")
st.markdown('<div class="carrusel-horizontal-box">', unsafe_allow_html=True)
cols_menu = st.columns(4 if es_casa else 3, gap="small")

with cols_menu[0]:
    if st.button("REMATES", key="menu_btn_remates_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Remates" else "secondary"):
        st.session_state.menu_principal_opcion = "Remates"
        guardar_estado_global()
        st.rerun()

with cols_menu[1]:
    if st.button("DUPLETA", key="menu_btn_dupletas_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Dupletas" else "secondary"):
        st.session_state.menu_principal_opcion = "Dupletas"
        guardar_estado_global()
        st.rerun()

with cols_menu[2]:
    if st.button("CUENTAS", key="menu_btn_cuentas_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Cuentas" else "secondary"):
        st.session_state.menu_principal_opcion = "Cuentas"
        guardar_estado_global()
        st.rerun()

if es_casa:
    with cols_menu[3]:
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

# --- BARRA LATERAL ---
st.sidebar.header("Barra Lateral")
ahora_dt_sb = obtener_hora_venezuela_local()
st.sidebar.markdown(f"🕒 **Hora:** `{ahora_dt_sb.strftime('%I:%M:%S %p')}`")

with st.sidebar.expander("👤 Usuario Activo y Selector", expanded=True):
    usuario_seleccionado_sidebar = st.selectbox(
        "Cambiar de Usuario", options=st.session_state.lista_usuarios,
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
# BLOQUE FRAGMENTADO UNIVERSAL EN TIEMPO REAL (1 SEGUNDO)
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
            
            carr_activa = nombre_carrera_virtual
            carrera_cerrada = st.session_state.carreras_cerradas_remate.get(carr_activa, False)
            tabla_html = generar_tabla_html_remate(st.session_state.remates_por_modalidad["Ciegos"][carr_activa], st.session_state.ejemplares_retirados.get(carr_activa, []), st.session_state.ejemplares_no_valido.get(carr_activa, []))
            components.html(tabla_html, height=220, scrolling=True)

        else:
            if lista_carreras_disponibles:
                carreras_modalidad_permitidas = st.session_state.carreras_por_modalidad.get(modo_actual_remate, lista_carreras_disponibles)
                carreras_filtradas_visibles = [c for c in lista_carreras_disponibles if c in carreras_modalidad_permitidas]
                
                if carreras_filtradas_visibles:
                    if "carrera_remate_activa_seleccionada" not in st.session_state or st.session_state["carrera_remate_activa_seleccionada"] not in carreras_filtradas_visibles:
                        carr_activa = carreras_filtradas_visibles[0]
                        st.session_state["carrera_remate_activa_seleccionada"] = carr_activa
                    else:
                        carr_activa = st.session_state["carrera_remate_activa_seleccionada"]

                    st.markdown("🔹 **Seleccionar Carrera:**")
                    cols_carreras = st.columns(len(carreras_filtradas_visibles), gap="small")
                    for idx, c_nombre in enumerate(carreras_filtradas_visibles):
                        abreviatura = obtener_abreviatura_carrera(c_nombre, modo_actual=modo_actual_remate)
                        with cols_carreras[idx]:
                            if st.button(abreviatura, key=f"rem_btn_sel_carr_{idx}", use_container_width=True, type="primary" if c_nombre == carr_activa else "secondary"):
                                st.session_state["carrera_remate_activa_seleccionada"] = c_nombre
                                guardar_estado_global()
                                st.rerun()
                    st.markdown("---")

                    # Control de Horarios Anti-Sniper
                    clave_mod_carr = f"{modo_actual_remate}_{carr_activa}"
                    dt_inicio = st.session_state.fechas_horas_inicio_remate_modalidad.get(clave_mod_carr)
                    dt_limite = st.session_state.fechas_horas_cierre_remate_modalidad.get(clave_mod_carr)
                    estado_conteo = st.session_state.estado_conteo_carrera_modalidad.get(clave_mod_carr, "INACTIVO")

                    bloqueo_por_inicio = dt_inicio and ahora_dt < dt_inicio
                    carrera_cerrada = st.session_state.carreras_cerradas_remate.get(carr_activa, False)

                    if dt_inicio:
                        st.markdown(f"<div style='background:#161b22; padding:6px; border-radius:6px; margin-bottom:4px; font-size:12px;'>🟢 Inicio Remate: <b>{dt_inicio.strftime('%d/%m/%Y - %I:%M %p')}</b></div>", unsafe_allow_html=True)
                    if dt_limite:
                        st.markdown(f"<div style='background:#161b22; padding:6px; border-radius:6px; margin-bottom:8px; font-size:12px;'>⏰ Cierre Estricto: <b>{dt_limite.strftime('%d/%m/%Y - %I:%M %p')}</b></div>", unsafe_allow_html=True)

                    if dt_limite and not carrera_cerrada:
                        diferencia_segundos = (dt_limite - ahora_dt).total_seconds()
                        if estado_conteo == "INACTIVO" and 0 < diferencia_segundos <= 10:
                            st.session_state.estado_conteo_carrera_modalidad[clave_mod_carr] = "CONTEO_10S"
                            st.session_state.tiempo_inicio_conteo_modalidad[clave_mod_carr] = ahora_dt
                            guardar_estado_global()
                            st.rerun()
                        elif estado_conteo == "CONTEO_10S":
                            tiempo_inicio = st.session_state.tiempo_inicio_conteo_modalidad.get(clave_mod_carr, ahora_dt)
                            transcurridos = (ahora_dt - tiempo_inicio).total_seconds()
                            if transcurridos >= 12:
                                st.session_state.carreras_cerradas_remate[carr_activa] = True
                                st.session_state.estado_conteo_carrera_modalidad[clave_mod_carr] = "CERRADO"
                                guardar_estado_global()
                                st.rerun()
                            else:
                                restantes = max(0, 10 - int(transcurridos))
                                if restantes > 0:
                                    st.markdown(f"<div class='timer-box'>⚠️ ¡CIERRE INMINENTE EN: {restantes}s! (Anti-Sniper Activo)</div>", unsafe_allow_html=True)

                    remates_actuales_mod = st.session_state.remates_por_modalidad[modo_actual_remate].get(carr_activa, {})
                    tabla_html = generar_tabla_html_remate(remates_actuales_mod, st.session_state.ejemplares_retirados.get(carr_activa, []), st.session_state.ejemplares_no_valido.get(carr_activa, []))
                    components.html(tabla_html, height=220, scrolling=True)

                    if bloqueo_por_inicio:
                        st.warning(f"⏳ **Remate no disponible:** Abre a las {dt_inicio.strftime('%I:%M %p')}.")
                    elif carrera_cerrada:
                        st.error("🔒 **Remate Cerrado:** El tiempo de apuestas finalizó.")
                    else:
                        with st.container(border=True):
                            st.markdown(f"⚡ **Registro Rápido de Puja - {carr_activa}**")
                            retirados_carr_activa = st.session_state.ejemplares_retirados.get(carr_activa, [])
                            no_validos_carr_activa = st.session_state.ejemplares_no_valido.get(carr_activa, [])
                            excluidos_carr_activa = set(retirados_carr_activa) | set(no_validos_carr_activa)

                            lista_caballos_activos = [c for c in list(remates_actuales_mod.keys()) if c not in excluidos_carr_activa]
                            
                            if not lista_caballos_activos:
                                st.warning("No hay ejemplares disponibles para pujar.")
                            else:
                                k_sel_cab = f"rem_caballo_activo_click_{modo_actual_remate}_{carr_activa}"
                                if k_sel_cab not in st.session_state or st.session_state[k_sel_cab] not in lista_caballos_activos:
                                    st.session_state[k_sel_cab] = lista_caballos_activos[0]
                                    
                                st.markdown("🔹 **1. Seleccionar Ejemplar (Haz clic en el número):**")
                                
                                # --- CUADRÍCULA DE BOTONES DINÁMICOS (REGISTRO DINÁMICO) ---
                                cantidad_ejemplares = len(lista_caballos_activos)
                                cols_ejemplares = 3
                                num_filas = (cantidad_ejemplares + cols_ejemplares - 1) // cols_ejemplares
                                
                                idx_cab = 0
                                for f in range(num_filas):
                                    cols_fila = st.columns(cols_ejemplares, gap="small")
                                    for c in range(cols_ejemplares):
                                        if idx_cab < cantidad_ejemplares:
                                            cab_item = lista_caballos_activos[idx_cab]
                                            num_parte = cab_item.split(" - ")[0]
                                            
                                            info_remate_cab = remates_actuales_mod.get(cab_item, {})
                                            propietario = info_remate_cab.get('jugador', 'Sin Postor')
                                            
                                            if propietario == "Sin Postor" or propietario == "CASA" or info_remate_cab.get('monto', 0.0) == 0:
                                                color_estilo = "background-color: #e2e8f0 !important; color: #1e293b !important; border: 1px solid #cbd5e1 !important;"
                                            elif propietario == st.session_state.usuario_activo:
                                                color_estilo = "background-color: #22c55e !important; color: #ffffff !important; border: 1px solid #16a34a !important;"
                                            else:
                                                color_estilo = "background-color: #ef4444 !important; color: #ffffff !important; border: 1px solid #dc2626 !important;"

                                            with cols_fila[c]:
                                                st.markdown(f"""
                                                    <style>
                                                    div[data-testid="stVerticalBlock"] button[key="rem_btn_cab_{modo_actual_remate}_{carr_activa}_{idx_cab}"] {{
                                                        {color_estilo}
                                                    }}
                                                    </style>
                                                """, unsafe_allow_html=True)

                                                if st.button(f"#{num_parte}", key=f"rem_btn_cab_{modo_actual_remate}_{carr_activa}_{idx_cab}", use_container_width=True):
                                                    st.session_state[k_sel_cab] = cab_item
                                                    st.rerun()

                                            idx_cab += 1
                                
                                caballero_seleccionado = st.session_state[k_sel_cab]
                                propietario_actual_sel = remates_actuales_mod[caballero_seleccionado].get('jugador', 'Sin Postor')
                                
                                # Tarjeta informativa del ejemplar seleccionado
                                if propietario_actual_sel == "Sin Postor" or propietario_actual_sel == "CASA" or remates_actuales_mod[caballero_seleccionado].get('monto', 0.0) == 0:
                                    bg_tarjeta = "linear-gradient(135deg, #161b22 0%, #21262d 100%)"
                                    color_borde = "#30363d"
                                    color_poseedor = "#8b949e"
                                    icono_poseedor = "⚪"
                                elif propietario_actual_sel == st.session_state.usuario_activo:
                                    bg_tarjeta = "linear-gradient(135deg, #064e3b 0%, #065f46 100%)"
                                    color_borde = "#10b981"
                                    color_poseedor = "#34d399"
                                    icono_poseedor = "🟢"
                                else:
                                    bg_tarjeta = "linear-gradient(135deg, #7f1d1d 0%, #991b1b 100%)"
                                    color_borde = "#ef4444"
                                    color_poseedor = "#fca5a5"
                                    icono_poseedor = "🔴"

                                st.markdown(f"""
                                    <div style="background: {bg_tarjeta}; border: 2px solid {color_borde}; border-radius: 12px; padding: 12px; margin: 10px 0; text-align: center;">
                                        <div style="font-size: 11px; font-weight: 900; color: #00ffff; text-transform: uppercase;">🐎 Ejemplar Seleccionado</div>
                                        <div style="font-size: 18px; font-weight: 900; color: #f1c40f; margin: 4px 0;">{caballero_seleccionado}</div>
                                        <div style="font-size: 12px; font-weight: 700; color: {color_poseedor};">{icono_poseedor} Dueño Actual: <b>{propietario_actual_sel}</b></div>
                                    </div>
                                """, unsafe_allow_html=True)

                                puja_actual = remates_actuales_mod[caballero_seleccionado]['monto']
                                opciones_escala = obtener_siguientes_montos(puja_actual)
                                monto_puja = st.selectbox("💰 **2. Monto de Puja**", opciones_escala, format_func=lambda x: formatear_bs(x), key=f"rem_sel_monto_{modo_actual_remate}_{carr_activa}_{caballero_seleccionado}")
                                
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

    # 2. MÓDULO DE DUPLETA
    elif st.session_state.menu_principal_opcion == "Dupletas":
        st.markdown("<div class='subasta-header'>🎟️ Armado Visual de Dupletas / Tripletas</div>", unsafe_allow_html=True)
        st.info("🟢 Módulo de apuestas múltiples activo.")

    # 3. MÓDULO DE CUENTAS
    elif st.session_state.menu_principal_opcion == "Cuentas":
        st.markdown("<div class='subasta-header'>📊 Mis Cuentas y Estado de Cuenta</div>", unsafe_allow_html=True)
        jugador = st.session_state.usuario_activo
        vals = st.session_state.cuentas.get(jugador, {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0})
        st.metric("Balance Neto", formatear_bs(vals['Pujas'] - vals['Abonos'] - vals['Premios']))

    # 4. ZONA ADMIN
    elif st.session_state.menu_principal_opcion == "🔒 Zona Admin" and es_casa:
        st.markdown("<div class='subasta-header'>🔒 Panel de Configuración y Administración</div>", unsafe_allow_html=True)
        tab1, tab2, tab3 = st.tabs(["✍️ Caballos", "👥 Usuarios", "⏰ Horarios"])
        with tab1:
            st.markdown("### ✍️ Gestión de Carreras y Ejemplares")
            carr_adm = st.selectbox("Seleccionar Carrera", lista_carreras_disponibles, key="adm_carr_sel")
            if carr_adm not in st.session_state.detalles_carreras:
                st.session_state.detalles_carreras[carr_adm] = {"condicion": "Estándar"}
            cond_edit = st.text_input("Condición de la Carrera", value=st.session_state.detalles_carreras[carr_adm].get("condicion", ""), key=f"cond_{carr_adm}")
            if st.button("Guardar Condición", key=f"save_cond_{carr_adm}", type="primary"):
                st.session_state.detalles_carreras[carr_adm]["condicion"] = cond_edit
                guardar_estado_global()
                st.toast("✅ Guardado con éxito")
                st.rerun()
        with tab2:
            st.markdown("### 👥 Registro de Usuarios")
            nuevo_u = st.text_input("Nombre de Usuario", key="new_u_input")
            if st.button("Registrar Usuario", type="primary"):
                if nuevo_u and nuevo_u.strip().upper() not in st.session_state.lista_usuarios:
                    st.session_state.lista_usuarios.append(nuevo_u.strip().upper())
                    guardar_estado_global()
                    st.rerun()
        with tab3:
            st.markdown("### ⏰ Control de Horarios Anti-Sniper")
            carr_h_adm = st.selectbox("Carrera para Horario", lista_carreras_disponibles, key="adm_h_carr")
            mod_h_adm = st.selectbox("Modalidad", ["Adelantados", "Ciegos", "En Vivo"], key="adm_h_mod")
            clave_adm_h = f"{mod_h_adm}_{carr_h_adm}"
            
            f_i = st.date_input("Fecha Inicio", value=ahora_dt.date(), key=f"fi_{clave_adm_h}")
            h_i = st.number_input("Hora Inicio (1-12)", 1, 12, 2, key=f"hi_{clave_adm_h}")
            m_i = st.number_input("Minuto Inicio (0-59)", 0, 59, 0, key=f"mi_{clave_adm_h}")
            ampm_i = st.selectbox("AM/PM Inicio", ["AM", "PM"], index=1, key=f"ampi_{clave_adm_h}")
            
            f_c = st.date_input("Fecha Cierre", value=ahora_dt.date(), key=f"fc_{clave_adm_h}")
            h_c = st.number_input("Hora Cierre (1-12)", 1, 12, 2, key=f"hc_{clave_adm_h}")
            m_c = st.number_input("Minuto Cierre (0-59)", 0, 59, 30, key=f"mc_{clave_adm_h}")
            ampm_c = st.selectbox("AM/PM Cierre", ["AM", "PM"], index=1, key=f"ampc_{clave_adm_h}")

            if st.button("💾 Guardar Horario Estricto", key=f"save_h_{clave_adm_h}", type="primary"):
                hi_24 = h_i if ampm_i == "AM" else (h_i + 12 if h_i < 12 else 12)
                if ampm_i == "AM" and h_i == 12: hi_24 = 0
                hc_24 = h_c if ampm_c == "AM" else (h_c + 12 if h_c < 12 else 12)
                if ampm_c == "AM" and h_c == 12: hc_24 = 0

                st.session_state.fechas_horas_inicio_remate_modalidad[clave_adm_h] = datetime.combine(f_i, dtime(hi_24, m_i))
                st.session_state.fechas_horas_cierre_remate_modalidad[clave_adm_h] = datetime.combine(f_c, dtime(hc_24, m_c))
                st.session_state.estado_conteo_carrera_modalidad[clave_adm_h] = "INACTIVO"
                guardar_estado_global()
                st.toast("✅ ¡Horario guardado y sincronizado!")
                st.rerun()

renderizar_tiempo_real_universal()

# --- TRANSMISIÓN EN VIVO ---
url_live_video = st.session_state.get('url_video_en_vivo', '').strip()
if url_live_video:
    st.markdown("<br><hr style='border-color: #30363d;'>", unsafe_allow_html=True)
    st.markdown("### 📺 TRANSMISIÓN EN VIVO")
    st.video(url_live_video)
