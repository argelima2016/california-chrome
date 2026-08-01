import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import re
import base64
import requests
import io
import json
from bs4 import BeautifulSoup
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from pypdf import PdfReader

# Configuración de pantalla completa
st.set_page_config(page_title="Wolf Ready to Run", layout="wide", page_icon="🐺")

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

def cargar_estado_global():
    default_state = {
        'menu_principal_opcion': "Remates",
        'sub_remate_opcion': "En Vivo",
        'sub_dupleta_opcion': "Dupleta",
        'usuario_activo': "CASA",
        'lista_usuarios': ["CASA"],
        'banco_caballos_por_carrera': {},
        'remates': {},
        'ejemplares_retirados': {},
        'detalles_carreras': {},
        'historial_ganadores': {},
        'carreras_cerradas_remate': {},
        'remates_cargados_en_cuentas': {},
        'fechas_horas_cierre_remate': {},
        'estado_conteo_carrera': {},
        'tiempo_inicio_conteo': {},
        'cuentas': {"CASA": {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}},
        'historial_jugadas': [],
        'ganancia_casa': 0.0,
        'dupletas_tickets': [],
        'tripleta_tickets': [],
        'polla_tickets': [],
        'carreras_habilitadas_dupleta': [],
        'carreras_habilitadas_tripleta': [],
        'carreras_habilitadas_polla': [],
        'config_montos_especiales': {"Dupleta": 500.0, "Tripleta": 500.0, "Polla Hipica": 1000.0},
        'dupleta_bloqueada': False,
        'carreras_activas_remate': [],
        'carreras_por_modalidad': {"Adelantados": [], "Ciegos": [], "En Vivo": []},
        'total_carreras_semana': 10,
        'url_video_en_vivo': "",
        'admin_tab_seleccionada': "✍️ Caballos",
        'imagenes_carreras': {},
        'gacetas_carreras': {}
    }
    
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in default_state.items():
                    if k not in st.session_state:
                        st.session_state[k] = data.get(k, v)
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
        'lista_usuarios', 'banco_caballos_por_carrera', 'remates', 'ejemplares_retirados',
        'detalles_carreras', 'historial_ganadores', 'carreras_cerradas_remate',
        'remates_cargados_en_cuentas', 'cuentas', 'historial_jugadas', 'ganancia_casa',
        'dupletas_tickets', 'tripleta_tickets', 'polla_tickets', 'carreras_habilitadas_dupleta',
        'carreras_habilitadas_tripleta', 'carreras_habilitadas_polla', 'config_montos_especiales',
        'dupleta_bloqueada', 'carreras_activas_remate', 'carreras_por_modalidad',
        'total_carreras_semana', 'url_video_en_vivo', 'imagenes_carreras'
    ]
    data = {}
    for k in keys_to_save:
        if k in st.session_state:
            val = st.session_state[k]
            if k == 'imagenes_carreras' and isinstance(val, dict):
                continue
            data[k] = val
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

cargar_estado_global()

# --- SCRIPT JS PARA AUTO-ACTUALIZACIÓN EN TIEMPO REAL Y CONTROL TOTAL ---
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

            // --- BOTÓN FLOTANTE DE TUERCA PARA CONTROLAR EL CIERRE TOTAL DE LA BARRA LATERAL ---
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
                    const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
                    if (sidebar) {
                        const currentTransform = window.getComputedStyle(sidebar).transform;
                        const isClosed = sidebar.getAttribute('aria-expanded') === 'false' || 
                                         (currentTransform && currentTransform !== 'none' && !currentTransform.includes('matrix(1, 0, 0, 1, 0, 0)'));
                        
                        if (isClosed) {
                            sidebar.setAttribute('aria-expanded', 'true');
                            sidebar.style.transform = 'none';
                            sidebar.style.visibility = 'visible';
                            sidebar.style.display = 'block';
                            sidebar.style.minWidth = '360px';
                            sidebar.style.width = '360px';
                            sidebar.style.position = 'relative';
                        } else {
                            sidebar.setAttribute('aria-expanded', 'false');
                            sidebar.style.transform = 'translateX(-100%)';
                            sidebar.style.visibility = 'hidden';
                            sidebar.style.display = 'none';
                            sidebar.style.minWidth = '0px';
                            sidebar.style.width = '0px';
                        }
                    } else {
                        const collapseBtn = doc.querySelector('[data-testid="stSidebarCollapseButton"] button') || 
                                            doc.querySelector('[data-testid="collapsedControl"] button');
                        if (collapseBtn) collapseBtn.click();
                    }
                };

                doc.body.appendChild(tuercaBtn);
            }
        }
        setInterval(sincronizacionEnVivo, 200);
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
    logo_display = '<span style="color: #f1c40f; font-size: 26px; font-weight: 900; font-style: italic; letter-spacing: 1.5px;">CALIFORNIA CHROME</span>'

ahora_dt = obtener_hora_venezuela_local()
hora_texto = ahora_dt.strftime('%I:%M:%S %p')
fecha_texto = ahora_dt.strftime('%d/%m/%Y')

# --- ESTILOS CSS AGRESIVOS PARA MÓVILES Y ANCHO ESPACIOSO DE BARRA LATERAL ---
st.markdown("""
    <style>
    * {
        box-sizing: border-box !important;
    }
    .stApp {
        background-color: #080a0f;
        color: #f0f6fc;
        overflow-x: hidden !important;
    }
    [data-testid="stSidebar"] {
        min-width: 360px !important;
        max-width: 360px !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        width: 360px !important;
        padding-left: 1.2rem !important;
        padding-right: 1.2rem !important;
    }
    [data-testid="stToolbar"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }
    header[data-testid="stHeader"] {
        display: none !important;
    }
    footer, #MainMenu {
        visibility: hidden !important;
        display: none !important;
    }
    div[data-testid="stTabs"] {
        display: none !important;
    }
    .block-container {
        padding-top: 0.4rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
        margin: 0 auto !important;
        overflow-x: hidden !important;
    }
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        overflow-x: auto !important;
        overflow-y: hidden !important;
        -webkit-overflow-scrolling: touch !important;
        width: 100% !important;
        gap: 6px !important;
        padding-bottom: 6px !important;
        scrollbar-width: thin;
    }
    div[data-testid="stHorizontalBlock"] > div {
        flex: 0 0 auto !important;
        width: auto !important;
        min-width: 110px !important;
        max-width: none !important;
    }
    .carreras-scroll-container div[data-testid="stHorizontalBlock"] > div {
        min-width: 55px !important;
        width: 55px !important;
    }
    div[data-testid="column"] button[kind="secondary"], 
    div[data-testid="column"] button[kind="primary"] {
        border-radius: 20px !important;
        width: 100% !important;
        height: 38px !important;
        min-height: 38px !important;
        max-height: 38px !important;
        padding: 0 4px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 auto !important;
        font-size: 11px !important;
        font-weight: 900 !important;
        letter-spacing: 0.5px !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
    }
    .stButton button {
        border-radius: 6px !important;
        font-weight: 700 !important;
        padding: 0.2rem 0.4rem !important;
        min-height: 32px !important;
        font-size: 12px !important;
        letter-spacing: 0.2px;
        white-space: nowrap !important;
        max-width: 100% !important;
    }
    .subasta-header {
        font-size: clamp(14px, 3.5vw, 18px);
        font-weight: 800;
        color: #f1e05a;
        margin-bottom: 4px;
        border-bottom: 2px solid #f1e05a;
        padding-bottom: 3px;
    }
    .timer-box {
        background-color: #161b22;
        border: 1px solid #ff4757;
        padding: 6px;
        border-radius: 6px;
        text-align: center;
        font-size: clamp(12px, 3vw, 15px);
        font-weight: bold;
        color: #ff4757;
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
        word-break: break-word;
    }
    .incentivo-llamativo {
        background: linear-gradient(135deg, #1f1c2c 0%, #923d41 100%);
        border: 2px dashed #00ffff;
        padding: 10px 16px;
        border-radius: 12px;
        text-align: center;
        margin: 10px 0;
        box-shadow: 0px 0px 15px rgba(0, 255, 255, 0.4);
    }
    .incentivo-llamativo-monto {
        color: #ffffff;
        font-size: 22px;
        font-weight: 900;
        letter-spacing: 0.5px;
        text-shadow: 2px 2px 4px #000000;
    }
    .ticket-jugador-card {
        background: #0d1117;
        border: 2px solid #30363d;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 10px;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.5);
    }
    .ticket-header-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px dashed #30363d;
        padding-bottom: 6px;
        margin-bottom: 8px;
        font-size: 12px;
        font-weight: 800;
        color: #f1c40f;
    }
    .ticket-body-row {
        font-size: 13px;
        color: #f0f6fc;
        margin-bottom: 4px;
        font-weight: 600;
    }
    
    /* --- ESTILOS MODERNOS PARA LA CABECERA --- */
    .header-container-modern {
        background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 10px 14px;
        margin-bottom: 10px;
        box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.6);
        display: flex;
        flex-direction: column;
        gap: 10px;
        width: 100%;
        box-sizing: border-box;
    }
    .header-top-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;
        gap: 8px;
    }
    .header-clock-box {
        display: flex;
        flex-direction: column;
        background: #080a0f;
        border: 1px solid #21262d;
        padding: 5px 10px;
        border-radius: 8px;
    }
    .h-time {
        color: #00ffff;
        font-size: 13px;
        font-weight: 900;
        letter-spacing: 0.5px;
    }
    .h-date {
        color: #8b949e;
        font-size: 10px;
        font-weight: 700;
    }
    .header-user-card {
        display: flex;
        align-items: center;
        gap: 8px;
        background: #080a0f;
        border: 1px solid #30363d;
        padding: 5px 10px;
        border-radius: 8px;
    }
    .user-details {
        display: flex;
        flex-direction: column;
        text-align: right;
    }
    .u-name {
        color: #f0f6fc;
        font-size: 12px;
        font-weight: 800;
    }
    .u-bal {
        font-size: 10px;
        font-weight: 700;
    }
    .u-avatar-badge {
        width: 28px;
        height: 28px;
        background: #1f6feb;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
    }
    .header-bottom-row-logo {
        text-align: center;
        border-top: 1px solid #21262d;
        padding-top: 8px;
    }
    .header-logo-img {
        max-height: 45px;
        width: auto;
        object-fit: contain;
    }
    </style>
""", unsafe_allow_html=True)

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

