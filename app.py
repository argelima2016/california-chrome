import streamlit as st
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

def cargar_estado_global(forzar_recarga=False):
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
        'fechas_horas_inicio_remate': {},
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
                    if k not in st.session_state or forzar_recarga:
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
        'total_carreras_semana', 'url_video_en_vivo', 'imagenes_carreras', 'gacetas_carreras',
        'fechas_horas_inicio_remate', 'fechas_horas_cierre_remate'
    ]
    data = {}
    for k in keys_to_save:
        if k in st.session_state:
            val = st.session_state[k]
            if k in ['fechas_horas_inicio_remate', 'fechas_horas_cierre_remate']:
                data[k] = {c_k: c_v.isoformat() if isinstance(c_v, datetime) else c_v for c_k, c_v in val.items()}
            else:
                data[k] = val
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

cargar_estado_global()

# Restaurar objetos datetime desde strings almacenados
for dict_key in ['fechas_horas_inicio_remate', 'fechas_horas_cierre_remate']:
    if dict_key in st.session_state:
        for c_k, c_v in list(st.session_state[dict_key].items()):
            if isinstance(c_v, str):
                try:
                    st.session_state[dict_key][c_k] = datetime.fromisoformat(c_v)
                except Exception:
                    pass

# --- SCRIPT JS PARA CONTROL TOTAL Y BARRA LATERAL ---
st.components.v1.html("""
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
        setInterval(sincronizacionEnVivo, 800);
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

ahora_dt = obtener_hora_venezuela_local()
hora_texto = ahora_dt.strftime('%I:%M:%S %p')
fecha_texto = ahora_dt.strftime('%d/%m/%Y')

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    * { box-sizing: border-box !important; }
    .stApp { background-color: #080a0f; color: #f0f6fc; overflow-x: hidden !important; }
    [data-testid="stSidebar"] { min-width: 360px !important; max-width: 360px !important; }
    [data-testid="stSidebar"] > div:first-child { width: 360px !important; padding-left: 1.2rem !important; padding-right: 1.2rem !important; }
    [data-testid="stToolbar"], header[data-testid="stHeader"], footer, #MainMenu, div[data-testid="stTabs"] { display: none !important; visibility: hidden !important; }
    .block-container { padding-top: 0.4rem !important; padding-bottom: 2rem !important; padding-left: 0.5rem !important; padding-right: 0.5rem !important; max-width: 100% !important; margin: 0 auto !important; }
    div[data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; overflow-x: auto !important; width: 100% !important; gap: 6px !important; padding-bottom: 6px !important; scrollbar-width: thin; }
    div[data-testid="stHorizontalBlock"] > div { flex: 0 0 auto !important; width: auto !important; min-width: 110px !important; }
    .carreras-scroll-container div[data-testid="stHorizontalBlock"] > div { min-width: 55px !important; width: 55px !important; }
    div[data-testid="column"] button { border-radius: 20px !important; width: 100% !important; height: 38px !important; min-height: 38px !important; font-size: 11px !important; font-weight: 900 !important; }
    .subasta-header { font-size: clamp(14px, 3.5vw, 18px); font-weight: 800; color: #f1e05a; margin-bottom: 4px; border-bottom: 2px solid #f1e05a; padding-bottom: 3px; }
    .timer-box { background-color: #161b22; border: 1px solid #ff4757; padding: 6px; border-radius: 6px; text-align: center; font-size: 15px; font-weight: bold; color: #ff4757; margin-bottom: 8px; }
    .carrera-condicion-card { background-color: #161b22; border: 1px solid #30363d; padding: 8px 12px; border-radius: 6px; font-size: 12px; color: #f0f6fc; margin-bottom: 10px; line-height: 1.4; }
    .incentivo-llamativo { background: linear-gradient(135deg, #1f1c2c 0%, #923d41 100%); border: 2px dashed #00ffff; padding: 10px 16px; border-radius: 12px; text-align: center; margin: 10px 0; }
    .incentivo-llamativo-monto { color: #ffffff; font-size: 22px; font-weight: 900; }
    .ticket-jugador-card { background: #0d1117; border: 2px solid #30363d; border-radius: 10px; padding: 12px 16px; margin-bottom: 10px; }
    .ticket-header-row { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #30363d; padding-bottom: 6px; margin-bottom: 8px; font-size: 12px; font-weight: 800; color: #f1c40f; }
    .ticket-body-row { font-size: 13px; color: #f0f6fc; margin-bottom: 4px; font-weight: 600; }
    .header-container-modern { background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); border: 1px solid #30363d; border-radius: 12px; padding: 14px 18px; margin-bottom: 10px; display: flex; flex-direction: column; gap: 14px; width: 100%; }
    .header-top-row { display: flex; justify-content: space-between; align-items: center; width: 100%; gap: 8px; }
    .header-clock-box { display: flex; flex-direction: column; background: #080a0f; border: 1px solid #21262d; padding: 5px 10px; border-radius: 8px; }
    .h-time { color: #00ffff; font-size: 13px; font-weight: 900; }
    .h-date { color: #8b949e; font-size: 10px; font-weight: 700; }
    .header-user-card { display: flex; align-items: center; gap: 8px; background: #080a0f; border: 1px solid #30363d; padding: 5px 10px; border-radius: 8px; }
    .user-details { display: flex; flex-direction: column; text-align: right; }
    .u-name { color: #f0f6fc; font-size: 12px; font-weight: 800; }
    .u-bal { font-size: 10px; font-weight: 700; }
    .u-avatar-badge { width: 28px; height: 28px; background: #1f6feb; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; }
    .header-bottom-row-logo { text-align: center; border-top: 1px solid #21262d; padding-top: 12px; }
    .header-logo-img { max-height: 120px; width: auto; object-fit: contain; }
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

def obtener_abreviatura_carrera(nombre_carrera, modo_ciego=False):
    if modo_ciego:
        carreras_ciegas = st.session_state.carreras_por_modalidad.get("Ciegos", [])
        if len(carreras_ciegas) >= 2:
            if nombre_carrera == carreras_ciegas[0]: return "1V"
            elif nombre_carrera == carreras_ciegas[1]: return "6V"
    match = re.search(r'\d+', nombre_carrera)
    if match: return f"C{match.group(0)}"
    return nombre_carrera[:3].upper()

if not st.session_state.remates:
    for i in range(1, st.session_state.total_carreras_semana + 1):
        carr_nombre = f"Carrera {i}"
        st.session_state.banco_caballos_por_carrera[carr_nombre] = [f"{j} - Ejemplar {j}" for j in range(1, 11)]
        st.session_state.remates[carr_nombre] = {f"{j} - Ejemplar {j}": {"jugador": "Sin Postor", "monto": 0.0} for j in range(1, 11)}
        st.session_state.detalles_carreras[carr_nombre] = {
            "condicion": "Condición estándar", "distancia": "1200 mts", "hora": "02:00 PM", 
            "monto_fijo_ciego": 500.0, "incentivo_adelantados": 0.0, "incentivo_ciegos": 0.0, "incentivo_envivo": 0.0, "hora_cierre_real": "No registrada"
        }

lista_carreras_disponibles = list(st.session_state.remates.keys())

if not st.session_state.carreras_activas_remate and lista_carreras_disponibles:
    st.session_state.carreras_activas_remate = list(lista_carreras_disponibles)
else:
    for c_disp in lista_carreras_disponibles:
        if c_disp not in st.session_state.carreras_activas_remate:
            st.session_state.carreras_activas_remate.append(c_disp)

if not st.session_state.carreras_habilitadas_dupleta and lista_carreras_disponibles:
    st.session_state.carreras_habilitadas_dupleta = list(lista_carreras_disponibles)
if not st.session_state.carreras_habilitadas_tripleta and lista_carreras_disponibles:
    st.session_state.carreras_habilitadas_tripleta = list(lista_carreras_disponibles)
if not st.session_state.carreras_habilitadas_polla and lista_carreras_disponibles:
    st.session_state.carreras_habilitadas_polla = list(lista_carreras_disponibles)

for mod in ["Adelantados", "Ciegos", "En Vivo"]:
    if not st.session_state.carreras_por_modalidad.get(mod) and lista_carreras_disponibles:
        if mod == "Ciegos": st.session_state.carreras_por_modalidad[mod] = lista_carreras_disponibles[:2]
        else: st.session_state.carreras_por_modalidad[mod] = list(lista_carreras_disponibles)
    else:
        for c_disp in lista_carreras_disponibles:
            if c_disp not in st.session_state.carreras_por_modalidad[mod]:
                st.session_state.carreras_por_modalidad[mod].append(c_disp)

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

# --- BARRA LATERAL ---
st.sidebar.header("barra lateral")
st.sidebar.markdown(f"🕒 **Hora:** `{ahora_dt.strftime('%I:%M:%S %p')}`")

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
    if not c_cerrada_actual:
        if st.button("🔒 Cerrar Remate Manual", key=f"sb_liq_cerrar_{carr_seleccionada_liq}", use_container_width=True, type="primary"):
            st.session_state.carreras_cerradas_remate[carr_seleccionada_liq] = True
            st.session_state.estado_conteo_carrera[carr_seleccionada_liq] = "CERRADO"
            st.session_state.detalles_carreras[carr_seleccionada_liq]["hora_cierre_real"] = ahora_dt.strftime('%I:%M:%S %p')
            if not st.session_state.remates_cargados_en_cuentas.get(carr_seleccionada_liq, False):
                retirados_carr = st.session_state.ejemplares_retirados.get(carr_seleccionada_liq, [])
                for cab, info in st.session_state.remates[carr_seleccionada_liq].items():
                    if cab in retirados_carr: continue
                    if info['jugador'] != "Sin Postor" and info['monto'] > 0:
                        if info['jugador'] not in st.session_state.cuentas: st.session_state.cuentas[info['jugador']] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
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
        if key not in ['banco_caballos_por_carrera', 'lista_usuarios']: del st.session_state[key]
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    st.toast("🚨 Jornada reiniciada.")
    st.rerun()

menu_principal_opcion = st.session_state.menu_principal_opcion

# =========================================================================
# FUNCIONES DE MÓDULOS AISLADOS (CERO SOLAPAMIENTOS)
# =========================================================================

def render_remates():
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
    carreras_modalidad_permitidas = st.session_state.carreras_por_modalidad.get(modo_actual_remate, lista_carreras_disponibles)
    if modo_actual_remate == "Ciegos" and len(carreras_modalidad_permitidas) > 2:
        carreras_modalidad_permitidas = carreras_modalidad_permitidas[:2]
    
    carreras_filtradas_visibles = [c for c in lista_carreras_disponibles if c in carreras_modalidad_permitidas and ((c in st.session_state.carreras_activas_remate) or st.session_state.carreras_cerradas_remate.get(c, False))]
    
    if not carreras_filtradas_visibles:
        st.info(f"ℹ️ No hay carreras habilitadas para la modalidad **{modo_actual_remate}**.")
        return

    if "carrera_remate_activa_seleccionada" not in st.session_state or st.session_state["carrera_remate_activa_seleccionada"] not in carreras_filtradas_visibles:
        carr_activa = carreras_filtradas_visibles[0]
        st.session_state["carrera_remate_activa_seleccionada"] = carr_activa
    else:
        carr_activa = st.session_state["carrera_remate_activa_seleccionada"]

    st.markdown("🔹 **Seleccionar Carrera:**")
    cols_carreras = st.columns(len(carreras_filtradas_visibles), gap="small")
    for idx, c_nombre in enumerate(carreras_filtradas_visibles):
        es_modo_ciego = (modo_actual_remate == "Ciegos")
        abreviatura = obtener_abreviatura_carrera(c_nombre, modo_ciego=es_modo_ciego)
        with cols_carreras[idx]:
            if st.button(abreviatura, key=f"rem_btn_sel_carr_{idx}", use_container_width=True, type="primary" if c_nombre == carr_activa else "secondary"):
                st.session_state["carrera_remate_activa_seleccionada"] = c_nombre
                guardar_estado_global()
                st.rerun()
    st.markdown("---")

    dt_inicio_remate = st.session_state.fechas_horas_inicio_remate.get(carr_activa)
    remate_iniciado = not (dt_inicio_remate and ahora_dt < dt_inicio_remate)

    if carr_activa in st.session_state.imagenes_carreras:
        try: st.image(st.session_state.imagenes_carreras[carr_activa], use_container_width=True)
        except Exception: pass

    carrera_cerrada = st.session_state.carreras_cerradas_remate.get(carr_activa, False)
    estado_icono = "🔴" if (carrera_cerrada or not remate_iniciado) else "🟢"
    st.markdown(f"### {estado_icono} {carr_activa} ({modo_actual_remate})")

    detalles_carr = st.session_state.detalles_carreras.get(carr_activa, {})
    st.markdown(f"""
        <div class="carrera-condicion-card">
            🏷️ <b>Condición:</b> {detalles_carr.get('condicion', 'N/A')}<br>
            📏 <b>Distancia:</b> {detalles_carr.get('distancia', 'N/A')} &nbsp;|&nbsp; ⏰ <b>Hora:</b> {detalles_carr.get('hora', 'N/A')}
        </div>
    """, unsafe_allow_html=True)

    if not remate_iniciado:
        st.warning(f"⏳ Remate programado para abrir el {dt_inicio_remate.strftime('%d/%m/%Y a las %I:%M %p')}.")
    else:
        if carr_activa not in st.session_state.ejemplares_retirados:
            st.session_state.ejemplares_retirados[carr_activa] = []
        
        # TABLA NATIVA DE REMATES 100% LIMPIA
        datos_tabla = []
        retirados_carr = st.session_state.ejemplares_retirados.get(carr_activa, [])
        for cab, info in st.session_state.remates[carr_activa].items():
            match_num = re.match(r'^(\d+)', cab)
            num = int(match_num.group(1)) if match_num else 0
            nombre_solo = cab.split(" - ", 1)[1] if " - " in cab else cab
            es_ret = cab in retirados_carr
            datos_tabla.append({
                "No": num,
                "Ejemplar": f"{nombre_solo.upper()} {'(RETIRADO)' if es_ret else ''}",
                "Comprador": info['jugador'],
                "Monto": formatear_bs(info['monto'])
            })
        st.dataframe(pd.DataFrame(datos_tabla), use_container_width=True, hide_index=True)

        total_pote = sum([info['monto'] for cab_n, info in st.session_state.remates[carr_activa].items() if cab_n not in retirados_carr])
        monto_casa = total_pote * (porcentaje_casa / 100)
        pote_neto_base = total_pote - monto_casa
        
        incentivo_actual = float(detalles_carr.get(f'incentivo_{modo_actual_remate.lower()}', 0.0)) if modo_actual_remate != "En Vivo" else float(detalles_carr.get('incentivo_envivo', 0.0))
        premio_total = pote_neto_base + incentivo_actual

        if incentivo_actual > 0:
            st.markdown(f'<div class="incentivo-llamativo"><div class="incentivo-llamativo-monto">🎁 {formatear_bs(incentivo_actual)}</div></div>', unsafe_allow_html=True)

        c_m1, c_m2 = st.columns(2)
        c_m1.metric("💰 Pote", formatear_bs(total_pote))
        c_m2.metric("🏆 Premio Total", formatear_bs(premio_total))

def render_dupletas():
    st.markdown(f"<div class='subasta-header'>🎟️ Módulo de Dupletas y Polla</div>", unsafe_allow_html=True)
    if st.session_state.dupleta_bloqueada:
        st.error("🔒 **BLOQUEADO:** Emisión de tickets cerrada temporalmente.")
    st.info("Seleccione sus opciones en el panel superior de sub-secciones.")

def render_cuentas():
    st.markdown("<div class='subasta-header'>📊 Mis Cuentas y Historial de Jugador</div>", unsafe_allow_html=True)
    jugador_actual = st.session_state.usuario_activo
    if jugador_actual not in st.session_state.cuentas:
        st.session_state.cuentas[jugador_actual] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
    vals = st.session_state.cuentas[jugador_actual]
    neto = vals['Pujas'] - vals['Abonos'] - vals['Premios']
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Compras", formatear_bs(vals['Pujas']))
    c2.metric("Premios", formatear_bs(vals['Premios']))
    c3.metric("Pagos", formatear_bs(vals['Abonos']))
    c4.metric("Neto", formatear_bs(neto))

def render_admin():
    st.markdown("<div class='subasta-header'>🔒 Panel de Configuración y Administración</div>", unsafe_allow_html=True)
    st.success("Zona de administración activa.")

# --- CONTROLADOR MAESTRO DE VISTAS AISLADAS ---
if menu_principal_opcion == "Remates":
    render_remates()
elif menu_principal_opcion == "Dupletas":
    render_dupletas()
elif menu_principal_opcion == "Cuentas":
    render_cuentas()
elif menu_principal_opcion == "🔒 Zona Admin":
    render_admin()

# --- TRANSMISIÓN EN VIVO ---
url_live_video = st.session_state.get('url_video_en_vivo', '').strip()
if url_live_video:
    st.markdown("<br><hr style='border-color: #30363d;'>", unsafe_allow_html=True)
    st.markdown("### 📺 TRANSMISIÓN EN VIVO")
    try: st.video(url_live_video)
    except Exception: pass

# --- SINCRONIZACIÓN AUTOMÁTICA ---
if menu_principal_opcion != "🔒 Zona Admin":
    time.sleep(6)
    cargar_estado_global(forzar_recarga=True)
    st.rerun()
