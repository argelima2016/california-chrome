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
st.set_page_config(page_title="CALIFORNIA CHROME", layout="wide", page_icon="🐺")

# --- HORA LOCAL DE VENEZUELA UNIFICADA ---
def obtener_hora_venezuela_local():
    try:
        zona_venezuela = ZoneInfo("America/Caracas")
        return datetime.now(zona_venezuela).replace(tzinfo=None)
    except Exception:
        pass
    utc_ahora = datetime.now(timezone.utc)
    return (utc_ahora - timedelta(hours=4)).replace(tzinfo=None)

def formatear_bs(monto):
    numero_formateado = f"{monto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"Bs. {numero_formateado}"

# --- SISTEMA DE PERSISTENCIA GLOBAL (JSON) ---
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
        'ejemplares_no_valido': {},
        'detalles_carreras': {},
        'historial_ganadores': {},
        'carreras_cerradas_remate': {},
        'remates_cargados_en_cuentas': {},
        'fechas_horas_inicio_remate_modalidad': {},
        'fechas_horas_cierre_remate_modalidad': {},
        'fechas_horas_inicio_modalidad_multiple': {},
        'fechas_horas_cierre_modalidad_multiple': {},
        'estado_conteo_carrera_modalidad': {},
        'tiempo_inicio_conteo_modalidad': {},
        'alertas_reproducidas': {},
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
        'datos_pago_movil': {
            'banco': 'Bancamiga (0172)',
            'telefono': '0412-0000000',
            'cedula': 'V-00.000.000'
        },
        'reportes_pago': []
    }
    
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for dict_key in ['fechas_horas_inicio_remate_modalidad', 'fechas_horas_cierre_remate_modalidad', 'fechas_horas_inicio_modalidad_multiple', 'fechas_horas_cierre_modalidad_multiple']:
                    if dict_key in data and isinstance(data[dict_key], dict):
                        for sub_k, sub_v in data[dict_key].items():
                            if isinstance(sub_v, str):
                                try:
                                    data[dict_key][sub_k] = datetime.fromisoformat(sub_v)
                                except Exception:
                                    pass
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
        'ejemplares_no_valido', 'detalles_carreras', 'historial_ganadores', 'carreras_cerradas_remate',
        'remates_cargados_en_cuentas', 'fechas_horas_inicio_remate_modalidad', 'fechas_horas_cierre_remate_modalidad',
        'fechas_horas_inicio_modalidad_multiple', 'fechas_horas_cierre_modalidad_multiple', 
        'estado_conteo_carrera_modalidad', 'alertas_reproducidas', 'cuentas', 'historial_jugadas', 'ganancia_casa',
        'dupletas_tickets', 'tripleta_tickets', 'polla_tickets', 'carreras_habilitadas_dupleta',
        'carreras_habilitadas_tripleta', 'carreras_habilitadas_polla', 'config_montos_especiales',
        'dupleta_bloqueada', 'carreras_activas_remate', 'carreras_por_modalidad',
        'total_carreras_semana', 'url_video_en_vivo', 'imagenes_carreras', 'admin_tab_seleccionada',
        'datos_pago_movil', 'reportes_pago'
    ]
    data = {}
    for k in keys_to_save:
        if k in st.session_state:
            val = st.session_state[k]
            if isinstance(val, dict):
                val_copy = {}
                for dk, dv in val.items():
                    if isinstance(dv, datetime):
                        val_copy[dk] = dv.isoformat()
                    else:
                        val_copy[dk] = dv
                data[k] = val_copy
            else:
                data[k] = val
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

cargar_estado_global()