# --- CABECERA SUPERIOR MODERNA ---
header_html = f"""
    <div class="header-container-modern">
        <div class="header-top-row">
            <div class="header-clock-box">
                <span class="h-time">⚡ {hora_texto}</span>
                <span class="h-date">📅 {fecha_texto}</span>
            </div>
            <div class="header-user-card">
                <div class="user-details">
                    <span class="u-name">{usuario_en_sesion}</span>
                    <span class="u-bal" style="color: {color_balance};">{etiqueta_balance}</span>
                </div>
                <div class="u-avatar-badge">🐺</div>
            </div>
        </div>
        <div class="header-bottom-row-logo">
            {logo_display}
        </div>
    </div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# Botón superior flotante para refrescar pantalla manualmente al instante desde cualquier dispositivo
col_ref_sync1, col_ref_sync2 = st.columns([6, 1])
with col_ref_sync2:
    if st.button("🔄 Sincronizar", use_container_width=True):
        cargar_estado_global()
        st.rerun()

def obtener_abreviatura_carrera(nombre_carrera, modo_ciego=False):
    if modo_ciego:
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

def generar_tabla_html_remate(remates_dict, retirados_list):
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
        clase_fila = "retirado-row" if es_retirado else ""
        etiqueta_estado = " (RETIRADO)" if es_retirado else ""
        
        html += f"""
                <tr class="{clase_fila}">
                    <td><span class="badge-numero {badge_class}">{num}</span></td>
                    <td style="font-weight: 800; font-size: 12px;" title="{nombre_solo.upper()}{etiqueta_estado}">{nombre_solo.upper()}{etiqueta_estado}</td>
                    <td title="{info['jugador']}">{info['jugador']}</td>
                    <td style="font-weight: bold; color: { '#990000' if es_retirado else '#000000' };">{formatear_bs(info['monto'])}</td>
                </tr>
        """
    html += """
            </tbody>
        </table>
    </div>
    """
    return html

if not st.session_state.remates:
    for i in range(1, st.session_state.total_carreras_semana + 1):
        carr_nombre = f"Carrera {i}"
        st.session_state.banco_caballos_por_carrera[carr_nombre] = [f"{j} - Ejemplar {j}" for j in range(1, 11)]
        st.session_state.remates[carr_nombre] = {f"{j} - Ejemplar {j}": {"jugador": "Sin Postor", "monto": 0.0} for j in range(1, 11)}
        st.session_state.detalles_carreras[carr_nombre] = {
            "condicion": "Condición estándar", 
            "distancia": "1200 mts", 
            "hora": "02:00 PM", 
            "monto_fijo_ciego": 500.0, 
            "incentivo_adelantados": 0.0,
            "incentivo_ciegos": 0.0,
            "incentivo_envivo": 0.0,
            "hora_cierre_real": "No registrada"
        }

lista_carreras_disponibles = list(st.session_state.remates.keys())

if not st.session_state.carreras_activas_remate and lista_carreras_disponibles:
    st.session_state.carreras_activas_remate = list(lista_carreras_disponibles)
if not st.session_state.carreras_habilitadas_dupleta and lista_carreras_disponibles:
    st.session_state.carreras_habilitadas_dupleta = list(lista_carreras_disponibles)
if not st.session_state.carreras_habilitadas_tripleta and lista_carreras_disponibles:
    st.session_state.carreras_habilitadas_tripleta = list(lista_carreras_disponibles)
if not st.session_state.carreras_habilitadas_polla and lista_carreras_disponibles:
    st.session_state.carreras_habilitadas_polla = list(lista_carreras_disponibles)

for mod in ["Adelantados", "Ciegos", "En Vivo"]:
    if not st.session_state.carreras_por_modalidad.get(mod) and lista_carreras_disponibles:
        if mod == "Ciegos":
            st.session_state.carreras_por_modalidad[mod] = lista_carreras_disponibles[:2]
        else:
            st.session_state.carreras_por_modalidad[mod] = list(lista_carreras_disponibles)

# --- MENÚ PRINCIPAL HORIZONTAL ---
st.markdown('<div class="carrusel-horizontal-box">', unsafe_allow_html=True)
col_menu1, col_menu2, col_menu3, col_menu4 = st.columns(4, gap="small")

with col_menu1:
    if st.button("REMATES", key="menu_btn_remates_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Remates" else "secondary"):
        st.session_state.menu_principal_opcion = "Remates"
        guardar_estado_global()
        st.rerun()

with col_menu2:
    if st.button("DUPLETAS/POLLAS", key="menu_btn_dupletas_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Dupletas" else "secondary"):
        st.session_state.menu_principal_opcion = "Dupletas"
        guardar_estado_global()
        st.rerun()

with col_menu3:
    if st.button("CUENTAS", key="menu_btn_cuentas_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Cuentas" else "secondary"):
        st.session_state.menu_principal_opcion = "Cuentas"
        guardar_estado_global()
        st.rerun()

with col_menu4:
    if st.button("⚙️ CONFIG", key="menu_btn_config_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "🔒 Zona Admin" else "secondary"):
        st.session_state.menu_principal_opcion = "🔒 Zona Admin"
        guardar_estado_global()
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<hr style='margin: 0.3rem 0; border-color: #21262d;'>", unsafe_allow_html=True)

# --- BANNER MARQUESINA DINÁMICO ---
elementos_carrusel_info = []

remates_abiertos = [c for c in lista_carreras_disponibles if not st.session_state.carreras_cerradas_remate.get(c, False)]
if remates_abiertos:
    texto_remates = "🟢 REMATES ABIERTOS: " + " | ".join(remates_abiertos)
    elementos_carrusel_info.append(texto_remates)
else:
    elementos_carrusel_info.append("🔴 TODOS LOS REMATES CERRADOS")

dupletas_hab = [c for c in st.session_state.carreras_habilitadas_dupleta if c in lista_carreras_disponibles]
if dupletas_hab:
    texto_dupletas = "🎟️ DUPLETAS DISPONIBLES EN: " + " - ".join(dupletas_hab)
    elementos_carrusel_info.append(texto_dupletas)

if st.session_state.historial_ganadores:
    for carr_g, info_g in st.session_state.historial_ganadores.items():
        ganador_jugador = info_g.get('Ganador', 'N/A')
        ejemplar_ganador_nombre = "N/A"
        for h in st.session_state.historial_jugadas:
            if h.get('carrera') == carr_g and h.get('jugador') == ganador_jugador and "Remate" in h.get('tipo', ''):
                ejemplar_ganador_nombre = h.get('detalle', 'N/A')
                break
        texto_ganador = "🏆 " + carr_g.upper() + " GANADOR: " + ganador_jugador + " (" + ejemplar_ganador_nombre + ")"
        elementos_carrusel_info.append(texto_ganador)
else:
    elementos_carrusel_info.append("⏳ ESPERANDO PRIMEROS RESULTADOS DE GANADORES...")

if elementos_carrusel_info:
    texto_unido_marquesina = " &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ".join(elementos_carrusel_info)
    html_banner_marquesina = f"""
    <style>
        .marquee-container {{
            width: 100%;
            background: transparent;
            border: none;
            box-shadow: none;
            padding: 8px 0;
            margin-bottom: 12px;
            overflow: hidden;
            box-sizing: border-box;
            display: flex;
            align-items: center;
        }}
        .marquee-text {{
            display: inline-block;
            white-space: nowrap;
            animation: scrollRight 80s linear infinite;
            font-family: 'Arial Black', Gadget, sans-serif;
            font-size: 15px;
            font-weight: 900;
            color: #00ffff;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            text-shadow: 0px 0px 10px rgba(0, 255, 255, 0.9), 2px 2px 2px #000000;
            padding-right: 100%;
        }}
        @keyframes scrollRight {{
            0% {{
                transform: translateX(-100%);
            }}
            100% {{
                transform: translateX(100%);
            }}
        }}
        .marquee-container:hover .marquee-text {{
            animation-play-state: paused;
        }}
    </style>
    <div class="marquee-container">
        <div class="marquee-text">{texto_unido_marquesina}</div>
    </div>
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
    js_images_array = str(lista_b64_banners)
    html_slider = f"""
    <style>
        body {{ margin: 0; padding: 0; background-color: #080a0f; overflow: hidden; }}
        .banner-slider-container {{ width: 100vw; height: 240px; margin: 0; padding: 0; overflow: hidden; position: relative; background-color: #080a0f; }}
        .banner-slide-img {{ width: 100%; height: 100%; object-fit: cover; transition: opacity 1.2s ease-in-out; display: block; }}
    </style>
    <div class="banner-slider-container">
        <img id="rinconada-slide" class="banner-slide-img" src="{lista_b64_banners[0]}" />
    </div>
    <script>
        (function() {{
            var images = {js_images_array};
            var index = 0;
            var imgElement = document.getElementById("rinconada-slide");
            if(images.length > 1) {{
                setInterval(function() {{
                    index = (index + 1) % images.length;
                    imgElement.style.opacity = "0.15";
                    setTimeout(function() {{
                        imgElement.src = images[index];
                        imgElement.style.opacity = "1";
                    }}, 400);
                }}, 8000);
            }}
        }})();
    </script>
    """
    components.html(html_slider, height=245)