# --- SCRIPT JS PARA COPIAR TODO EN 1 TOQUE Y ALERTAS MÓVILES ---
components.html("""
    <script>
        function copiarPagoMovilUnico(banco, telefono, cedula) {
            const textoCompleto = `DATOS PAGO MÓVIL:\\nBanco: ${banco}\\nTeléfono: ${telefono}\\nCédula/RIF: ${cedula}`;
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(textoCompleto).then(() => {
                    alert("¡Datos de Pago Móvil copiados al portapapeles!");
                }).catch(err => {
                    prompt("Copia manualmente:", textoCompleto);
                });
            } else {
                prompt("Copia manualmente:", textoCompleto);
            }
        }
        window.copiarPagoMovilUnico = copiarPagoMovilUnico;

        function reproducirAlertaMovilYCalle(tipo) {
            if ("vibrate" in navigator) {
                if (tipo === 'cierre') {
                    navigator.vibrate([200, 100, 200, 100, 400]);
                } else {
                    navigator.vibrate(300);
                }
            }
            try {
                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                if (audioCtx.state === 'suspended') { audioCtx.resume(); }
                const osc = audioCtx.createOscillator();
                const gainNode = audioCtx.createGain();
                osc.connect(gainNode);
                gainNode.connect(audioCtx.destination);
                if (tipo === 'cierre' || tipo === 'tiempo') {
                    osc.type = 'square';
                    osc.frequency.setValueAtTime(587.33, audioCtx.currentTime);
                    osc.frequency.setValueAtTime(880, audioCtx.currentTime + 0.15);
                    gainNode.gain.setValueAtTime(0.4, audioCtx.currentTime);
                    gainNode.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.5);
                    osc.start();
                    osc.stop(audioCtx.currentTime + 0.5);
                } else if (tipo === 'exito') {
                    osc.type = 'triangle';
                    osc.frequency.setValueAtTime(523.25, audioCtx.currentTime);
                    osc.frequency.setValueAtTime(659.25, audioCtx.currentTime + 0.15);
                    gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime);
                    gainNode.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.4);
                    osc.start();
                    osc.stop(audioCtx.currentTime + 0.4);
                }
            } catch (e) {
                console.log("Audio restringido.");
            }
        }
        window.reproducirAlertaMovilYCalle = reproducirAlertaMovilYCalle;

        function sincronizacionEnVivo() {
            const doc = window.parent.document;
            const selectors = [
                'header[data-testid="stHeader"]', 'footer', '.stDeployButton',
                'div[data-testid="stStatusWidget"]', '[data-testid="stToolbar"]', '#MainMenu', 'a[href*="streamlit.io"]'
            ];
            selectors.forEach(selector => {
                doc.querySelectorAll(selector).forEach(el => {
                    if (el) { el.style.display = 'none'; el.style.visibility = 'hidden'; el.style.opacity = '0'; el.remove(); }
                });
            });

            const relojElem = doc.getElementById('reloj-js-vivo');
            if (relojElem) {
                const options = { timeZone: 'America/Caracas', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true };
                relojElem.innerText = new Intl.DateTimeFormat('en-US', options).format(new Date());
            }

            let tuercaBtn = doc.getElementById('custom-tuerca-sidebar-btn');
            if (!tuercaBtn) {
                tuercaBtn = doc.createElement('button');
                tuercaBtn.id = 'custom-tuerca-sidebar-btn';
                tuercaBtn.innerHTML = '⚙️';
                tuercaBtn.title = 'Barra Lateral';
                tuercaBtn.style.position = 'fixed';
                tuercaBtn.style.top = '10px';
                tuercaBtn.style.right = '15px';
                tuercaBtn.style.zIndex = '99999';
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
                        } else {
                            sidebar.setAttribute('aria-expanded', 'false');
                            sidebar.style.transform = 'translateX(-100%)';
                            sidebar.style.visibility = 'hidden';
                            sidebar.style.display = 'none';
                            sidebar.style.minWidth = '0px';
                            sidebar.style.width = '0px';
                        }
                    }
                };
                doc.body.appendChild(tuercaBtn);
            }
        }
        setInterval(sincronizacionEnVivo, 1000);
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
    "1001397336_preview_rev_1.png", "1001397336_preview_rev_1.jpg",
    "1001397336.jpg", "1001397336.png", "logo.png", "logo.jpg"
]
img_b64 = get_image_base64(nombres_archivos)
logo_display = f'<img src="data:image/png;base64,{img_b64}" class="header-logo-img" />' if img_b64 else '<span style="color: #f1c40f; font-size: 38px; font-weight: 900; font-style: italic;">CALIFORNIA CHROME</span>'

# --- INICIALIZAR REMATES Y CARRERAS ---
if not st.session_state.remates or len(st.session_state.remates) != st.session_state.total_carreras_semana:
    nuevos_remates = {}
    nuevo_banco = {}
    nuevo_detalles = {}
    for i in range(1, int(st.session_state.total_carreras_semana) + 1):
        carr_nombre = f"Carrera {i}"
        nuevo_banco[carr_nombre] = [f"{j} - Ejemplar {j}" for j in range(1, 11)]
        nuevos_remates[carr_nombre] = {f"{j} - Ejemplar {j}": {"jugador": "Sin Postor", "monto": 0.0} for j in range(1, 11)}
        nuevo_detalles[carr_nombre] = {
            "condicion": "Condición estándar", "distancia": "1200 mts", "hora": "02:00 PM", 
            "monto_fijo_ciego": 500.0, "incentivo_adelantados": 0.0, "incentivo_ciegos": 0.0, "incentivo_envivo": 0.0, "hora_cierre_real": "No registrada"
        }
    st.session_state.banco_caballos_por_carrera = nuevo_banco
    st.session_state.remates = nuevos_remates
    st.session_state.detalles_carreras = nuevo_detalles

lista_carreras_disponibles = list(st.session_state.remates.keys())
ahora_dt = obtener_hora_venezuela_local()

# --- ESTILOS CSS GENERALES ---
st.markdown("""
    <style>
    * { box-sizing: border-box !important; }
    .stApp { background-color: #080a0f; color: #f0f6fc; overflow-x: hidden !important; }
    [data-testid="stSidebar"] { min-width: 360px !important; max-width: 360px !important; }
    [data-testid="stSidebar"] > div:first-child { width: 360px !important; padding-left: 1.2rem !important; padding-right: 1.2rem !important; }
    [data-testid="stToolbar"], header[data-testid="stHeader"], footer, #MainMenu { display: none !important; visibility: hidden !important; }
    .block-container { padding-top: 0.4rem !important; padding-bottom: 2rem !important; padding-left: 0.5rem !important; padding-right: 0.5rem !important; max-width: 100% !important; margin: 0 auto !important; }
    .stButton button { border-radius: 6px !important; font-weight: 700 !important; padding: 0.2rem 0.4rem !important; min-height: 38px !important; font-size: 12px !important; width: 100% !important; }
    .subasta-header { font-size: clamp(14px, 3.5vw, 18px); font-weight: 800; color: #f1e05a; margin-bottom: 4px; border-bottom: 2px solid #f1e05a; padding-bottom: 3px; }
    @keyframes latidoEmergencia { 0% { transform: scale(1); box-shadow: 0 0 10px #ff4757; } 50% { transform: scale(1.05); box-shadow: 0 0 30px #ff4757; } 100% { transform: scale(1); box-shadow: 0 0 10px #ff4757; } }
    .timer-box { background-color: #161b22; border: 2px solid #ff4757; padding: 12px; border-radius: 8px; text-align: center; font-size: clamp(18px, 4vw, 24px); font-weight: 900; color: #ff4757; margin-bottom: 12px; animation: latidoEmergencia 1s infinite; text-shadow: 0px 0px 10px rgba(255, 71, 87, 0.8); }
    .carrera-condicion-card { background-color: #161b22; border: 1px solid #30363d; padding: 8px 12px; border-radius: 6px; font-size: 12px; color: #f0f6fc; margin-bottom: 10px; line-height: 1.4; }
    .incentivo-llamativo { background: linear-gradient(135deg, #1f1c2c 0%, #923d41 100%); border: 2px dashed #00ffff; padding: 10px 16px; border-radius: 12px; text-align: center; margin: 10px 0; box-shadow: 0px 0px 15px rgba(0, 255, 255, 0.4); }
    .incentivo-llamativo-monto { color: #ffffff; font-size: 22px; font-weight: 900; letter-spacing: 0.5px; text-shadow: 2px 2px 4px #000000; }
    @keyframes parpadeoGanador { 0% { transform: scale(1); box-shadow: 0 0 15px #f1c40f, inset 0 0 15px #f1c40f; } 50% { transform: scale(1.02); box-shadow: 0 0 35px #00ffff, inset 0 0 25px #00ffff; } 100% { transform: scale(1); box-shadow: 0 0 15px #f1c40f, inset 0 0 15px #f1c40f; } }
    .ganador-banner-epic { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); border: 3px solid #f1c40f; border-radius: 14px; padding: 16px; text-align: center; margin: 12px 0; animation: parpadeoGanador 2s infinite ease-in-out; }
    .ganador-titulo-epic { color: #00ffff; font-size: 14px; font-weight: 900; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 6px; }
    .ganador-nombre-epic { color: #f1c40f; font-size: 24px; font-weight: 900; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 4px; }
    .ganador-premio-epic { color: #2ed573; font-size: 18px; font-weight: 900; }
    .ticket-jugador-card { background: #0d1117; border: 2px solid #30363d; border-radius: 10px; padding: 12px 16px; margin-bottom: 10px; box-shadow: 0px 4px 12px rgba(0,0,0,0.5); }
    .ticket-header-row { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #30363d; padding-bottom: 6px; margin-bottom: 8px; font-size: 12px; font-weight: 800; color: #f1c40f; }
    .ticket-body-row { font-size: 13px; color: #f0f6fc; margin-bottom: 4px; font-weight: 600; }
    .header-container-modern { background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); border: 1px solid #30363d; border-radius: 12px; padding: 14px 18px; margin-bottom: 10px; display: flex; flex-direction: column; gap: 14px; width: 100%; }
    .header-top-row { display: flex; justify-content: space-between; align-items: center; width: 100%; }
    .header-user-card { display: flex; align-items: center; gap: 10px; background: #080a0f; border: 1px solid #30363d; padding: 6px 12px; border-radius: 8px; }
    .user-details { display: flex; flex-direction: column; text-align: right; }
    .u-name { color: #f0f6fc; font-size: 13px; font-weight: 800; }
    .u-bal { font-size: 11px; font-weight: 700; }
    .u-avatar-badge { width: 34px; height: 34px; background: #1f6feb; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 16px; }
    .header-logo-img { max-height: 120px; width: auto; object-fit: contain; }
    .reloj-digital-container { background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); border: 1.5px solid #00ffff; border-radius: 10px; padding: 10px 18px; display: flex; justify-content: center; align-items: center; margin-bottom: 12px; box-shadow: 0px 0px 15px rgba(0, 255, 255, 0.3); }
    .reloj-digital-txt { color: #00ffff; font-size: 20px; font-weight: 900; letter-spacing: 2px; font-family: monospace; }
    @keyframes parpadeoLed { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.9); } 100% { opacity: 1; transform: scale(1); } }
    .led-estado { width: 10px; height: 10px; border-radius: 50%; display: inline-block; box-shadow: 0 0 8px currentColor; }
    .led-verde { background-color: #2ed573; color: #2ed573; animation: parpadeoLed 1.5s infinite ease-in-out; }
    .led-rojo { background-color: #ff4757; color: #ff4757; }
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

estado_global_remate = "cerrados" if all(st.session_state.carreras_cerradas_remate.get(c, False) for c in lista_carreras_disponibles) and lista_carreras_disponibles else "abiertos"
led_clase_css = "led-rojo" if estado_global_remate == "cerrados" else "led-verde"

col_h_izq, col_h_der = st.columns([1, 1], gap="small")
with col_h_izq:
    if st.button("💳 Reportar Pago Móvil", key="btn_ir_reportar_pago_top", use_container_width=True, type="primary"):
        st.session_state.menu_principal_opcion = "Cuentas"
        guardar_estado_global()
        st.rerun()

st.markdown(f"""
    <div class="header-container-modern" style="margin-top: 8px;">
        <div class="header-top-row">
            <div></div>
            <div class="header-user-card">
                <div class="user-details">
                    <div class="u-name-container">
                        <span class="u-name">{usuario_en_sesion}</span>
                        <span class="led-estado {led_clase_css}" title="Remates En Línea"></span>
                    </div>
                    <span class="u-bal" style="color: {color_balance};">{etiqueta_balance}</span>
                </div>
                <div class="u-avatar-badge">🐺</div>
            </div>
        </div>
        <div style="text-align: center; border-top: 1px solid #21262d; padding-top: 12px;">
            {logo_display}
        </div>
    </div>
""", unsafe_allow_html=True)

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
        .tabla-referencia { width: 100%; border-collapse: collapse; font-family: sans-serif; background-color: #ffffff; color: #000000; margin-bottom: 10px; table-layout: fixed; }
        .tabla-referencia th { border-top: 2px solid #dfc729; border-bottom: 2px solid #dfc729; padding: 6px 4px; text-align: left; font-weight: 800; background-color: #ffffff; color: #000000; font-size: 11px; }
        .tabla-referencia td { border-bottom: 1px solid #dfc729; padding: 6px 4px; background-color: #fbfbfb; color: #111111; font-size: 11px; vertical-align: middle; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .badge-numero { display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; font-weight: bold; font-size: 11px; border-radius: 2px; }
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
        num = int(match_num.group(1)) if match_num else 0
        nombre_solo = cab.split(" - ", 1)[1] if " - " in cab else cab
        badge_class = f"badge-{num}" if 1 <= num <= 7 else "badge-default"
        
        es_retirado = cab in retirados_list
        es_novale = cab in no_validos_list
        clase_fila = "retirado-row" if es_retirado else ("novale-row" if es_novale else "")
        etiqueta_estado = " (RETIRADO)" if es_retirado else (" (NO VALE)" if es_novale else "")
        
        html += f"""
                <tr class="{clase_fila}">
                    <td><span class="badge-numero {badge_class}">{num}</span></td>
                    <td style="font-weight: 800; font-size: 12px;" title="{nombre_solo.upper()}{etiqueta_estado}">{nombre_solo.upper()}{etiqueta_estado}</td>
                    <td title="{info['jugador']}">{info['jugador']}</td>
                    <td style="font-weight: bold; color: { '#990000' if es_retirado else ('#856404' if es_novale else '#000000') };">{formatear_bs(info['monto'])}</td>
                </tr>
        """
    html += "</tbody></table></div>"
    return html

# --- GARANTIZAR MODALIDADES ---
for mod in ["Adelantados", "Ciegos", "En Vivo"]:
    if mod not in st.session_state.carreras_por_modalidad:
        st.session_state.carreras_por_modalidad[mod] = []

if not st.session_state.carreras_habilitadas_dupleta and lista_carreras_disponibles:
    st.session_state.carreras_habilitadas_dupleta = list(lista_carreras_disponibles)
if not st.session_state.carreras_habilitadas_tripleta and lista_carreras_disponibles:
    st.session_state.carreras_habilitadas_tripleta = list(lista_carreras_disponibles)
if not st.session_state.carreras_habilitadas_polla and lista_carreras_disponibles:
    st.session_state.carreras_habilitadas_polla = list(lista_carreras_disponibles)

# --- MENÚ PRINCIPAL HORIZONTAL ---
col_menu1, col_menu2, col_menu3, col_menu4 = st.columns(4, gap="small")
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
with col_menu4:
    if st.button("⚙️ CONFIG", key="menu_btn_config_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "🔒 Zona Admin" else "secondary"):
        st.session_state.menu_principal_opcion = "🔒 Zona Admin"
        guardar_estado_global()
        st.rerun()

st.markdown("<hr style='margin: 0.3rem 0; border-color: #21262d;'>", unsafe_allow_html=True)

# --- BANNER MARQUESINA ---
elementos_carrusel_info = []
for mod_m in ["Adelantados", "Ciegos", "En Vivo"]:
    carrs_m = [c for c in st.session_state.carreras_por_modalidad.get(mod_m, []) if c in lista_carreras_disponibles]
    if carrs_m:
        prefijo_m = "🔴 EN VIVO" if mod_m == "En Vivo" else mod_m.upper()
        elementos_carrusel_info.append(f"{prefijo_m}: " + " | ".join(carrs_m))

if not elementos_carrusel_info:
    elementos_carrusel_info.append("⏳ CONFIGURA LAS CARRERAS ASIGNADAS EN LA ZONA ADMIN")

texto_unido_marquesina = " &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ".join(elementos_carrusel_info)
html_banner_marquesina = f"""
<style>
    .marquee-container {{ width: 100%; background: transparent; padding: 8px 0; margin-bottom: 12px; overflow: hidden; display: flex; align-items: center; }}
    .marquee-text {{ display: inline-block; white-space: nowrap; animation: scrollRight 150s linear infinite !important; font-family: 'Arial Black', Gadget, sans-serif; font-size: 15px; font-weight: 900; color: #00ffff; text-transform: uppercase; letter-spacing: 1.5px; text-shadow: 0px 0px 10px rgba(0, 255, 255, 0.9), 2px 2px 2px #000000; padding-right: 100%; }}
    @keyframes scrollRight {{ 0% {{ transform: translateX(-100%); }} 100% {{ transform: translateX(100%); }} }}
</style>
<div class="marquee-container"><div class="marquee-text">{texto_unido_marquesina}</div></div>
"""
components.html(html_banner_marquesina, height=42)

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
            st.session_state.detalles_carreras[carr_seleccionada_liq]["hora_cierre_real"] = ahora_dt.strftime('%I:%M:%S %p')
            if not st.session_state.remates_cargados_en_cuentas.get(carr_seleccionada_liq, False):
                retirados_carr = st.session_state.ejemplares_retirados.get(carr_seleccionada_liq, [])
                no_val_carr = st.session_state.get('ejemplares_no_valido', {}).get(carr_seleccionada_liq, [])
                for cab, info in st.session_state.remates[carr_seleccionada_liq].items():
                    if cab in retirados_carr or cab in no_val_carr: continue
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
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    st.toast("🚨 Jornada reiniciada.")
    st.rerun()

menu_principal_opcion = st.session_state.menu_principal_opcion

# =========================================================================
# BLOQUE FRAGMENTADO UNIVERSAL EN TIEMPO REAL
# =========================================================================
@st.fragment(run_every=10.0)
def renderizar_tiempo_real_universal():
    cargar_estado_global(forzar_recarga=True)
    ahora_dt_frag = obtener_hora_venezuela_local()

    if st.session_state.menu_principal_opcion == "Remates":
        col_so1, col_so2, col_so3 = st.columns(3, gap="small")
        with col_so1:
            if st.button("Adelantados", key="sub_rem_adelantados", use_container_width=True, type="primary" if st.session_state.sub_remate_opcion == "Adelantados" else "secondary"):
                st.session_state.sub_remate_opcion = "Adelantados"
                guardar_estado_global()
                st.rerun()
        with col_so2:
            if st.button("Ciegos", key="sub_rem_ciegos", use_container_width=True, type="primary" if st.session_state.sub_remate_opcion == "Ciegos" else "secondary"):
                st.session_state.sub_remate_opcion = "Ciegos"
                guardar_estado_global()
                st.rerun()
        with col_so3:
            if st.button("🔴 En Vivo", key="sub_rem_envivo", use_container_width=True, type="primary" if st.session_state.sub_remate_opcion == "En Vivo" else "secondary"):
                st.session_state.sub_remate_opcion = "En Vivo"
                guardar_estado_global()
                st.rerun()

        st.markdown("<hr style='margin: 0.3rem 0; border-color: #21262d;'>", unsafe_allow_html=True)
        modo_actual_remate = st.session_state.sub_remate_opcion

        if not lista_carreras_disponibles:
            st.warning("⚠️ No hay carreras cargadas en el sistema.")
        else:
            # --- FILTRADO ESTRICTO DE EXCLUSIÓN MUTUA ENTRE MODALIDADES ---
            carreras_asignadas_admin = st.session_state.carreras_por_modalidad.get(modo_actual_remate, [])
            
            carreras_filtradas_visibles = []
            for c in carreras_asignadas_admin:
                if c not in lista_carreras_disponibles: continue
                asignada_en_otra = False
                for otra_mod, lista_otra in st.session_state.carreras_por_modalidad.items():
                    if otra_mod != modo_actual_remate and c in lista_otra:
                        asignada_en_otra = True
                        break
                if not asignada_en_otra:
                    carreras_filtradas_visibles.append(c)

            if modo_actual_remate == "Ciegos":
                carreras_filtradas_visibles = carreras_filtradas_visibles[:2]

            if not carreras_filtradas_visibles:
                if modo_actual_remate == "Ciegos":
                    st.info("ℹ️ El Remate Ciego requiere exactamente dos carreras exclusivas asignadas en la Zona Admin.")
                else:
                    st.info(f"ℹ️ No hay carreras exclusivas asignadas para la modalidad **{modo_actual_remate}**. Configúralas en Zona Admin.")
            else:
                if "carrera_remate_activa_seleccionada" not in st.session_state or st.session_state["carrera_remate_activa_seleccionada"] not in carreras_filtradas_visibles:
                    carr_activa = carreras_filtradas_visibles[0]
                    st.session_state["carrera_remate_activa_seleccionada"] = carr_activa
                else:
                    carr_activa = st.session_state["carrera_remate_activa_seleccionada"]

                st.markdown("🔹 **Seleccionar Carrera:**")
                cols_carreras = st.columns(len(carreras_filtradas_visibles), gap="small")
                for idx, c_nombre in enumerate(carreras_filtradas_visibles):
                    abreviatura = obtener_abreviatura_carrera(c_nombre, modo_actual=modo_actual_remate)
                    es_activa = (c_nombre == carr_activa)
                    with cols_carreras[idx]:
                        if st.button(abreviatura, key=f"rem_btn_sel_carr_{idx}", use_container_width=True, type="primary" if es_activa else "secondary"):
                            st.session_state["carrera_remate_activa_seleccionada"] = c_nombre
                            guardar_estado_global()
                            st.rerun()
                st.markdown("---")

                hora_actual_envivo = ahora_dt_frag.strftime('%I:%M:%S %p')
                st.markdown(f"""
                    <div class="reloj-digital-container">
                        <span id="reloj-js-vivo" class="reloj-digital-txt">{hora_actual_envivo}</span>
                    </div>
                """, unsafe_allow_html=True)

                if carr_activa in st.session_state.imagenes_carreras:
                    try:
                        st.image(st.session_state.imagenes_carreras[carr_activa], caption=f"Imagen oficial - {carr_activa}", use_container_width=True)
                    except Exception:
                        pass

                carrera_cerrada = st.session_state.carreras_cerradas_remate.get(carr_activa, False)
                estado_icono = "🔴" if carrera_cerrada else "🟢"
                
                st.markdown(f"""
                    <div style="font-size: 14px; font-weight: 800; color: #f0f6fc; display: flex; align-items: center; gap: 6px; margin-top: 8px; margin-bottom: 8px;">
                        <span>{estado_icono}</span>
                        <span>{carr_activa}</span>
                        <span style="font-size: 11px; font-weight: 600; color: #8b949e; background: #161b22; padding: 1px 6px; border-radius: 4px; border: 1px solid #30363d;">{modo_actual_remate}</span>
                    </div>
                """, unsafe_allow_html=True)

                if carr_activa not in st.session_state.detalles_carreras:
                    st.session_state.detalles_carreras[carr_activa] = {
                        "condicion": "Condición general", "distancia": "1200 mts", "hora": "02:00 PM", 
                        "monto_fijo_ciego": 500.0, "incentivo_adelantados": 0.0, "incentivo_ciegos": 0.0, "incentivo_envivo": 0.0, "hora_cierre_real": "No registrada"
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
                if 'ejemplares_no_valido' not in st.session_state:
                    st.session_state.ejemplares_no_valido = {}
                if carr_activa not in st.session_state.ejemplares_no_valido:
                    st.session_state.ejemplares_no_valido[carr_activa] = []
                
                lista_todos_caballos_carr = list(st.session_state.remates[carr_activa].keys())
                retirados_actuales_carr = [c for c in st.session_state.ejemplares_retirados[carr_activa] if c in lista_todos_caballos_carr]
                no_validos_actuales_carr = [c for c in st.session_state.ejemplares_no_valido[carr_activa] if c in lista_todos_caballos_carr]

                with st.expander("🚫 Gestionar Ejemplares Retirados", expanded=False):
                    nuevos_retirados = st.multiselect(
                        "Selecciona los ejemplares retirados en esta carrera:",
                        options=lista_todos_caballos_carr, default=retirados_actuales_carr, key=f"multiselect_retirados_{carr_activa}"
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
                                        "fecha": ahora_dt_frag.strftime('%d/%m/%Y %I:%M:%S %p'), "jugador": comprador,
                                        "tipo": "Retirado (Descuento)", "carrera": carr_activa, "detalle": f"Ejemplar retirado: {cab_ret}", "monto": -monto_ej
                                    })
                        st.session_state.ejemplares_retirados[carr_activa] = nuevos_retirados
                        guardar_estado_global()
                        st.toast("✅ ¡Retirados actualizados!")
                        st.rerun()

                clave_mod_carr = f"{modo_actual_remate}_{carr_activa}"
                dt_inicio = st.session_state.fechas_horas_inicio_remate_modalidad.get(clave_mod_carr)
                dt_limite = st.session_state.fechas_horas_cierre_remate_modalidad.get(clave_mod_carr)
                estado_conteo = st.session_state.estado_conteo_carrera_modalidad.get(clave_mod_carr, "INACTIVO")

                if isinstance(dt_inicio, str):
                    try: dt_inicio = datetime.fromisoformat(dt_inicio)
                    except Exception: dt_inicio = None
                if isinstance(dt_limite, str):
                    try: dt_limite = datetime.fromisoformat(dt_limite)
                    except Exception: dt_limite = None

                if dt_inicio and carrera_cerrada:
                    if ahora_dt_frag >= dt_inicio:
                        st.session_state.carreras_cerradas_remate[carr_activa] = False
                        guardar_estado_global()
                        carrera_cerrada = False

                if dt_inicio:
                    st.markdown(f"<div style='background:#161b22; padding:6px; border-radius:6px; margin-bottom:4px; border:1px solid #30363d; font-size:12px;'>🟢 Inicio Remate ({modo_actual_remate}): <b>{dt_inicio.strftime('%d/%m/%Y - %I:%M %p')}</b></div>", unsafe_allow_html=True)
                if dt_limite:
                    st.markdown(f"<div style='background:#161b22; padding:6px; border-radius:6px; margin-bottom:8px; border:1px solid #30363d; font-size:12px;'>⏰ Cierre Estricto ({modo_actual_remate}): <b>{dt_limite.strftime('%d/%m/%Y - %I:%M %p')}</b></div>", unsafe_allow_html=True)

                # --- ALERTAS Y CONTEO REGRESIVO ---
                if dt_limite and not carrera_cerrada:
                    diferencia_segundos = (dt_limite - ahora_dt_frag).total_seconds()
                    if diferencia_segundos > 0:
                        min_rest = int(diferencia_segundos / 60)
                        seg_rest = int(diferencia_segundos % 60)
                        alertas_target = [60, 30, 20, 10, 5, 4, 3, 2, 1]
                        if min_rest in alertas_target and seg_rest <= 10:
                            clave_alerta = f"{clave_mod_carr}_{min_rest}m"
                            if clave_alerta not in st.session_state.get('alertas_reproducidas', {}):
                                if 'alertas_reproducidas' not in st.session_state: st.session_state.alertas_reproducidas = {}
                                st.session_state.alertas_reproducidas[clave_alerta] = True
                                txt_tiempo = "1 hora" if min_rest == 60 else f"{min_rest} minutos"
                                st.toast(f"⏳ ¡ATENCIÓN! Faltan {txt_tiempo} para el cierre de {carr_activa}", icon="🚨")
                                components.html("<script>window.parent.reproducirAlertaMovilYCalle('tiempo');</script>", height=0, width=0)

                    if estado_conteo == "INACTIVO":
                        if 0 < diferencia_segundos <= 10:
                            st.session_state.estado_conteo_carrera_modalidad[clave_mod_carr] = "CONTEO_10S"
                            st.session_state.tiempo_inicio_conteo_modalidad[clave_mod_carr] = ahora_dt_frag
                            guardar_estado_global()
                            components.html("<script>window.parent.reproducirAlertaMovilYCalle('cierre');</script>", height=0, width=0)
                            st.rerun()
                        elif diferencia_segundos <= 0:
                            st.session_state.carreras_cerradas_remate[carr_activa] = True
                            st.session_state.estado_conteo_carrera_modalidad[clave_mod_carr] = "CERRADO"
                            guardar_estado_global()
                            st.rerun()
                    elif estado_conteo == "CONTEO_10S":
                        tiempo_inicio = st.session_state.tiempo_inicio_conteo_modalidad.get(clave_mod_carr, ahora_dt_frag)
                        transcurridos = (ahora_dt_frag - tiempo_inicio).total_seconds()
                        if transcurridos >= 10:
                            st.session_state.carreras_cerradas_remate[carr_activa] = True
                            st.session_state.estado_conteo_carrera_modalidad[clave_mod_carr] = "CERRADO"
                            guardar_estado_global()
                            st.rerun()
                        else:
                            restantes_10s = max(0, 10 - int(transcurridos))
                            if restantes_10s > 0:
                                st.markdown(f"<div class='timer-box'>⚠️ CIERRE INMINENTE: <b>{restantes_10s}s</b><br><span style='font-size:12px; font-weight:normal;'>(Nuevas pujas reinician el contador)</span></div>", unsafe_allow_html=True)

                tabla_html = generar_tabla_html_remate(st.session_state.remates[carr_activa], st.session_state.ejemplares_retirados.get(carr_activa, []), st.session_state.ejemplares_no_valido.get(carr_activa, []))
                cantidad_filas = len(st.session_state.remates[carr_activa])
                components.html(tabla_html, height=min(max(140, (cantidad_filas * 35) + 50), 420), scrolling=True)
                
                excluidos_carr_activa = set(retirados_actuales_carr) | set(no_validos_actuales_carr)
                total_pote = sum([info['monto'] for cab_n, info in st.session_state.remates[carr_activa].items() if cab_n not in excluidos_carr_activa])
                monto_casa = total_pote * (porcentaje_casa / 100)
                pote_neto_base = total_pote - monto_casa

                incentivo_actual = float(detalles_carr.get(f'incentivo_{modo_actual_remate.lower().replace(" ", "")}', 0.0))
                premio_total_calculado = pote_neto_base + incentivo_actual

                if incentivo_actual > 0:
                    st.markdown(f"""
                        <div class="incentivo-llamativo">
                            <div style="font-size: 11px; font-weight: 800; color: #00ffff; text-transform: uppercase; margin-bottom: 2px;">PREMIO TOTAL</div>
                            <div class="incentivo-llamativo-monto">🎁 {formatear_bs(premio_total_calculado)}</div>
                        </div>
                    """, unsafe_allow_html=True)

                c_m1, c_m2 = st.columns(2)
                c_m1.metric(f"💰 Pote ({carr_activa})", formatear_bs(total_pote))
                c_m2.metric(f"🎁 Incentivo ({carr_activa})", formatear_bs(incentivo_actual))

                if carr_activa in st.session_state.historial_ganadores:
                    info_g_prev = st.session_state.historial_ganadores[carr_activa]
                    st.markdown(f"""
                        <div class="ganador-banner-epic">
                            <div class="ganador-titulo-epic">🏆 ¡RESULTADO OFICIAL - {carr_activa.upper()}! 🏆</div>
                            <div class="ganador-nombre-epic">🎉 {info_g_prev.get('Ganador', 'N/A')} 🎉</div>
                            <div style="color: #00ffff; font-size: 16px; font-weight: 900; margin-bottom: 4px;">🐎 EJEMPLAR: {info_g_prev.get('Caballo', 'N/A').upper()}</div>
                            <div class="ganador-premio-epic">💰 Premio Liquidado: {info_g_prev.get('Premio', '0')}</div>
                        </div>
                    """, unsafe_allow_html=True)

                if modo_actual_remate == "Adelantados":
                    with st.container(border=True):
                        st.markdown(f"<p style='font-size: 11px; font-weight: 700; margin-bottom: 2px; color: #f1e05a;'>🎯 Liquidar Ganador - {carr_activa}</p>", unsafe_allow_html=True)
                        if carr_activa not in st.session_state.historial_ganadores:
                            cabs_ganador = [c for c in list(st.session_state.remates[carr_activa].keys()) if c not in excluidos_carr_activa] or list(st.session_state.remates[carr_activa].keys())
                            col_g1, col_g2 = st.columns([3, 2], gap="small")
                            with col_g1:
                                caballo_ganador_elegido = st.selectbox("Ganador", cabs_ganador, key=f"rem_sel_ganador_{carr_activa}", label_visibility="collapsed")
                            with col_g2:
                                if st.button("🏆 Liquidar", key=f"rem_btn_liquidar_{carr_activa}", use_container_width=True, type="primary"):
                                    pote_tot = sum([info['monto'] for cab_n, info in st.session_state.remates[carr_activa].items() if cab_n not in excluidos_carr_activa])
                                    m_casa = pote_tot * (porcentaje_casa / 100)
                                    premio_liq = pote_tot - m_casa + float(detalles_carr.get('incentivo_adelantados', 0.0))
                                    info_g = st.session_state.remates[carr_activa][caballo_ganador_elegido]
                                    if info_g['jugador'] != "Sin Postor":
                                        if info_g['jugador'] not in st.session_state.cuentas: st.session_state.cuentas[info_g['jugador']] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                                        st.session_state.cuentas[info_g['jugador']]['Premios'] += premio_liq
                                    st.session_state.ganancia_casa += m_casa
                                    st.session_state.historial_ganadores[carr_activa] = {"Ganador": info_g['jugador'], "Premio": formatear_bs(premio_liq), "Caballo": caballo_ganador_elegido}
                                    guardar_estado_global()
                                    st.rerun()

                # --- BLOQUEO ESTRICTO POR HORARIO ---
                fuera_de_horario = False
                if dt_inicio and ahora_dt_frag < dt_inicio:
                    fuera_de_horario = True
                    st.error("⏳ **REMATES CERRADOS:** Aún no es la hora de apertura para esta modalidad.")
                elif (dt_limite and ahora_dt_frag >= dt_limite) or carrera_cerrada:
                    fuera_de_horario = True
                    st.error("🔒 **REMATES FINALIZADOS:** El tiempo límite de esta modalidad ha culminado.")

                with st.container(border=True):
                    if fuera_de_horario:
                        st.warning("🚫 Las acciones de puja están deshabilitadas fuera del horario establecido.")
                    else:
                        if modo_actual_remate == "Ciegos":
                            st.markdown(f"🙈 **Remate Ciego - Asignación ({carr_activa})**")
                            monto_fijo_carrera = detalles_carr.get('monto_fijo_ciego', 500.0)
                            cabs_ciego = [cab for cab, info in st.session_state.remates[carr_activa].items() if (info['jugador'] == "Sin Postor" or info['monto'] <= 0) and cab not in excluidos_carr_activa]
                            if not cabs_ciego:
                                st.warning("⚠️ Todos los ejemplares ya han sido adquiridos.")
                            else:
                                cols_cg = st.columns(min(3, len(cabs_ciego)), gap="small")
                                for idx_cb, cb_disp in enumerate(cabs_ciego):
                                    num_cb_parte = cb_disp.split(" - ")[0]
                                    with cols_cg[idx_cb % len(cols_cg)]:
                                        if st.button(f"#{num_cb_parte}", key=f"btn_ciego_{carr_activa}_{cb_disp}", use_container_width=True, type="primary"):
                                            st.session_state.remates[carr_activa][cb_disp] = {"jugador": st.session_state.usuario_activo, "monto": monto_fijo_carrera}
                                            st.session_state.historial_jugadas.append({
                                                "fecha": ahora_dt_frag.strftime('%d/%m/%Y %I:%M:%S %p'), "jugador": st.session_state.usuario_activo,
                                                "tipo": f"Remate Ciego", "carrera": carr_activa, "detalle": cb_disp, "monto": monto_fijo_carrera
                                            })
                                            if st.session_state.usuario_activo not in st.session_state.cuentas: st.session_state.cuentas[st.session_state.usuario_activo] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                                            st.session_state.cuentas[st.session_state.usuario_activo]['Pujas'] += monto_fijo_carrera
                                            guardar_estado_global()
                                            components.html("<script>window.parent.reproducirAlertaMovilYCalle('exito');</script>", height=0, width=0)
                                            st.success(f"🎉 #{num_cb_parte} asignado!")
                                            st.rerun()
                        else:
                            st.markdown(f"⚡ **Registro Rápido de Puja - {carr_activa}**")
                            cabs_activos = [c for c in list(st.session_state.remates[carr_activa].keys()) if c not in excluidos_carr_activa]
                            if not cabs_activos:
                                st.warning("No hay ejemplares disponibles para pujar.")
                            else:
                                k_sel_cab = f"rem_cab_click_{carr_activa}"
                                if k_sel_cab not in st.session_state or st.session_state[k_sel_cab] not in cabs_activos:
                                    st.session_state[k_sel_cab] = cabs_activos[0]
                                
                                cols_ej = 3
                                num_f = (len(cabs_activos) + cols_ej - 1) // cols_ej
                                idx_c = 0
                                for _ in range(num_f):
                                    c_fil = st.columns(cols_ej, gap="small")
                                    for cc in range(cols_ej):
                                        if idx_c < len(cabs_activos):
                                            item_c = cabs_activos[idx_c]
                                            n_parte = item_c.split(" - ")[0]
                                            prop = st.session_state.remates[carr_activa][item_c].get('jugador', 'Sin Postor')
                                            est_st = "#e2e8f0; color: #1e293b;" if prop == "Sin Postor" or prop == "CASA" else ("#22c55e; color: #ffffff;" if prop == st.session_state.usuario_activo else "#ef4444; color: #ffffff;")
                                            with c_fil[cc]:
                                                st.markdown(f'<style>div[data-testid="stVerticalBlock"] button[key="btn_c_{carr_activa}_{idx_c}"] {{ background-color: {est_st} }}</style>', unsafe_allow_html=True)
                                                if st.button(f"#{n_parte}", key=f"btn_c_{carr_activa}_{idx_c}", use_container_width=True):
                                                    st.session_state[k_sel_cab] = item_c
                                                    st.rerun()
                                            idx_c += 1

                                sel_cab_actual = st.session_state[k_sel_cab]
                                st.info(f"Ejemplar activo: **{sel_cab_actual}** (Poseedor: **{st.session_state.remates[carr_activa][sel_cab_actual].get('jugador')}**)")
                                m_act = st.session_state.remates[carr_activa][sel_cab_actual]['monto']
                                monto_puja = st.selectbox("💰 Monto de Puja", obtener_siguientes_montos(m_act), format_func=lambda x: formatear_bs(x), key=f"sel_m_{carr_activa}")
                                
                                if st.button(f"🔨 Confirmar Puja", key=f"btn_conf_{carr_activa}", use_container_width=True, type="primary"):
                                    if monto_puja <= m_act:
                                        st.error("Debe ser mayor a la puja actual.")
                                    else:
                                        st.session_state.remates[carr_activa][sel_cab_actual] = {"jugador": st.session_state.usuario_activo, "monto": monto_puja}
                                        st.session_state.historial_jugadas.append({
                                            "fecha": ahora_dt_frag.strftime('%d/%m/%Y %I:%M:%S %p'), "jugador": st.session_state.usuario_activo,
                                            "tipo": f"Remate ({modo_actual_remate})", "carrera": carr_activa, "detalle": sel_cab_actual, "monto": monto_puja
                                        })
                                        if estado_conteo == "CONTEO_10S":
                                            st.session_state.tiempo_inicio_conteo_modalidad[clave_mod_carr] = obtener_hora_venezuela_local()
                                        guardar_estado_global()
                                        components.html("<script>window.parent.reproducirAlertaMovilYCalle('exito');</script>", height=0, width=0)
                                        st.success("✅ ¡Puja registrada!")
                                        st.rerun()

renderizar_tiempo_real_universal()

# =========================================================================
# 2. MÓDULO DE DUPLETA Y 6 EN LINEA
# =========================================================================
if menu_principal_opcion == "Dupletas":
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

    st.markdown("<hr style='margin: 0.3rem 0; border-color: #21262d;'>", unsafe_allow_html=True)
    sub_dup_actual = st.session_state.sub_dupleta_opcion
    st.markdown(f"<div class='subasta-header'>🎟️ Armado Visual de {sub_dup_actual}</div>", unsafe_allow_html=True)
    
    monto_unico_seccion = st.session_state.config_montos_especiales.get(sub_dup_actual, 500.0)
    carreras_permitidas = [c for c in (st.session_state.carreras_habilitadas_dupleta if sub_dup_actual == "Dupleta" else (st.session_state.carreras_habilitadas_tripleta if sub_dup_actual == "Tripleta" else st.session_state.carreras_habilitadas_polla)) if c in lista_carreras_disponibles]

    with st.container(border=True):
        st.markdown(f"👤 **Jugador:** `{st.session_state.usuario_activo}` &nbsp;|&nbsp; 💵 **Costo Ticket:** `{formatear_bs(monto_unico_seccion)}`")
        st.markdown("---")
        if not carreras_permitidas:
            st.warning(f"⚠️ No hay carreras habilitadas para **{sub_dup_actual}**.")
        else:
            seleccion_legs = []
            carreras_usadas = set()
            valido_legs = True
            cant_pasos = 2 if sub_dup_actual == "Dupleta" else (3 if sub_dup_actual == "Tripleta" else len(carreras_permitidas))

            for paso in range(cant_pasos):
                carr_leg = carreras_permitidas[paso % len(carreras_permitidas)]
                st.markdown(f"🔹 **Paso {paso + 1}** — 🏁 `{carr_leg}`")
                excl_carr_t = set(st.session_state.ejemplares_retirados.get(carr_leg, [])) | set(st.session_state.get('ejemplares_no_valido', {}).get(carr_leg, []))
                caballos_in_carr = [c for c in list(st.session_state.remates.get(carr_leg, {}).keys()) if c not in excl_carr_t]
                
                cab_leg = st.selectbox(f"Ejemplar para {carr_leg}", options=caballos_in_carr or ["Sin Disponibles"], key=f"t_cab_{sub_dup_actual}_{paso}")
                if carr_leg in carreras_usadas: valido_legs = False
                carreras_usadas.add(carr_leg)
                seleccion_legs.append({"carrera": carr_leg, "ejemplar": cab_leg})
                st.markdown("---")

            if st.button(f"🚀 Emitir Ticket de {sub_dup_actual}", key=f"btn_em_{sub_dup_actual}", use_container_width=True, type="primary"):
                if not valido_legs:
                    st.error("⚠️ No puedes repetir carreras en el mismo ticket.")
                else:
                    lista_tk = st.session_state.dupletas_tickets if sub_dup_actual == "Dupleta" else (st.session_state.tripleta_tickets if sub_dup_actual == "Tripleta" else st.session_state.polla_tickets)
                    pref = "DUP" if sub_dup_actual == "Dupleta" else ("TRIP" if sub_dup_actual == "Tripleta" else "6L")
                    t_id = f"{pref}-{len(lista_tk) + 1:04d}"
                    nuevo_t = {"id": t_id, "jugador": st.session_state.usuario_activo, "monto": monto_unico_seccion, "legs": seleccion_legs, "estado": "Pendiente", "fecha": ahora_dt.strftime('%d/%m %I:%M %p')}
                    lista_tk.append(nuevo_t)
                    if st.session_state.usuario_activo not in st.session_state.cuentas: st.session_state.cuentas[st.session_state.usuario_activo] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                    st.session_state.cuentas[st.session_state.usuario_activo]['Pujas'] += monto_unico_seccion
                    guardar_estado_global()
                    components.html("<script>window.parent.reproducirAlertaMovilYCalle('exito');</script>", height=0, width=0)
                    st.success(f"✅ ¡Ticket {t_id} emitido!")
                    st.rerun()

# =========================================================================
# 3. MÓDULO DE CUENTAS (COPIAR PAGO MÓVIL EN 1 TOQUE)
# =========================================================================
elif menu_principal_opcion == "Cuentas":
    st.markdown("<div class='subasta-header'>📊 Mis Cuentas y Reporte de Pago Móvil</div>", unsafe_allow_html=True)
    jugador_actual = st.session_state.usuario_activo
    st.markdown(f"👤 **Jugador en Sesión:** `{jugador_actual}`")

    if jugador_actual not in st.session_state.cuentas:
        st.session_state.cuentas[jugador_actual] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
    vals = st.session_state.cuentas[jugador_actual]
    neto_u = vals['Pujas'] - vals['Abonos'] - vals['Premios']

    col_cu1, col_cu2, col_cu3, col_cu4 = st.columns(4, gap="small")
    col_cu1.metric("🛒 Compras", formatear_bs(vals['Pujas']))
    col_cu2.metric("🏆 Premios", formatear_bs(vals['Premios']))
    col_cu3.metric("💳 Pagos", formatear_bs(vals['Abonos']))
    col_cu4.metric("⚖️ Neto", formatear_bs(neto_u))
    st.markdown("---")

    with st.container(border=True):
        st.markdown("📱 **1. Datos para Pago Móvil**")
        p_movil = st.session_state.datos_pago_movil
        
        st.markdown(f"""
            - 🏦 **Banco:** `{p_movil['banco']}`
            - 📱 **Teléfono:** `{p_movil['telefono']}`
            - 🆔 **Cédula/RIF:** `{p_movil['cedula']}`
        """)
        
        btn_copiar_html = f"""
            <button onclick="copiarPagoMovilUnico('{p_movil['banco']}', '{p_movil['telefono']}', '{p_movil['cedula']}')" style="background-color: #1f6feb; color: white; border: none; padding: 10px 16px; border-radius: 6px; font-weight: bold; cursor: pointer; width: 100%; margin-top: 8px;">
                📋 Copiar Datos de Pago Móvil (Todo en 1 Toque)
            </button>
        """
        components.html(btn_copiar_html, height=50)

    st.markdown("<br>", unsafe_allow_html=True)
    BANCOS_VENEZUELA = [
        "0102 - Banco de Venezuela", "0104 - Venezolano de Crédito", "0105 - Mercantil",
        "0108 - Provincial", "0114 - Bancaribe", "0115 - Exterior", "0128 - Banco Caroní",
        "0134 - Banesco", "0137 - Sofitasa", "0138 - Banco Plaza", "0151 - BFC Banco Fondo Común",
        "0156 - 100% Banco", "0157 - Del Sur", "0163 - Banco del Tesoro",
        "0169 - Mi Banco", "0171 - Banco Activo", "0172 - Bancamiga", "0174 - Banplus",
        "0175 - Bicentenario", "0177 - Banfanb", "0191 - BNC Nacional de Crédito"
    ]

    with st.container(border=True):
        st.markdown("📝 **2. Reportar un Pago Realizado**")
        with st.form(key="form_reportar_pago_jugador"):
            monto_rep = st.number_input("Monto Pagado (Bs.)", min_value=0.5, step=100.0)
            banco_remitente = st.selectbox("Banco Emisor", BANCOS_VENEZUELA)
            ref_pago = st.text_input("Últimos 4 dígitos o Referencia")
            if st.form_submit_button("📤 Enviar Reporte de Pago", use_container_width=True):
                if monto_rep > 0 and ref_pago:
                    st.session_state.reportes_pago.append({
                        "jugador": jugador_actual, "monto": monto_rep, "banco": banco_remitente,
                        "referencia": ref_pago, "fecha": ahora_dt.strftime('%d/%m/%Y %I:%M %p'), "estado": "Pendiente de Aprobación"
                    })
                    guardar_estado_global()
                    st.success("✅ ¡Reporte enviado!")
                    st.rerun()
                else:
                    st.error("⚠️ Complete los datos correctamente.")

# =========================================================================
# 4. ZONA DE ADMINISTRADOR
# =========================================================================
elif menu_principal_opcion == "🔒 Zona Admin":
    st.markdown("<div class='subasta-header'>🔒 Panel de Configuración y Administración</div>", unsafe_allow_html=True)
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["✍️ Caballos", "👥 Usuarios", "⚙️ Dupleta/6L", "📺 Video", "📊 Saldos", "🖼️ Imágenes"])

    with tab1:
        st.markdown("### ✍️ Configuración de Jornada y Carreras")
        with st.container(border=True):
            st.markdown("📅 **Número Total de Carreras de la Semana**")
            nueva_cantidad_carreras = st.number_input(
                "Cantidad de carreras:", min_value=1, max_value=25, 
                value=int(st.session_state.total_carreras_semana), step=1, key="input_total_carreras_semana"
            )
            if st.button("💾 Actualizar y Generar Carreras", key="btn_actualizar_cant_carreras", use_container_width=True, type="primary"):
                st.session_state.total_carreras_semana = nueva_cantidad_carreras
                nuevos_remates = {}
                nuevo_banco = {}
                nuevo_detalles = {}
                for i in range(1, int(nueva_cantidad_carreras) + 1):
                    c_n = f"Carrera {i}"
                    nuevo_banco[c_n] = [f"{j} - Ejemplar {j}" for j in range(1, 11)]
                    nuevos_remates[c_n] = {f"{j} - Ejemplar {j}": {"jugador": "Sin Postor", "monto": 0.0} for j in range(1, 11)}
                    nuevo_detalles[c_n] = st.session_state.detalles_carreras.get(c_n, {
                        "condicion": "Condición estándar", "distancia": "1200 mts", "hora": "02:00 PM", 
                        "monto_fijo_ciego": 500.0, "incentivo_adelantados": 0.0, "incentivo_ciegos": 0.0, "incentivo_envivo": 0.0, "hora_cierre_real": "No registrada"
                    })
                st.session_state.banco_caballos_por_carrera = nuevo_banco
                st.session_state.remates = nuevos_remates
                st.session_state.detalles_carreras = nuevo_detalles
                guardar_estado_global()
                st.toast(f"✅ ¡Jornada actualizada a {nueva_cantidad_carreras} carreras!")
                st.rerun()

        st.markdown("---")
        with st.container(border=True):
            st.markdown("🎯 **Asignación Independiente por Modalidad (Exclusiva)**")
            carr_existentes = list(st.session_state.remates.keys())
            mod_dict = st.session_state.carreras_por_modalidad

            def_adel = [c for c in mod_dict.get("Adelantados", []) if c in carr_existentes]
            def_ciego = [c for c in mod_dict.get("Ciegos", []) if c in carr_existentes]
            def_envivo = [c for c in mod_dict.get("En Vivo", []) if c in carr_existentes]

            sel_adel = st.multiselect("Adelantados", options=carr_existentes, default=def_adel, key="ms_carr_adelantados")
            sel_ciego = st.multiselect("Ciegos (Exactamente 2)", options=carr_existentes, default=def_ciego, key="ms_carr_ciegos")
            sel_envivo = st.multiselect("En Vivo", options=carr_existentes, default=def_envivo, key="ms_carr_envivo")

            if st.button("💾 Guardar Modalidades", key="btn_save_mod_ind", use_container_width=True, type="primary"):
                st.session_state.carreras_por_modalidad["Adelantados"] = sel_adel
                st.session_state.carreras_por_modalidad["Ciegos"] = sel_ciego
                st.session_state.carreras_por_modalidad["En Vivo"] = sel_envivo
                guardar_estado_global()
                st.toast("✅ ¡Modalidades guardadas!")
                st.rerun()

        st.markdown("---")
        carr_banco_sel = st.selectbox("Seleccionar Carrera para Editar Detalles", lista_carreras_disponibles, key="adm_banco_sel_carrera")
        det_actuales = st.session_state.detalles_carreras[carr_banco_sel]
        
        with st.container(border=True):
            edit_cond = st.text_input("Condición", value=det_actuales.get('condicion', ''), key=f"banco_cond_{carr_banco_sel}")
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1: edit_dist = st.text_input("Distancia", value=det_actuales.get('distancia', ''), key=f"banco_dist_{carr_banco_sel}")
            with col_b2: edit_hora = st.text_input("Hora", value=det_actuales.get('hora', ''), key=f"banco_hora_{carr_banco_sel}")
            with col_b3: edit_m_ciego = st.number_input("Monto Ciego", min_value=0.0, value=float(det_actuales.get('monto_fijo_ciego', 500.0)), key=f"banco_mc_{carr_banco_sel}")

            col_inc1, col_inc2, col_inc3 = st.columns(3)
            with col_inc1: edit_inc_adel = st.number_input("Incentivo Adelantados", min_value=0.0, value=float(det_actuales.get('incentivo_adelantados', 0.0)), key=f"banco_ia_{carr_banco_sel}")
            with col_inc2: edit_inc_ciegos = st.number_input("Incentivo Ciegos", min_value=0.0, value=float(det_actuales.get('incentivo_ciegos', 0.0)), key=f"banco_ic_{carr_banco_sel}")
            with col_inc3: edit_inc_envivo = st.number_input("Incentivo En Vivo", min_value=0.0, value=float(det_actuales.get('incentivo_envivo', 0.0)), key=f"banco_ie_{carr_banco_sel}")

            if st.button("💾 Guardar Detalles de Carrera", key=f"btn_save_det_{carr_banco_sel}", use_container_width=True, type="primary"):
                st.session_state.detalles_carreras[carr_banco_sel] = {
                    "condicion": edit_cond, "distancia": edit_dist, "hora": edit_hora, "monto_fijo_ciego": edit_m_ciego,
                    "incentivo_adelantados": edit_inc_adel, "incentivo_ciegos": edit_inc_ciegos, "incentivo_envivo": edit_inc_envivo,
                    "hora_cierre_real": det_actuales.get("hora_cierre_real", "No registrada")
                }
                guardar_estado_global()
                st.toast("✅ ¡Detalles guardados!")
                st.rerun()

        st.markdown("---")
        with st.container(border=True):
            st.markdown(f"⏰ **Control de Horarios por Modalidad ({carr_banco_sel})**")
            mod_h_sel = st.selectbox("Modalidad", ["Adelantados", "Ciegos", "En Vivo"], key=f"sel_mod_h_{carr_banco_sel}")
            clave_adm_h = f"{mod_h_sel}_{carr_banco_sel}"
            
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                f_i = st.date_input("Fecha Inicio", value=ahora_dt.date(), key=f"fi_{clave_adm_h}")
                hi_h = st.number_input("Hora (1-12)", min_value=1, max_value=12, value=2, key=f"hih_{clave_adm_h}")
                hi_m = st.number_input("Min (0-59)", min_value=0, max_value=59, value=0, key=f"him_{clave_adm_h}")
                hi_ap = st.selectbox("AM/PM", ["AM", "PM"], index=1, key=f"hiap_{clave_adm_h}")
            with col_h2:
                f_c = st.date_input("Fecha Cierre", value=ahora_dt.date(), key=f"fc_{clave_adm_h}")
                hc_h = st.number_input("Hora Cierre (1-12)", min_value=1, max_value=12, value=2, key=f"hch_{clave_adm_h}")
                hc_m = st.number_input("Min Cierre (0-59)", min_value=0, max_value=59, value=30, key=f"hcm_{clave_adm_h}")
                hc_ap = st.selectbox("AM/PM Cierre", ["AM", "PM"], index=1, key=f"hcap_{clave_adm_h}")

            if st.button(f"💾 Guardar Horarios", key=f"btn_sh_{clave_adm_h}", use_container_width=True, type="primary"):
                hi_24 = hi_h if hi_ap == "AM" else (hi_h + 12 if hi_h < 12 else 12)
                if hi_ap == "AM" and hi_h == 12: hi_24 = 0
                hc_24 = hc_h if hc_ap == "AM" else (hc_h + 12 if hc_h < 12 else 12)
                if hc_ap == "AM" and hc_h == 12: hc_24 = 0

                st.session_state.fechas_horas_inicio_remate_modalidad[clave_adm_h] = datetime.combine(f_i, dtime(hi_24, hi_m))
                st.session_state.fechas_horas_cierre_remate_modalidad[clave_adm_h] = datetime.combine(f_c, dtime(hc_24, hc_m))
                st.session_state.estado_conteo_carrera_modalidad[clave_adm_h] = "INACTIVO"
                guardar_estado_global()
                st.toast("✅ ¡Horarios guardados!")
                st.rerun()

    with tab2:
        st.markdown("### 👥 Usuarios")
        with st.container(border=True):
            nuevo_u = st.text_input("Nuevo Usuario", key="txt_nu")
            if st.button("➕ Registrar", key="btn_ru", type="primary"):
                u_limp = nuevo_u.strip().upper()
                if u_limp and u_limp not in st.session_state.lista_usuarios:
                    st.session_state.lista_usuarios.append(u_limp)
                    st.session_state.cuentas[u_limp] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                    guardar_estado_global()
                    st.rerun()
        for u in st.session_state.lista_usuarios:
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"👤 **{u}**")
            if u != "CASA" and c2.button("🗑️", key=f"du_{u}"):
                st.session_state.lista_usuarios.remove(u)
                if u in st.session_state.cuentas: del st.session_state.cuentas[u]
                guardar_estado_global()
                st.rerun()

    with tab3:
        st.markdown("### ⚙️ Dupleta y 6 En Línea")
        with st.container(border=True):
            m_dup = st.number_input("Dupleta (Bs.)", value=float(st.session_state.config_montos_especiales.get("Dupleta", 500.0)), key="cfg_md")
            m_trip = st.number_input("Tripleta (Bs.)", value=float(st.session_state.config_montos_especiales.get("Tripleta", 500.0)), key="cfg_mt")
            m_pol = st.number_input("6 En Línea (Bs.)", value=float(st.session_state.config_montos_especiales.get("6 En Linea", 1000.0)), key="cfg_mp")
            if st.button("💾 Guardar Montos", key="btn_sm", type="primary"):
                st.session_state.config_montos_especiales.update({"Dupleta": m_dup, "Tripleta": m_trip, "6 En Linea": m_pol})
                guardar_estado_global()
                st.rerun()

    with tab4:
        st.markdown("### 📺 Video en Vivo")
        with st.container(border=True):
            u_vid = st.text_input("URL YouTube", value=st.session_state.get('url_video_en_vivo', ''))
            if st.button("💾 Guardar Video", type="primary"):
                st.session_state.url_video_en_vivo = u_vid.strip()
                guardar_estado_global()
                st.rerun()

    with tab5:
        st.markdown("### 📊 Saldos y Pagos")
        with st.container(border=True):
            p_adm = st.session_state.datos_pago_movil
            n_b = st.text_input("Banco", value=p_adm['banco'])
            n_t = st.text_input("Teléfono", value=p_adm['telefono'])
            n_c = st.text_input("Cédula", value=p_adm['cedula'])
            if st.button("💾 Guardar Pago Móvil", type="primary"):
                st.session_state.datos_pago_movil = {'banco': n_b, 'telefono': n_t, 'cedula': n_c}
                guardar_estado_global()
                st.rerun()

        for idx_rep, rep in enumerate(reversed(st.session_state.reportes_pago)):
            with st.container(border=True):
                st.markdown(f"👤 **{rep['jugador']}** — 💰 **{formatear_bs(rep['monto'])}** (Ref: `{rep['referencia']}`)")
                if rep['estado'] == "Pendiente de Aprobación" and st.button("✅ Aprobar Pago", key=f"ap_{idx_rep}", type="primary"):
                    jug_r = rep['jugador']
                    if jug_r not in st.session_state.cuentas: st.session_state.cuentas[jug_r] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                    st.session_state.cuentas[jug_r]['Abonos'] += rep['monto']
                    rep['estado'] = "Aprobado"
                    guardar_estado_global()
                    st.rerun()

    with tab6:
        st.markdown("### 🖼️ Imágenes por Carrera")
        c_img = st.selectbox("Carrera", lista_carreras_disponibles, key="sel_ci")
        img_sub = st.file_uploader("Subir imagen", type=["png", "jpg", "jpeg"], key=f"fimg_{c_img}")
        if img_sub and st.button("💾 Guardar Imagen", type="primary"):
            st.session_state.imagenes_carreras[c_img] = f"data:image/jpeg;base64,{base64.b64encode(img_sub.getvalue()).decode('utf-8')}"
            guardar_estado_global()
            st.rerun()

# --- TRANSMISIÓN EN VIVO ---
url_live = st.session_state.get('url_video_en_vivo', '').strip()
if url_live:
    st.markdown("<br><hr style='border-color: #30363d;'>", unsafe_allow_html=True)
    st.markdown("### 📺 TRANSMISIÓN EN VIVO")
    yt_m = re.search(r'(?:v=|\/embed\/|youtu\.be\/|\/v\/|\/e\/|watch\?v=|&v=)([^#&?]{11})', url_live)
    try:
        st.video(f"https://www.youtube.com/embed/{yt_m.group(1)}?playsinline=1" if yt_m else url_live)
    except Exception:
        st.video(url_live)