else:
    st.markdown("""
        <div style="background: linear-gradient(90deg, #11141d 0%, #1f2937 100%); padding: 15px; text-align: center; margin-bottom: 10px; border-radius: 6px;">
            <h3 style="color: #f1c40f; margin: 0; font-weight: 900; letter-spacing: 1px; font-size: 16px;">INH - HIPÓDROMO DE LA RINCONADA</h3>
            <p style="color: #8b949e; font-size: 11px; margin: 4px 0 0 0;">¡La pasión del hipismo venezolano en vivo!</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- BARRA LATERAL ---
st.sidebar.header("barra lateral")
ahora_dt = obtener_hora_venezuela_local()
st.sidebar.markdown(f"🕒 **Hora:** `{ahora_dt.strftime('%I:%M:%S %p')}`")

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

with st.sidebar.expander("🔒 Estado Dupletas / Polla", expanded=False):
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
    
    col_cz1, col_cz2 = st.columns(2)
    with col_cz1:
        fecha_cierre_adm = st.date_input("Fecha límite", value=ahora_dt.date(), key=f"sb_f_cierre_{carr_seleccionada_liq}")
    with col_cz2:
        hora_cierre_adm = st.time_input("Hora límite", value=datetime.now().time(), key=f"sb_h_cierre_{carr_seleccionada_liq}")
    
    if st.button("💾 Guardar Cierre Estricto", key=f"sb_btn_guardar_h_{carr_seleccionada_liq}", use_container_width=True):
        dt_cierre_estricto = datetime.combine(fecha_cierre_adm, hora_cierre_adm)
        st.session_state.fechas_horas_cierre_remate[carr_seleccionada_liq] = dt_cierre_estricto
        st.session_state.estado_conteo_carrera[carr_seleccionada_liq] = "INACTIVO"
        guardar_estado_global()
        st.toast(f"✅ Cierre estricto guardado para {carr_seleccionada_liq}")
        st.rerun()

    st.markdown("---")
    if not c_cerrada_actual:
        if st.button("🔒 Cerrar Remate Manual", key=f"sb_liq_cerrar_{carr_seleccionada_liq}", use_container_width=True, type="primary"):
            st.session_state.carreras_cerradas_remate[carr_seleccionada_liq] = True
            st.session_state.estado_conteo_carrera[carr_seleccionada_liq] = "CERRADO"
            st.session_state.detalles_carreras[carr_seleccionada_liq]["hora_cierre_real"] = ahora_dt.strftime('%I:%M:%S %p')
            if not st.session_state.remates_cargados_en_cuentas.get(carr_seleccionada_liq, False):
                retirados_carr = st.session_state.ejemplares_retirados.get(carr_seleccionada_liq, [])
                for cab, info in st.session_state.remates[carr_seleccionada_liq].items():
                    if cab in retirados_carr:
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
# 1. MÓDULO DE REMATES
# =========================================================================
if menu_principal_opcion == "Remates":
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

    if not lista_carreras_disponibles:
        st.warning("⚠️ No hay carreras cargadas en el sistema.")
    else:
        carreras_modalidad_permitidas = st.session_state.carreras_por_modalidad.get(modo_actual_remate, lista_carreras_disponibles)
        if modo_actual_remate == "Ciegos" and len(carreras_modalidad_permitidas) > 2:
            carreras_modalidad_permitidas = carreras_modalidad_permitidas[:2]
        
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
                es_modo_ciego = (modo_actual_remate == "Ciegos")
                abreviatura = obtener_abreviatura_carrera(c_nombre, modo_ciego=es_modo_ciego)
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

            carrera_cerrada = st.session_state.carreras_cerradas_remate.get(carr_activa, False)
            estado_icono = "🔴" if carrera_cerrada else "🟢"
            
            col_st1, col_st2 = st.columns([3, 1], gap="small")
            with col_st1:
                st.markdown(f"""
                    <div style="font-size: 14px; font-weight: 800; color: #f0f6fc; display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                        <span>{estado_icono}</span>
                        <span>{carr_activa}</span>
                        <span style="font-size: 11px; font-weight: 600; color: #8b949e; background: #161b22; padding: 1px 6px; border-radius: 4px; border: 1px solid #30363d;">{modo_actual_remate}</span>
                    </div>
                """, unsafe_allow_html=True)
            with col_st2:
                if carr_activa in st.session_state.gacetas_carreras:
                    st.download_button(
                        label="📰 Gaceta",
                        data=st.session_state.gacetas_carreras[carr_activa],
                        file_name=f"gaceta_{carr_activa.lower().replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        key=f"btn_descargar_gaceta_{carr_activa}",
                        use_container_width=True
                    )
                else:
                    st.markdown("<span style='font-size: 10px; color: #8b949e; text-align: right; display: block; padding-top: 6px;'>Sin Gaceta</span>", unsafe_allow_html=True)

            if carr_activa not in st.session_state.detalles_carreras:
                st.session_state.detalles_carreras[carr_activa] = {
                    "condicion": "Condición general", 
                    "distancia": "1200 mts", 
                    "hora": "02:00 PM", 
                    "monto_fijo_ciego": 500.0, 
                    "incentivo_adelantados": 0.0,
                    "incentivo_ciegos": 0.0,
                    "incentivo_envivo": 0.0,
                    "hora_cierre_real": "No registrada"
                }
            
            detalles_carr = st.session_state.detalles_carreras[carr_activa]
            st.markdown(f"""
                <div class="carrera-condicion-card">
                    <b>🏁 {carr_activa}</b><br>
                    🏷️ <b>Condición:</b> {detalles_carr.get('condicion', 'N/A')}<br>
                    📏 <b>Distancia:</b> {detalles_carr.get('distancia', 'N/A')} &nbsp;|&nbsp; ⏰ <b>Hora:</b> {detalles_carr.get('hora', 'N/A')}
                </div>
            """, unsafe_allow_html=True)

            if carr_activa not in st.session_state.ejemplares_retirados:
                st.session_state.ejemplares_retirados[carr_activa] = []
            
            lista_todos_caballos_carr = list(st.session_state.remates[carr_activa].keys())
            retirados_actuales_carr = st.session_state.ejemplares_retirados[carr_activa]

            with st.expander("🚫 Gestionar Ejemplares Retirados", expanded=False):
                nuevos_retirados = st.multiselect(
                    "Selecciona los ejemplares retirados en esta carrera:",
                    options=lista_todos_caballos_carr,
                    default=retirados_actuales_carr,
                    key=f"multiselect_retirados_{carr_activa}"
                )
                if st.button("💾 Actualizar Retirados", key=f"btn_save_retirados_{carr_activa}", use_container_width=True, type="primary"):
                    retirados_anteriores = set(retirados_actuales_carr)
                    retirados_nuevos_set = set(nuevos_retirados)
                    recien_retirados = retirados_nuevos_set - retirados_anteriores

                    for cab_ret in recien_retirados:
                        info_cab = st.session_state.remates[carr_activa].get(cab_ret, {})
                        comprador = info_cab.get('jugador', 'Sin Postor')
                        monto_ej = info_cab.get('monto', 0.0)

                        if comprador != "Sin Postor" and monto_ej > 0:
                            if comprador in st.session_state.cuentas:
                                st.session_state.cuentas[comprador]['Pujas'] = max(0.0, st.session_state.cuentas[comprador]['Pujas'] - monto_ej)
                                st.session_state.historial_jugadas.append({
                                    "fecha": ahora_dt.strftime('%d/%m/%Y %I:%M:%S %p'),
                                    "jugador": comprador,
                                    "tipo": "Retirado (Descuento)",
                                    "carrera": carr_activa,
                                    "detalle": f"Ejemplar retirado: {cab_ret}",
                                    "monto": -monto_ej
                                })

                    for t_polla in st.session_state.polla_tickets:
                        for leg in t_polla['legs']:
                            base_ej_p = leg['ejemplar'].split(" (")[0]
                            if leg['carrera'] == carr_activa and base_ej_p in nuevos_retirados:
                                idx_ret = lista_todos_caballos_carr.index(base_ej_p)
                                siguiente_cab = None
                                for siguiente_c in lista_todos_caballos_carr[idx_ret + 1:] + lista_todos_caballos_carr[:idx_ret]:
                                    if siguiente_c not in nuevos_retirados:
                                        siguiente_cab = siguiente_c
                                        break
                                if siguiente_cab:
                                    leg['ejemplar'] = f"{siguiente_cab} (Sustituto por retiro)"

                    for lista_tkts in [st.session_state.dupletas_tickets, st.session_state.tripleta_tickets]:
                        for t_dup in lista_tkts:
                            if t_dup.get('estado', 'Pendiente') == 'Pendiente':
                                afect = False
                                for leg in t_dup['legs']:
                                    base_ej_t = leg['ejemplar'].split(" (")[0]
                                    if leg['carrera'] == carr_activa and base_ej_t in nuevos_retirados:
                                        afect = True
                                        break
                                if afect:
                                    t_dup['estado'] = 'Nulo (Retirado)'
                                    jug_t = t_dup['jugador']
                                    monto_t = t_dup['monto']
                                    if jug_t in st.session_state.cuentas:
                                        st.session_state.cuentas[jug_t]['Pujas'] = max(0.0, st.session_state.cuentas[jug_t]['Pujas'] - monto_t)
                                    st.session_state.historial_jugadas.append({
                                        "fecha": ahora_dt.strftime('%d/%m/%Y %I:%M:%S %p'),
                                        "jugador": jug_t,
                                        "tipo": "Ticket Anulado (Retiro)",
                                        "carrera": carr_activa,
                                        "detalle": f"Ticket {t_dup['id']} anulado por retiro",
                                        "monto": -monto_t
                                    })

                    st.session_state.ejemplares_retirados[carr_activa] = nuevos_retirados
                    guardar_estado_global()
                    st.toast("✅ ¡Ejemplares retirados actualizados y tickets ajustados!")
                    st.rerun()

            dt_limite = st.session_state.fechas_horas_cierre_remate.get(carr_activa)
            estado_conteo = st.session_state.estado_conteo_carrera.get(carr_activa, "INACTIVO")
            
            if dt_limite:
                st.markdown(f"<div class='cierre-info-box' style='background:#161b22; padding:6px; border-radius:6px; margin-bottom:8px; border:1px solid #30363d;'>⏰ Cierre Estricto: <b>{dt_limite.strftime('%d/%m/%Y - %I:%M %p')}</b></div>", unsafe_allow_html=True)

            if dt_limite and not carrera_cerrada:
                diferencia_segundos = (dt_limite - ahora_dt).total_seconds()
                if estado_conteo == "INACTIVO":
                    if 0 < diferencia_segundos <= 10:
                        st.session_state.estado_conteo_carrera[carr_activa] = "CONTEO_10S"
                        st.session_state.tiempo_inicio_conteo[carr_activa] = ahora_dt
                        guardar_estado_global()
                        st.rerun()
                    elif diferencia_segundos <= 0:
                        st.session_state.carreras_cerradas_remate[carr_activa] = True
                        st.session_state.estado_conteo_carrera[carr_activa] = "CERRADO"
                        st.session_state.detalles_carreras[carr_activa]["hora_cierre_real"] = ahora_dt.strftime('%I:%M:%S %p')
                        guardar_estado_global()
                        st.rerun()
                elif estado_conteo == "CONTEO_10S":
                    tiempo_inicio = st.session_state.tiempo_inicio_conteo.get(carr_activa, ahora_dt)
                    transcurridos = (ahora_dt - tiempo_inicio).total_seconds()
                    if transcurridos >= 12:
                        st.session_state.carreras_cerradas_remate[carr_activa] = True
                        st.session_state.estado_conteo_carrera[carr_activa] = "CERRADO"
                        st.session_state.detalles_carreras[carr_activa]["hora_cierre_real"] = ahora_dt.strftime('%I:%M:%S %p')
                        guardar_estado_global()
                        st.rerun()
                    else:
                        restantes_10s = max(0, 10 - int(transcurridos))
                        if restantes_10s > 0:
                            st.markdown(f"<div class='timer-box'>⚠️ CIERRE EN: <b>{restantes_10s}s</b> ({carr_activa})</div>", unsafe_allow_html=True)

            tabla_html = generar_tabla_html_remate(st.session_state.remates[carr_activa], st.session_state.ejemplares_retirados.get(carr_activa, []))
            cantidad_filas = len(st.session_state.remates[carr_activa])
            altura_dinamica = min(max(140, (cantidad_filas * 35) + 50), 420)
            components.html(tabla_html, height=altura_dinamica, scrolling=True)
            
            # --- POTE, PREMIO E INCENTIVO LLAMATIVO DEBAJO DE LA TABLA DE REMATE ---
            retirados_carr_activa = st.session_state.ejemplares_retirados.get(carr_activa, [])
            total_pote = sum([info['monto'] for cab_n, info in st.session_state.remates[carr_activa].items() if cab_n not in retirados_carr_activa])
            monto_casa = total_pote * (porcentaje_casa / 100)
            pote_neto_base = total_pote - monto_casa

            if modo_actual_remate == "Adelantados":
                incentivo_actual = float(detalles_carr.get('incentivo_adelantados', 0.0))
            elif modo_actual_remate == "Ciegos":
                incentivo_actual = float(detalles_carr.get('incentivo_ciegos', 0.0))
            else:
                incentivo_actual = float(detalles_carr.get('incentivo_envivo', 0.0))

            premio_total_calculado = pote_neto_base + incentivo_actual

            if incentivo_actual > 0:
                st.markdown(f"""
                    <div class="incentivo-llamativo">
                        <div class="incentivo-llamativo-monto">🎁 {formatear_bs(incentivo_actual)}</div>
                    </div>
                """, unsafe_allow_html=True)

            c_m1, c_m2 = st.columns(2)
            c_m1.metric(f"💰 Pote ({carr_activa})", formatear_bs(total_pote))
            c_m2.metric(f"🏆 Premio Total ({carr_activa})", formatear_bs(premio_total_calculado))

            with st.container(border=True):
                st.markdown(f"<p style='font-size: 11px; font-weight: 700; margin-bottom: 2px; color: #f1e05a;'>🎯 Ganador - {carr_activa}</p>", unsafe_allow_html=True)
                if carr_activa in st.session_state.historial_ganadores:
                    info_ganador_prev = st.session_state.historial_ganadores[carr_activa]
                    st.success(f"✅ Ganador: **{info_ganador_prev.get('Ganador', 'N/A')}** | Premio: **{info_ganador_prev.get('Premio', '0')}**")
                else:
                    caballos_lista_ganador = [c for c in list(st.session_state.remates[carr_activa].keys()) if c not in st.session_state.ejemplares_retirados.get(carr_activa, [])]
                    if not caballos_lista_ganador:
                        caballos_lista_ganador = list(st.session_state.remates[carr_activa].keys())
                    col_g1, col_g2 = st.columns([3, 2], gap="small")
                    with col_g1:
                        caballo_ganador_elegido = st.selectbox("Ejemplar Ganador", caballos_lista_ganador, key=f"rem_sel_ganador_{carr_activa}", label_visibility="collapsed")
                    with col_g2:
                        if st.button("🏆 Liquidar", key=f"rem_btn_liquidar_{carr_activa}", use_container_width=True, type="primary"):
                            retirados_carr_liq = st.session_state.ejemplares_retirados.get(carr_activa, [])
                            pote_carr_total = sum([info['monto'] for cab_n, info in st.session_state.remates[carr_activa].items() if cab_n not in retirados_carr_liq])
                            monto_casa_calc = pote_carr_total * (porcentaje_casa / 100)
                            
                            if modo_actual_remate == "Adelantados":
                                incentivo_establecido = float(detalles_carr.get('incentivo_adelantados', 0.0))
                            elif modo_actual_remate == "Ciegos":
                                incentivo_establecido = float(detalles_carr.get('incentivo_ciegos', 0.0))
                            else:
                                incentivo_establecido = float(detalles_carr.get('incentivo_envivo', 0.0))

                            premio_final_liq = pote_carr_total - monto_casa_calc + incentivo_establecido
                            
                            info_g = st.session_state.remates[carr_activa][caballo_ganador_elegido]
                            if info_g['jugador'] != "Sin Postor":
                                if info_g['jugador'] not in st.session_state.cuentas:
                                    st.session_state.cuentas[info_g['jugador']] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                                st.session_state.cuentas[info_g['jugador']]['Premios'] += premio_final_liq
                            st.session_state.ganancia_casa += monto_casa_calc
                            st.session_state.historial_ganadores[carr_activa] = {"Ganador": info_g['jugador'], "Premio": formatear_bs(premio_final_liq)}
                            guardar_estado_global()
                            st.success(f"✅ ¡Premio liquidado a **{info_g['jugador']}**!")
                            st.rerun()

            with st.expander(f"📜 Historial de Pujas - {carr_activa} ({modo_actual_remate})", expanded=False):
                historial_carrera_actual = [
                    h for h in st.session_state.historial_jugadas 
                    if h.get('carrera') == carr_activa and "Remate" in h.get('type', h.get('tipo', ''))
                ]
                if not historial_carrera_actual:
                    st.info(f"ℹ️ No hay registros de pujas para {carr_activa}.")
                else:
                    datos_h_carr = []
                    for h in reversed(historial_carrera_actual):
                        datos_h_carr.append({
                            "Fecha / Hora": h.get('fecha', ''),
                            "Modo": h.get('tipo', ''),
                            "Jugador": h.get('jugador', ''),
                            "Ejemplar": h.get('detalle', ''),
                            "Monto": formatear_bs(h.get('monto', 0.0))
                        })
                    st.dataframe(pd.DataFrame(datos_h_carr), use_container_width=True, hide_index=True)

            with st.container(border=True):
                if modo_actual_remate == "Ciegos":
                    st.markdown(f"🙈 **Remate Ciego - Asignación de Ejemplar ({carr_activa})**")
                    monto_fijo_carrera = detalles_carr.get('monto_fijo_ciego', 500.0)

                    caballos_disponibles_ciego = [
                        cab for cab, info in st.session_state.remates[carr_activa].items() 
                        if (info['jugador'] == "Sin Postor" or info['monto'] <= 0) and cab not in retirados_carr_activa
                    ]

                    if not caballos_disponibles_ciego:
                        st.warning("⚠️ Todos los ejemplares disponibles de esta carrera ya han sido adquiridos.")
                    else:
                        st.markdown("🎲 **Panel Didáctico (Elige un número para asignar):**")
                        cols_ciego_grid = st.columns(min(8, len(caballos_disponibles_ciego)), gap="small")
                        for idx_cb, cb_disp in enumerate(caballos_disponibles_ciego):
                            c_idx = idx_cb % len(cols_ciego_grid)
                            num_cb_parte = cb_disp.split(" - ")[0]
                            with cols_ciego_grid[c_idx]:
                                if carrera_cerrada:
                                    st.button(f"🔒#{num_cb_parte}", key=f"btn_ciego_grid_{carr_activa}_{cb_disp}", use_container_width=True, disabled=True)
                                else:
                                    if st.button(f"#{num_cb_parte}", key=f"btn_ciego_grid_{carr_activa}_{cb_disp}", use_container_width=True, type="primary"):
                                        st.session_state.remates[carr_activa][cb_disp] = {
                                            "jugador": st.session_state.usuario_activo, 
                                            "monto": monto_fijo_carrera
                                        }
                                        st.session_state.historial_jugadas.append({
                                            "fecha": ahora_dt.strftime('%d/%m/%Y %I:%M:%S %p'),
                                            "jugador": st.session_state.usuario_activo,
                                            "tipo": f"Remate Ciego ({modo_actual_remate})",
                                            "carrera": carr_activa,
                                            "detalle": cb_disp,
                                            "monto": monto_fijo_carrera
                                        })
                                        if st.session_state.usuario_activo not in st.session_state.cuentas:
                                            st.session_state.cuentas[st.session_state.usuario_activo] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                                        st.session_state.cuentas[st.session_state.usuario_activo]['Pujas'] += monto_fijo_carrera
                                        guardar_estado_global()
                                        st.success(f"🎉 #{num_cb_parte} asignado a **{st.session_state.usuario_activo}** ({formatear_bs(monto_fijo_carrera)})!")
                                        st.rerun()
                else:
                    st.markdown(f"⚡ **Registro Rápido de Puja - {carr_activa}**")
                    lista_caballos_activos = [c for c in list(st.session_state.remates[carr_activa].keys()) if c not in retirados_carr_activa]
                    
                    if not lista_caballos_activos:
                        st.warning("No hay ejemplares disponibles.")
                    else:
                        k_sel_cab = f"rem_caballo_activo_click_{carr_activa}"
                        if k_sel_cab not in st.session_state or st.session_state[k_sel_cab] not in lista_caballos_activos:
                            st.session_state[k_sel_cab] = lista_caballos_activos[0]
                            
                        st.markdown(f"🔹 **1. Seleccionar Ejemplar (Disponibles: {len(lista_caballos_activos)}):**")
                        cantidad_ejemplares = len(lista_caballos_activos)
                        cols_ejemplares = min(5, cantidad_ejemplares) if cantidad_ejemplares > 0 else 1
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
                                    st.session_state.remates[carr_activa][caballo_seleccionado] = {"jugador": st.session_state.usuario_activo, "monto": monto_puja}
                                    st.session_state.historial_jugadas.append({
                                        "fecha": ahora_dt.strftime('%d/%m/%Y %I:%M:%S %p'),
                                        "jugador": st.session_state.usuario_activo,
                                        "tipo": f"Remate ({modo_actual_remate})",
                                        "carrera": carr_activa,
                                        "detalle": caballo_seleccionado,
                                        "monto": monto_puja
                                    })
                                    if estado_conteo == "CONTEO_10S":
                                        st.session_state.tiempo_inicio_conteo[carr_activa] = obtener_hora_venezuela_local()
                                    guardar_estado_global()
                                    st.success("✅ ¡Puja registrada correctamente!")
                                    st.rerun()

# =========================================================================
# 2. MÓDULO DE DUPLETAS, TRIPLETAS Y POLLA HÍPICA
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
        if st.button("🏇 Polla", key="sub_dup_polla", use_container_width=True, type="primary" if st.session_state.sub_dupleta_opcion == "Polla Hipica" else "secondary"):
            st.session_state.sub_dupleta_opcion = "Polla Hipica"
            guardar_estado_global()
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<hr style='margin: 0.3rem 0; border-color: #21262d;'>", unsafe_allow_html=True)
    sub_dup_actual = st.session_state.sub_dupleta_opcion

    st.markdown(f"<div class='subasta-header'>🎟️ Armado Visual de {sub_dup_actual}</div>", unsafe_allow_html=True)
    if st.session_state.dupleta_bloqueada:
        st.error("🔒 **BLOQUEADO:** Emisión cerrada temporalmente.")

    monto_unico_seccion = st.session_state.config_montos_especiales.get(sub_dup_actual, 500.0)

    if sub_dup_actual == "Dupleta":
        pote_total = sum([t['monto'] for t in st.session_state.dupletas_tickets if t.get('estado') == 'Pendiente'])
        st.metric("💰 Pote Acumulado Dupletas", formatear_bs(pote_total))
        carreras_permitidas = [c for c in st.session_state.carreras_habilitadas_dupleta if c in lista_carreras_disponibles]
    elif sub_dup_actual == "Tripleta":
        pote_total = sum([t['monto'] for t in st.session_state.tripleta_tickets if t.get('estado') == 'Pendiente'])
        st.metric("💰 Pote Acumulado Tripletas", formatear_bs(pote_total))
        carreras_permitidas = [c for c in st.session_state.carreras_habilitadas_tripleta if c in lista_carreras_disponibles]
    else:
        pote_total = sum([t['monto'] for t in st.session_state.polla_tickets])
        st.metric("💰 Pote Acumulado Polla", formatear_bs(pote_total))
        carreras_permitidas = [c for c in st.session_state.carreras_habilitadas_polla if c in lista_carreras_disponibles]

    # --- CARRUSEL DESLIZANTE CON TARJETAS MÁS LARGAS (VERTICALES) ---
    cards_html_slider = ""
    for carr_h in carreras_permitidas:
        det_h = st.session_state.detalles_carreras.get(carr_h, {})
        cond_h = det_h.get('condicion', 'Carrera oficial')
        dist_h = det_h.get('distancia', '1200 mts')
        hora_h = det_h.get('hora', '02:00 PM')
        
        img_carr_b64 = ""
        if carr_h in st.session_state.imagenes_carreras:
            try:
                img_obj = st.session_state.imagenes_carreras[carr_h]
                if hasattr(img_obj, "read"):
                    img_bytes = img_obj.getvalue()
                else:
                    with open(img_obj, "rb") as f_img:
                        img_bytes = f_img.read()
                img_carr_b64 = base64.b64encode(img_bytes).decode('utf-8')
            except Exception:
                pass

        if img_carr_b64:
            media_content = f'<img src="data:image/jpeg;base64,{img_carr_b64}" style="width:100%; height:320px; object-fit:cover; border-radius:10px; margin-bottom:12px;" />'
        else:
            media_content = f'<div style="width:100%; height:320px; background:#161b22; border:1px dashed #30363d; display:flex; align-items:center; justify-content:center; border-radius:10px; margin-bottom:12px; color:#8b949e; font-size:14px; font-weight:700;">{carr_h}</div>'

        cards_html_slider += f"""
            <div style="flex: 0 0 240px; background: #0d1117; border: 1px solid #30363d; border-radius: 14px; padding: 14px; text-align: left; box-shadow: 0px 6px 18px rgba(0,0,0,0.7); display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    {media_content}
                    <div style="color: #f1c40f; font-size: 16px; font-weight: 900; margin-bottom: 6px;">{carr_h}</div>
                    <div style="color: #8b949e; font-size: 11px; line-height: 1.4; white-space: normal; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;">{cond_h}</div>
                </div>
                <div style="color: #ffffff; font-size: 11px; font-weight: 700; margin-top: 12px; border-top: 1px solid #21262d; padding-top: 8px;">📏 {dist_h} &nbsp;|&nbsp; ⏰ {hora_h}</div>
            </div>
        """

    if cards_html_slider:
        st.markdown("🖼️ **Carrusel de Carreras Disponibles (Tarjetas Verticales Amplias):**")
        st.markdown(f"""
            <div style="display: flex; overflow-x: auto; gap: 14px; padding-bottom: 14px; margin-bottom: 16px; scrollbar-width: thin;">
                {cards_html_slider}
            </div>
        """, unsafe_allow_html=True)

    # --- SELECTOR VERTICAL FIJO ---
    with st.container(border=True):
        st.markdown(f"👤 **Jugador Activo:** `{st.session_state.usuario_activo}` &nbsp;|&nbsp; 💵 **Costo Ticket:** `{formatear_bs(monto_unico_seccion)}`")
        st.markdown("---")

        if not carreras_permitidas:
            st.warning(f"⚠️ No hay carreras habilitadas para **{sub_dup_actual}**. Configúralas en Zona Admin.")
        else:
            seleccion_legs = []
            valido_legs = True
            carreras_usadas = set()

            cantidad_pasos = 2 if sub_dup_actual == "Dupleta" else (3 if sub_dup_actual == "Tripleta" else len(carreras_permitidas))

            for paso in range(cantidad_pasos):
                st.markdown(f"🔹 **Paso {paso + 1} de {cantidad_pasos}**")
                
                carr_leg = carreras_permitidas[paso % len(carreras_permitidas)]
                
                st.markdown(f"🏁 **Carrera fija:** `{carr_leg}`")
                
                retirados_carr_t = st.session_state.ejemplares_retirados.get(carr_leg, [])
                todos_caballos_carr = list(st.session_state.remates.get(carr_leg, {}).keys())
                caballos_in_carr = [c for c in todos_caballos_carr if c not in retirados_carr_t]
                
                if retirados_carr_t and sub_dup_actual in ["Dupleta", "Tripleta"]:
                    st.markdown(f"<p style='color: #ff4757; font-size: 11px; font-weight: bold;'>⚠️ Hay ejemplares retirados en esta carrera. Puede cambiar el ejemplar seleccionado:</p>", unsafe_allow_html=True)

                cab_leg = st.selectbox(
                    f"Selecciona el Ejemplar para {carr_leg}", 
                    options=caballos_in_carr if caballos_in_carr else ["Sin Caballos Disponibles"], 
                    key=f"ticket_cab_{sub_dup_actual}_{paso}"
                )
                
                if sub_dup_actual == "Polla Hipica" and cab_leg in retirados_carr_t:
                    idx_ret = todos_caballos_carr.index(cab_leg)
                    siguiente_cab = None
                    for siguiente_c in todos_caballos_carr[idx_ret + 1:] + todos_caballos_carr[:idx_ret]:
                        if siguiente_c not in retirados_carr_t:
                            siguiente_cab = siguiente_c
                            break
                    if siguiente_cab:
                        cab_leg = f"{siguiente_cab} (Sustituto por retiro)"
                        st.info(f"🔄 **Polla Hípica:** El ejemplar seleccionado estaba retirado. Se asignó automáticamente el siguiente disponible: **{cab_leg}**")

                if carr_leg in carreras_usadas:
                    valido_legs = False
                carreras_usadas.add(carr_leg)
                seleccion_legs.append({"carrera": carr_leg, "ejemplar": cab_leg})
                st.markdown("---")

            if not st.session_state.dupleta_bloqueada:
                if st.button(f"🚀 Emitir Ticket de {sub_dup_actual}", key=f"btn_emitir_{sub_dup_actual}", use_container_width=True, type="primary"):
                    if not valido_legs:
                        st.error("⚠️ No puedes repetir la misma carrera en el mismo ticket.")
                    else:
                        legs_ordenadas = sorted(seleccion_legs, key=lambda x: x['carrera'])
                        firma_combinacion = tuple((l['carrera'], l['ejemplar']) for l in legs_ordenadas)

                        lista_tickets_activo = (
                            st.session_state.dupletas_tickets if sub_dup_actual == "Dupleta" else
                            st.session_state.tripleta_tickets if sub_dup_actual == "Tripleta" else
                            st.session_state.polla_tickets
                        )

                        duplicado = False
                        for t in lista_tickets_activo:
                            t_legs_ordenadas = sorted(t['legs'], key=lambda x: x['carrera'])
                            t_firma = tuple((l['carrera'], l['ejemplar']) for l in t_legs_ordenadas)
                            if t_firma == firma_combinacion:
                                duplicado = True
                                break

                        if duplicado:
                            st.error("❌ **BLOQUEADO:** Ya existe un ticket con esta misma combinación.")
                        else:
                            prefijo_id = "DUP" if sub_dup_actual == "Dupleta" else ("TRIP" if sub_dup_actual == "Tripleta" else "POLL")
                            ticket_id = f"{prefijo_id}-{len(lista_tickets_activo) + 1:04d}"
                            
                            nuevo_ticket_dict = {
                                "id": ticket_id, "jugador": st.session_state.usuario_activo, "monto": monto_unico_seccion,
                                "legs": seleccion_legs, "estado": "Pendiente", "fecha": ahora_dt.strftime('%d/%m %I:%M %p')
                            }

                            if sub_dup_actual == "Dupleta":
                                st.session_state.dupletas_tickets.append(nuevo_ticket_dict)
                            elif sub_dup_actual == "Tripleta":
                                st.session_state.tripleta_tickets.append(nuevo_ticket_dict)
                            else:
                                st.session_state.polla_tickets.append(nuevo_ticket_dict)

                            detalles_str = " ➔ ".join([f"{l['carrera']}: {l['ejemplar']}" for l in seleccion_legs])
                            st.session_state.historial_jugadas.append({
                                "fecha": ahora_dt.strftime('%d/%m/%Y %I:%M:%S %p'),
                                "jugador": st.session_state.usuario_activo,
                                "tipo": sub_dup_actual,
                                "carrera": "Múltiple",
                                "detalle": f"Ticket {ticket_id} ({detalles_str})",
                                "monto": monto_unico_seccion
                            })
                            if st.session_state.usuario_activo not in st.session_state.cuentas:
                                st.session_state.cuentas[st.session_state.usuario_activo] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                            st.session_state.cuentas[st.session_state.usuario_activo]['Pujas'] += monto_unico_seccion
                            
                            guardar_estado_global()
                            st.success(f"✅ ¡Ticket {ticket_id} emitido con éxito (Estado: PENDIENTE)!")
                            st.rerun()

    st.markdown("---")
    st.markdown(f"### 📋 Historial de Tickets ({sub_dup_actual})")
    lista_tickets_activo_ver = (
        st.session_state.dupletas_tickets if sub_dup_actual == "Dupleta" else
        st.session_state.tripleta_tickets if sub_dup_actual == "Tripleta" else
        st.session_state.polla_tickets
    )
    if not lista_tickets_activo_ver:
        st.info("No hay tickets emitidos todavía en esta sección.")
    else:
        for idx_t, t in enumerate(reversed(lista_tickets_activo_ver)):
            with st.container(border=True):
                col_t1, col_t2, col_t3, col_t4 = st.columns([2, 2, 2, 2])
                col_t1.markdown(f"🏷️ `{t['id']}`")
                col_t2.markdown(f"👤 `{t['jugador']}`")
                col_t3.markdown(f"💰 `{formatear_bs(t['monto'])}`")
                col_t4.markdown(f"📌 **Estado:** `{t.get('estado', 'Pendiente')}`")
                
                detalles_legs = " ➔ ".join([f"**{l['carrera']}**: {l['ejemplar']}" for l in t['legs']])
                st.markdown(f"> {detalles_legs}")
                st.caption(f"Emitido: {t['fecha']}")

                if sub_dup_actual != "Polla Hipica":
                    retirado_en_ticket = False
                    carrera_afectada = None
                    for leg in t['legs']:
                        carr_l = leg['carrera']
                        ej_l = leg['ejemplar'].split(" (")[0]
                        retirados_carr = st.session_state.ejemplares_retirados.get(carr_l, [])
                        if ej_l in retirados_carr:
                            retirado_en_ticket = True
                            carrera_afectada = carr_l
                            break

                    if retirado_en_ticket:
                        if t.get('estado') == 'Pendiente':
                            t['estado'] = 'Nulo (Retirado)'
                            jug_t = t['jugador']
                            monto_t = t['monto']
                            if jug_t in st.session_state.cuentas:
                                st.session_state.cuentas[jug_t]['Pujas'] = max(0.0, st.session_state.cuentas[jug_t]['Pujas'] - monto_t)
                            st.session_state.historial_jugadas.append({
                                "fecha": ahora_dt.strftime('%d/%m/%Y %I:%M:%S %p'),
                                "jugador": jug_t,
                                "tipo": "Ticket Anulado (Retiro)",
                                "carrera": carrera_afectada,
                                "detalle": f"Ticket {t['id']} anulado por retiro",
                                "monto": -monto_t
                            })
                            guardar_estado_global()

                        st.error(f"❌ El ticket **{t['id']}** está **NULO** y su monto ha sido restado porque el ejemplar de la **{carrera_afectada}** fue retirado. Seleccione un nuevo ejemplar para reactivarlo:")
                        
                        with st.form(key=f"form_modificar_ticket_{t['id']}_{idx_t}"):
                            nuevas_legs = []
                            for i_l, leg in enumerate(t['legs']):
                                carr_l = leg['carrera']
                                ej_actual = leg['ejemplar'].split(" (")[0]
                                
                                if carr_l == carrera_afectada:
                                    ret_carr = st.session_state.ejemplares_retirados.get(carr_l, [])
                                    disponibles_l = [c for c in list(st.session_state.remates.get(carr_l, {}).keys()) if c not in ret_carr]
                                    
                                    idx_def = 0
                                    if ej_actual in disponibles_l:
                                        idx_def = disponibles_l.index(ej_actual)

                                    nuevo_ej = st.selectbox(
                                        f"Elija nuevo ejemplar para {carr_l} (Retirado: {ej_actual})",
                                        options=disponibles_l if disponibles_l else [ej_actual],
                                        index=idx_def,
                                        key=f"mod_ticket_{t['id']}_carr_{carr_l}"
                                    )
                                    nuevas_legs.append({"carrera": carr_l, "ejemplar": f"{nuevo_ej} (Cambiado por retiro)"})
                                else:
                                    nuevas_legs.append(leg)

                            if st.form_submit_button("🔄 Reactivar y Asignar Nuevo Ejemplar", use_container_width=True):
                                t['legs'] = nuevas_legs
                                t['estado'] = 'Pendiente'
                                jug_t = t['jugador']
                                monto_t = t['monto']
                                
                                if jug_t not in st.session_state.cuentas:
                                    st.session_state.cuentas[jug_t] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                                st.session_state.cuentas[jug_t]['Pujas'] += monto_t
                                
                                st.session_state.historial_jugadas.append({
                                    "fecha": ahora_dt.strftime('%d/%m/%Y %I:%M:%S %p'),
                                    "jugador": jug_t,
                                    "tipo": sub_dup_actual,
                                    "carrera": "Múltiple Reactivada",
                                    "detalle": f"Ticket {t['id']} reactivado tras cambio",
                                    "monto": monto_t
                                })

                                guardar_estado_global()
                                st.success(f"✅ ¡Ticket {t['id']} reactivado con éxito!")
                                st.rerun()

# =========================================================================
# 3. MÓDULO DE CUENTAS
# =========================================================================
elif menu_principal_opcion == "Cuentas":
    st.markdown("<div class='subasta-header'>📊 Mis Cuentas y Historial de Jugador en Formato Ticket</div>", unsafe_allow_html=True)
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

    st.markdown("---")
    st.markdown(f"### 🎟️ Historial de Tickets y Asignaciones de `{jugador_actual}`")

    st.markdown("#### 🐎 Tickets de Remates (Última puja ganada por carrera)")
    
    remates_ganados_por_carrera = {}
    for carr_k, remates_carr in st.session_state.remates.items():
        for ej_k, info_rem in remates_carr.items():
            if info_rem['jugador'] == jugador_actual and info_rem['monto'] > 0:
                retirados_c = st.session_state.ejemplares_retirados.get(carr_k, [])
                if ej_k not in retirados_c:
                    remates_ganados_por_carrera[carr_k] = {
                        "ejemplar": ej_k,
                        "monto": info_rem['monto']
                    }

    if remates_ganados_por_carrera:
        for carr_k, info_r in remates_ganados_por_carrera.items():
            detalles_c = st.session_state.detalles_carreras.get(carr_k, {})
            hora_cierre_real = detalles_c.get('hora_cierre_real', 'No cerrado todavía')
            
            fecha_puja = "Jornada actual"
            for h in reversed(st.session_state.historial_jugadas):
                if h.get('carrera') == carr_k and h.get('jugador') == jugador_actual and h.get('detalle') == info_r['ejemplar']:
                    fecha_puja = h.get('fecha', '')
                    break

            ticket_html = f"""
                <div class="ticket-jugador-card">
                    <div class="ticket-header-row">
                        <span>🏷️ TICKET REMATE (GANADOR)</span>
                        <span>📅 {fecha_puja}</span>
                    </div>
                    <div class="ticket-body-row">🏁 <b>Carrera:</b> {carr_k}</div>
                    <div class="ticket-body-row">🐎 <b>Último Ejemplar Asignado:</b> {info_r['ejemplar']}</div>
                    <div class="ticket-body-row">🔒 <b>Hora de Cierre Carrera:</b> {hora_cierre_real}</div>
                    <div class="ticket-body-row" style="color: #f1c40f; margin-top: 6px;">💰 <b>Monto Ganador:</b> {formatear_bs(info_r['monto'])}</div>
                </div>
            """
            st.markdown(ticket_html, unsafe_allow_html=True)
    else:
        st.info("ℹ️ No tienes remates ganados activos registrados en esta jornada.")

    st.markdown("---")

    tickets_usuario_dupletas = [t for t in st.session_state.dupletas_tickets if t['jugador'] == jugador_actual]
    tickets_usuario_tripletas = [t for t in st.session_state.tripleta_tickets if t['jugador'] == jugador_actual]
    tickets_usuario_pollas = [t for t in st.session_state.polla_tickets if t['jugador'] == jugador_actual]

    todos_tickets_multiples = tickets_usuario_dupletas + tickets_usuario_tripletas + tickets_usuario_pollas

    if todos_tickets_multiples:
        st.markdown("#### 🎟️ Tickets de Dupletas, Tripletas y Polla Hípica")
        for t in reversed(todos_tickets_multiples):
            detalles_legs = " ➔ ".join([f"**{l['carrera']}**: {l['ejemplar']}" for l in t['legs']])
            estado_t = t.get('estado', 'Pendiente')
            color_est = "#2ed573" if estado_t == 'Pendiente' else "#ff4757"

            ticket_m_html = f"""
                <div class="ticket-jugador-card" style="border-color: {color_est};">
                    <div class="ticket-header-row">
                        <span>🏷️ {t['id']}</span>
                        <span style="color: {color_est};">📌 {estado_t}</span>
                    </div>
                    <div class="ticket-body-row">🛤️ <b>Selecciones:</b> {detalles_legs}</div>
                    <div class="ticket-body-row" style="color: #f1c40f; margin-top: 6px;">💰 <b>Monto Ticket:</b> {formatear_bs(t['monto'])}</div>
                    <div style="font-size: 10px; color: #8b949e; text-align: right; margin-top: 4px;">Emitido: {t['fecha']}</div>
                </div>
            """
            st.markdown(ticket_m_html, unsafe_allow_html=True)
    else:
        st.info("ℹ️ No hay tickets de dupletas, tripletas o pollas registrados para este usuario.")

# =========================================================================
# 4. ZONA DE ADMINISTRADOR (CONFIGURACIÓN)
# =========================================================================
elif menu_principal_opcion == "🔒 Zona Admin":
    st.markdown("<div class='subasta-header'>🔒 Panel de Configuración y Administración</div>", unsafe_allow_html=True)
    
    opciones_admin_tabs = ["✍️ Caballos", "👥 Usuarios", "⚙️ Dupletas/Polla", "📺 Video", "📊 Saldos", "🖼️ Imágenes", "📄 Importar"]
    
    st.markdown('<div class="carrusel-horizontal-box">', unsafe_allow_html=True)
    cols_adm_tabs = st.columns(len(opciones_admin_tabs), gap="small")
    for idx, tab_nombre in enumerate(opciones_admin_tabs):
        with cols_adm_tabs[idx]:
            es_tab_activa = (st.session_state.admin_tab_seleccionada == tab_nombre)
            if st.button(tab_nombre, key=f"adm_tab_btn_{idx}", use_container_width=True, type="primary" if es_tab_activa else "secondary"):
                st.session_state.admin_tab_seleccionada = tab_nombre
                guardar_estado_global()
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<hr style='margin: 0.5rem 0; border-color: #30363d;'>", unsafe_allow_html=True)
    tab_actual = st.session_state.admin_tab_seleccionada

    if tab_actual == "✍️ Caballos":
        st.markdown("### ✍️ Banco de Caballos y Carreras Activas")
        with st.container(border=True):
            st.markdown("📅 **Configuración General de la Semana**")
            nueva_cantidad_carreras = st.number_input(
                "¿Cuántas carreras van a correr esta semana?", 
                min_value=1, max_value=25, 
                value=int(st.session_state.total_carreras_semana), 
                step=1, key="input_total_carreras_semana"
            )
            if st.button("💾 Actualizar Carreras", key="btn_actualizar_cant_carreras", use_container_width=True, type="primary"):
                st.session_state.total_carreras_semana = nueva_cantidad_carreras
                for i in range(1, nueva_cantidad_carreras + 1):
                    c_n = f"Carrera {i}"
                    if c_n not in st.session_state.banco_caballos_por_carrera:
                        st.session_state.banco_caballos_por_carrera[c_n] = [f"{j} - Ejemplar {j}" for j in range(1, 11)]
                        st.session_state.remates[c_n] = {f"{j} - Ejemplar {j}": {"jugador": "Sin Postor", "monto": 0.0} for j in range(1, 11)}
                        st.session_state.detalles_carreras[c_n] = {
                            "condicion": "Condición estándar", 
                            "distancia": "1200 mts", 
                            "hora": "02:00 PM", 
                            "monto_fijo_ciego": 500.0, 
                            "incentivo_adelantados": 0.0,
                            "incentivo_ciegos": 0.0,
                            "incentivo_envivo": 0.0,
                            "hora_cierre_real": "No registrada"
                        }
                guardar_estado_global()
                st.toast(f"✅ ¡Jornada ajustada a {nueva_cantidad_carreras} carreras!")
                st.rerun()

        st.markdown("---")
        with st.container(border=True):
            st.markdown("⚡ **Panel Didáctico: Carreras Activas para Remate**")
            carreras_disponibles_todas = list(st.session_state.remates.keys())
            if not carreras_disponibles_todas:
                st.warning("⚠️ No hay carreras en el banco.")
            else:
                carreras_activas_actuales = st.session_state.carreras_activas_remate
                cols_grid = st.columns(min(4, len(carreras_disponibles_todas)), gap="small")
                nuevas_activas = []
                for i, carr_n in enumerate(carreras_disponibles_todas):
                    col_idx = i % len(cols_grid)
                    with cols_grid[col_idx]:
                        estado_marcado = st.checkbox(
                            f"🏁 {carr_n}", 
                            value=(carr_n in carreras_activas_actuales),
                            key=f"chk_didactico_activa_{carr_n}"
                        )
                        if estado_marcado:
                            nuevas_activas.append(carr_n)
                if st.button("💾 Guardar Carreras Activas", key="btn_save_activas_didactico", use_container_width=True, type="primary"):
                    st.session_state.carreras_activas_remate = nuevas_activas
                    guardar_estado_global()
                    st.toast("✅ ¡Actualizado con éxito!")
                    st.rerun()

        st.markdown("---")
        with st.container(border=True):
            st.markdown("🙈 **Selección de las 2 Carreras para Remate Ciego (1V y 6V)**")
            carreras_existentes = list(st.session_state.remates.keys())
            carreras_ciego_actuales = st.session_state.carreras_por_modalidad.get("Ciegos", [])
            default_ciego = [c for c in carreras_ciego_actuales if c in carreras_existentes][:2]

            carreras_ciego_seleccionadas = st.multiselect(
                "Elige exactamente 2 carreras:",
                options=carreras_existentes,
                default=default_ciego,
                key="multiselect_carreras_ciego"
            )
            if st.button("💾 Guardar Ciegos", key="btn_save_carr_ciego", use_container_width=True, type="primary"):
                if len(carreras_ciego_seleccionadas) != 2:
                    st.error("⚠️ Debes seleccionar exactamente 2 carreras.")
                else:
                    st.session_state.carreras_por_modalidad["Ciegos"] = carreras_ciego_seleccionadas
                    guardar_estado_global()
                    st.toast("✅ ¡Guardado!")
                    st.rerun()

        st.markdown("---")
        carr_banco_sel = st.selectbox("Seleccionar Carrera para Editar", lista_carreras_disponibles, key="adm_banco_sel_carrera")
        
        if carr_banco_sel not in st.session_state.banco_caballos_por_carrera:
            st.session_state.banco_caballos_por_carrera[carr_banco_sel] = []
        if carr_banco_sel not in st.session_state.detalles_carreras:
            st.session_state.detalles_carreras[carr_banco_sel] = {
                "condicion": "Condición general", 
                "distancia": "1200 mts", 
                "hora": "02:00 PM", 
                "monto_fijo_ciego": 500.0, 
                "incentivo_adelantados": 0.0,
                "incentivo_ciegos": 0.0,
                "incentivo_envivo": 0.0,
                "hora_cierre_real": "No registrada"
            }

        det_actuales = st.session_state.detalles_carreras[carr_banco_sel]
        with st.container(border=True):
            st.markdown(f"🛠️ **Detalles e Incentivos por Modalidad ({carr_banco_sel})**")
            edit_cond = st.text_input("Condición", value=det_actuales.get('condicion', ''), key=f"banco_cond_{carr_banco_sel}")
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                edit_dist = st.text_input("Distancia", value=det_actuales.get('distancia', ''), key=f"banco_dist_{carr_banco_sel}")
            with col_b2:
                edit_hora = st.text_input("Hora", value=det_actuales.get('hora', ''), key=f"banco_hora_{carr_banco_sel}")
            with col_b3:
                edit_monto_ciego = st.number_input("Monto Fijo Ciego", min_value=0.0, value=float(det_actuales.get('monto_fijo_ciego', 500.0)), step=50.0, key=f"banco_monto_ciego_{carr_banco_sel}")

            st.markdown("🎁 **Incentivos Separados por Modalidad:**")
            col_inc1, col_inc2, col_inc3 = st.columns(3)
            with col_inc1:
                edit_inc_adel = st.number_input("Incentivo Adelantados", min_value=0.0, value=float(det_actuales.get('incentivo_adelantados', 0.0)), step=50.0, key=f"banco_inc_adel_{carr_banco_sel}")
            with col_inc2:
                edit_inc_ciegos = st.number_input("Incentivo Ciegos", min_value=0.0, value=float(det_actuales.get('incentivo_ciegos', 0.0)), step=50.0, key=f"banco_inc_ciegos_{carr_banco_sel}")
            with col_inc3:
                edit_inc_envivo = st.number_input("Incentivo En Vivo", min_value=0.0, value=float(det_actuales.get('incentivo_envivo', 0.0)), step=50.0, key=f"banco_inc_envivo_{carr_banco_sel}")
            
            if st.button("💾 Guardar Detalles e Incentivos", key=f"btn_save_banco_det_{carr_banco_sel}", use_container_width=True, type="primary"):
                st.session_state.detalles_carreras[carr_banco_sel] = {
                    "condicion": edit_cond, 
                    "distancia": edit_dist, 
                    "hora": edit_hora, 
                    "monto_fijo_ciego": edit_monto_ciego,
                    "incentivo_adelantados": edit_inc_adel,
                    "incentivo_ciegos": edit_inc_ciegos,
                    "incentivo_envivo": edit_inc_envivo,
                    "hora_cierre_real": det_actuales.get("hora_cierre_real", "No registrada")
                }
                guardar_estado_global()
                st.toast("✅ ¡Detalles e incentivos guardados!")
                st.rerun()

        st.markdown("---")
        st.markdown("#### 🐎 Ejemplares Inscritos")
        with st.container(border=True):
            nuevo_nom_banco = st.text_input("Nombre del Ejemplar", placeholder="Ej: Rey David", key=f"adm_banco_input_{carr_banco_sel}")
            if st.button("💾 Agregar", key=f"adm_banco_btn_add_{carr_banco_sel}", use_container_width=True, type="primary"):
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
                    guardar_estado_global()
                    st.toast("✅ ¡Agregado!")
                    st.rerun()

        for idx_b, ej_item in enumerate(st.session_state.banco_caballos_por_carrera[carr_banco_sel]):
            col_ib1, col_ib2 = st.columns([5, 1])
            with col_ib1: st.text(ej_item)
            with col_ib2:
                if st.button("🗑️", key=f"adm_banco_del_{carr_banco_sel}_{idx_b}", use_container_width=True):
                    st.session_state.banco_caballos_por_carrera[carr_banco_sel].pop(idx_b)
                    if carr_banco_sel in st.session_state.remates and ej_item in st.session_state.remates[carr_banco_sel]:
                        del st.session_state.remates[carr_banco_sel][ej_item]
                    guardar_estado_global()
                    st.rerun()

    elif tab_actual == "👥 Usuarios":
        st.markdown("### 👥 Registro de Usuarios")
        with st.container(border=True):
            nuevo_usuario_input = st.text_input("Nuevo Usuario", placeholder="Ej: JUAN", key="input_nuevo_usuario_reg")
            if st.button("➕ Registrar", key="btn_registrar_nuevo_usuario", use_container_width=True, type="primary"):
                usuario_limpio = nuevo_usuario_input.strip().upper()
                if not usuario_limpio:
                    st.warning("⚠️ Escribe un nombre válido.")
                elif usuario_limpio in st.session_state.lista_usuarios:
                    st.error("❌ Ya existe.")
                else:
                    st.session_state.lista_usuarios.append(usuario_limpio)
                    if usuario_limpio not in st.session_state.cuentas:
                        st.session_state.cuentas[usuario_limpio] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                    guardar_estado_global()
                    st.toast(f"✅ ¡Registrado **{usuario_limpio}**!")
                    st.rerun()

        st.markdown("---")
        for u in st.session_state.lista_usuarios:
            col_u1, col_u2 = st.columns([4, 1])
            with col_u1: st.markdown(f"👤 **{u}**")
            with col_u2:
                if u != "CASA":
                    if st.button("🗑️", key=f"btn_del_usu_{u}", use_container_width=True):
                        st.session_state.lista_usuarios.remove(u)
                        if u in st.session_state.cuentas:
                            del st.session_state.cuentas[u]
                        if st.session_state.usuario_activo == u:
                            st.session_state.usuario_activo = "CASA"
                        guardar_estado_global()
                        st.rerun()

    elif tab_actual == "⚙️ Dupletas/Polla":
        st.markdown("### ⚙️ Configuración de Montos y Carreras")
        with st.container(border=True):
            st.markdown("💰 **Montos Únicos**")
            monto_dup_cfg = st.number_input("Dupleta (Bs.)", min_value=0.0, value=float(st.session_state.config_montos_especiales.get("Dupleta", 500.0)), step=50.0, key="cfg_monto_dupleta")
            monto_trip_cfg = st.number_input("Tripleta (Bs.)", min_value=0.0, value=float(st.session_state.config_montos_especiales.get("Tripleta", 500.0)), step=50.0, key="cfg_monto_tripleta")
            monto_polla_cfg = st.number_input("Polla (Bs.)", min_value=0.0, value=float(st.session_state.config_montos_especiales.get("Polla Hipica", 1000.0)), step=50.0, key="cfg_monto_polla")
            
            if st.button("💾 Guardar Montos", key="btn_save_montos_cfg", use_container_width=True, type="primary"):
                st.session_state.config_montos_especiales["Dupleta"] = monto_dup_cfg
                st.session_state.config_montos_especiales["Tripleta"] = monto_trip_cfg
                st.session_state.config_montos_especiales["Polla Hipica"] = monto_polla_cfg
                guardar_estado_global()
                st.toast("✅ ¡Guardado!")
                st.rerun()

        st.markdown("---")
        with st.container(border=True):
            st.markdown("🏇 **Carreras Habilitadas**")
            carr_disp_all = list(st.session_state.remates.keys())
            
            def_dup = [c for c in st.session_state.carreras_habilitadas_dupleta if c in carr_disp_all]
            def_trip = [c for c in st.session_state.carreras_habilitadas_tripleta if c in carr_disp_all]
            def_polla = [c for c in st.session_state.carreras_habilitadas_polla if c in carr_disp_all]

            sel_dup_hab = st.multiselect("Dupleta", options=carr_disp_all, default=def_dup, key="multiselect_hab_dup")
            sel_trip_hab = st.multiselect("Tripleta", options=carr_disp_all, default=def_trip, key="multiselect_hab_trip")
            sel_polla_hab = st.multiselect("Polla", options=carr_disp_all, default=def_polla, key="multiselect_hab_polla")

            if st.button("💾 Guardar Habilitadas", key="btn_save_carr_hab", use_container_width=True, type="primary"):
                st.session_state.carreras_habilitadas_dupleta = sel_dup_hab
                st.session_state.carreras_habilitadas_tripleta = sel_trip_hab
                st.session_state.carreras_habilitadas_polla = sel_polla_hab
                guardar_estado_global()
                st.toast("✅ ¡Guardado!")
                st.rerun()

    elif tab_actual == "📺 Video":
        st.markdown("### 📺 Video en Vivo")
        with st.container(border=True):
            nueva_url_video = st.text_input("URL", value=st.session_state.get('url_video_en_vivo', ''), placeholder="https://youtube.com/watch?v=...", key="input_live_video_url")
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                if st.button("💾 Guardar", key="btn_save_video_url", use_container_width=True, type="primary"):
                    st.session_state.url_video_en_vivo = nueva_url_video.strip()
                    guardar_estado_global()
                    st.toast("✅ ¡Guardado!")
                    st.rerun()
            with col_v2:
                if st.button("🗑️ Desactivar", key="btn_clear_video_url", use_container_width=True):
                    st.session_state.url_video_en_vivo = ""
                    guardar_estado_global()
                    st.toast("🗑️ Desactivado.")
                    st.rerun()

    elif tab_actual == "📊 Saldos":
        st.markdown("### 📊 Saldos de Usuarios")
        usuarios_futuros = [u for u in st.session_state.lista_usuarios if u != "CASA"]
        if not usuarios_futuros:
            st.info("ℹ️ No hay usuarios registrados.")
        else:
            datos_cuentas_adm = []
            for jugador in usuarios_futuros:
                if jugador not in st.session_state.cuentas:
                    st.session_state.cuentas[jugador] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                vals = st.session_state.cuentas[jugador]
                pujas, premios, abonos = vals['Pujas'], vals['Premios'], vals['Abonos']
                balance_neto = pujas - abonos - premios
                datos_cuentas_adm.append({"Usuario": jugador, "Compras": formatear_bs(pujas), "Premios": formatear_bs(premios), "Pagos": formatear_bs(abonos), "Neto": formatear_bs(balance_neto)})
            st.dataframe(pd.DataFrame(datos_cuentas_adm), use_container_width=True, hide_index=True)

        st.metric("Ganancia Casa", formatear_bs(st.session_state.ganancia_casa))
        st.markdown("---")
        
        # --- BLOQUE DE ABONOS Y RETIROS ---
        col_op1, col_op2 = st.columns(2, gap="small")
        
        with col_op1:
            with st.container(border=True):
                st.markdown("#### 💵 Registrar Abono (Pago)")
                jugador_abonar = st.selectbox("Usuario", st.session_state.lista_usuarios, key="adm_abono_jugador")
                monto_abono = st.number_input("Monto Abono (Bs.)", min_value=0.0, step=100.0, key="adm_abono_monto")
                if st.button("➕ Aplicar Abono", key="adm_btn_aplicar_abono", use_container_width=True, type="primary"):
                    if jugador_abonar not in st.session_state.cuentas:
                        st.session_state.cuentas[jugador_abonar] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                    st.session_state.cuentas[jugador_abonar]['Abonos'] += monto_abono
                    guardar_estado_global()
                    st.toast(f"✅ Abono registrado a {jugador_abonar}")
                    st.rerun()

        with col_op2:
            with st.container(border=True):
                st.markdown("#### 💸 Registrar Retiro")
                jugador_retirar = st.selectbox("Usuario", st.session_state.lista_usuarios, key="adm_retiro_jugador")
                monto_retiro = st.number_input("Monto Retiro (Bs.)", min_value=0.0, step=100.0, key="adm_retiro_monto")
                if st.button("➖ Aplicar Retiro", key="adm_btn_aplicar_retiro", use_container_width=True, type="primary"):
                    if jugador_retirar not in st.session_state.cuentas:
                        st.session_state.cuentas[jugador_retirar] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                    
                    st.session_state.cuentas[jugador_retirar]['Pujas'] = max(0.0, st.session_state.cuentas[jugador_retirar]['Pujas'] - monto_retiro)
                    st.session_state.cuentas[jugador_retirar]['Premios'] = max(0.0, st.session_state.cuentas[jugador_retirar]['Premios'] - monto_retiro)
                    
                    st.session_state.historial_jugadas.append({
                        "fecha": ahora_dt.strftime('%d/%m/%Y %I:%M:%S %p'),
                        "jugador": jugador_retirar,
                        "tipo": "Retiro",
                        "carrera": "General",
                        "detalle": f"Retiro de fondos aplicado",
                        "monto": monto_retiro
                    })
                    
                    guardar_estado_global()
                    st.toast(f"✅ Retiro de {formatear_bs(monto_retiro)} deducido a {jugador_retirar}")
                    st.rerun()

    elif tab_actual == "🖼️ Imágenes":
        st.markdown("### 🖼️ Imágenes y Gacetas por Carrera")
        carr_img_sel = st.selectbox("Seleccionar Carrera", lista_carreras_disponibles, key="adm_img_sel_carr")
        with st.container(border=True):
            st.markdown("📸 **Imagen de la Carrera**")
            imagen_subida = st.file_uploader("Subir imagen (PNG, JPG)", type=["png", "jpg", "jpeg"], key=f"file_img_{carr_img_sel}")
            if imagen_subida is not None:
                if st.button("💾 Guardar Imagen", key=f"btn_save_img_{carr_img_sel}", use_container_width=True, type="primary"):
                    st.session_state.imagenes_carreras[carr_img_sel] = imagen_subida
                    guardar_estado_global()
                    st.toast("✅ ¡Imagen guardada!")
                    st.rerun()
            if carr_img_sel in st.session_state.imagenes_carreras:
                try:
                    st.image(st.session_state.imagenes_carreras[carr_img_sel], width=250)
                except Exception:
                    pass
                if st.button("🗑️ Eliminar Imagen", key=f"btn_del_img_{carr_img_sel}", use_container_width=True):
                    del st.session_state.imagenes_carreras[carr_img_sel]
                    guardar_estado_global()
                    st.toast("🗑️ Imagen removida")
                    st.rerun()

        st.markdown("---")
        with st.container(border=True):
            st.markdown("📰 **Archivo Gaceta (PDF)**")
            gaceta_subida = st.file_uploader("Subir PDF de la Gaceta", type=["pdf"], key=f"file_gaceta_{carr_img_sel}")
            if gaceta_subida is not None:
                if st.button("💾 Guardar Gaceta", key=f"btn_save_gaceta_{carr_img_sel}", use_container_width=True, type="primary"):
                    st.session_state.gacetas_carreras[carr_img_sel] = gaceta_subida.read()
                    guardar_estado_global()
                    st.toast("✅ ¡Gaceta guardada!")
                    st.rerun()
            if carr_img_sel in st.session_state.gacetas_carreras:
                st.success("✅ Gaceta disponible para descarga en esta carrera.")
                if st.button("🗑️ Eliminar Gaceta", key=f"btn_del_gaceta_{carr_img_sel}", use_container_width=True):
                    del st.session_state.gacetas_carreras[carr_img_sel]
                    guardar_estado_global()
                    st.toast("🗑️ Gaceta removida")
                    st.rerun()

    elif tab_actual == "📄 Importar":
        st.markdown("### 📄 Importar Contenido")
        texto_copiado_web = st.text_area(
            "Pegar texto:", value="", height=200, key="text_area_web_copiado",
            placeholder="Primera Carrera - 1.200 mts - 02:00 PM\n1 - Rey David\n2 - Gran Amigo"
        )
        if st.button("🚀 Procesar Contenido", key="btn_procesar_texto_pegado", use_container_width=True, type="primary"):
            if texto_copiado_web.strip():
                if procesar_texto_flexible(texto_copiado_web):
                    guardar_estado_global()
                    st.success("✅ ¡Procesado con éxito!")
                    st.rerun()
                else:
                    st.warning("⚠️ Asegúrate de incluir el nombre de la carrera y los ejemplares numerados.")
            else:
                st.warning("⚠️ El campo está vacío.")

# =========================================================================
# TRANSMISIÓN EN VIVO
# =========================================================================
url_live_video = st.session_state.get('url_video_en_vivo', '').strip()

if url_live_video:
    st.markdown("<br><hr style='border-color: #30363d;'>", unsafe_allow_html=True)
    st.markdown("### 📺 TRANSMISIÓN EN VIVO")
    yt_match = re.search(r'(?:v=|\/embed\/|youtu\.be\/|\/v\/|\/e\/|watch\?v=|&v=)([^#&?]{11})', url_live_video)
    if yt_match:
        yt_id = yt_match.group(1)
        embed_url = f"https://www.youtube.com/embed/{yt_id}?playsinline=1"
        try:
            st.video(embed_url)
        except Exception:
            st.video(url_live_video)
    else:
        try:
            st.video(url_live_video)
        except Exception:
            st.video(url_live_video)
