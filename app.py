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
from supabase import create_client, Client

# Configuración de pantalla completa optimizada para celulares
st.set_page_config(page_title="WOLF READY TO RUN", layout="wide", page_icon="🐺")

# --- CREDENCIALES DE SUPABASE (SEGURIZADAS CON SECRETS) ---
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://qssnhvwdgxzwzkfusstf.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_C4EDNCtB6i6yL84HDxw6tw_V5YGVmTQ")

@st.cache_resource
def init_supabase():
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        client.table("app_state").select("id").eq("id", 1).execute()
        return client
    except Exception as e:
        print("Error conectando a Supabase:", e)
        return None

supabase: Client = init_supabase()

if not supabase:
    st.error("⚠️ **ADVERTENCIA CRÍTICA:** No hay conexión con Supabase. Los datos entre la PC y los teléfonos no se sincronizarán. Verifica tus Secrets en Streamlit Cloud o la creación de la tabla `app_state` en Supabase.")

# --- CREDENCIALES Y CONFIGURACIÓN DE TELEGRAM ---
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "8969428136:AAFRhNzoAFB8TVAXUp2hnjffzw1gFPCyyrY")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "1111059746")
URL_DE_TU_APP = st.secrets.get("URL_DE_TU_APP", "https://tu-app.streamlit.app")

def enviar_notificacion_telegram_pago(reporte_idx, jugador, monto, banco, referencia):
    if not TELEGRAM_BOT_TOKEN:
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    mensaje = (
        f"💳 **¡NUEVO PAGO REPORTADO!** 💳\n\n"
        f"👤 **Jugador:** {jugador}\n"
        f"💰 **Monto:** {formatear_bs(monto)}\n"
        f"🏦 **Banco:** {banco}\n"
        f"📌 **Ref:** {referencia}\n\n"
        f"Haz clic abajo para ir directo a la Zona Admin:"
    )
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {
                        "text": "🔗 ABRIR PANEL DE PAGOS EN LA APP", 
                        "url": URL_DE_TU_APP
                    }
                ]
            ]
        }
    }
    
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Error enviando Telegram:", e)

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

# --- SISTEMA DE PERSISTENCIA Y SINCRONIZACIÓN EN TIEMPO REAL CON SUPABASE ---
DB_ROW_ID = 1

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
        'config_montos_especiales': {"Dupleta": 500.0, "Tripleta": 500.0, "POLLA HIPICA": 1000.0},
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
        'reportes_pago': [],
        'resultados_oficiales_polla': {},
        '_local_timestamp': 0.0
    }
    
    data = None
    if supabase:
        try:
            response = supabase.table("app_state").select("data").eq("id", DB_ROW_ID).execute()
            if response.data and len(response.data) > 0:
                data = response.data[0].get("data")
        except Exception as e:
            print("Error cargando de Supabase:", e)
            data = None

    if data and isinstance(data, dict) and len(data.keys()) > 0:
        try:
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
            
            if "_timestamp" in data:
                st.session_state["_local_timestamp"] = data.get("_timestamp", 0.0)
        except Exception:
            for k, v in default_state.items():
                if k not in st.session_state:
                    st.session_state[k] = v
    else:
        for k, v in default_state.items():
            if k not in st.session_state:
                st.session_state[k] = v
        guardar_estado_global()

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
        'datos_pago_movil', 'reportes_pago', 'resultados_oficiales_polla'
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
                
    current_ts = time.time()
    data["_timestamp"] = current_ts
    st.session_state["_local_timestamp"] = current_ts

    if supabase:
        try:
            supabase.table("app_state").upsert({"id": DB_ROW_ID, "data": data}).execute()
        except Exception as e:
            print("Error al guardar en Supabase: ", e)

cargar_estado_global()

# --- VIGILANTE GLOBAL DE SINCRONIZACIÓN OPTIMIZADO (4 SEGUNDOS PARA EVITAR PARPADEOS) ---
@st.fragment(run_every=4.0)
def vigilante_sincronizacion_global():
    if supabase:
        try:
            response = supabase.table("app_state").select("data").eq("id", DB_ROW_ID).execute()
            if response.data and len(response.data) > 0:
                remote_data = response.data[0].get("data", {})
                remote_ts = remote_data.get("_timestamp", 0.0)
                local_ts = st.session_state.get("_local_timestamp", 0.0)
                if remote_ts > local_ts:
                    st.session_state["_local_timestamp"] = remote_ts
                    st.rerun()
        except Exception:
            pass

vigilante_sincronizacion_global()

# --- SCRIPT JS PARA AUTO-ACTUALIZACIÓN, RELOJ, ALERTAS MÓVILES Y RESPONSIVIDAD MÓVIL ---
components.html(r"""
    <script>
        let audioCtxGlobal = null;

        function inicializarAudio() {
            if (!audioCtxGlobal) {
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                if (AudioContext) {
                    audioCtxGlobal = new AudioContext();
                }
            }
            if (audioCtxGlobal && audioCtxGlobal.state === 'suspended') {
                audioCtxGlobal.resume();
            }
        }

        window.addEventListener('click', inicializarAudio, { once: true });
        window.addEventListener('touchstart', inicializarAudio, { once: true });

        function reproducirAlertaMovilYCalle(tipo) {
            if ("vibrate" in navigator) {
                if (tipo === 'cierre') {
                    navigator.vibrate([200, 100, 200, 100, 400]);
                } else {
                    navigator.vibrate(300);
                }
            }

            try {
                inicializarAudio();
                if (!audioCtxGlobal) return;

                const osc = audioCtxGlobal.createOscillator();
                const gainNode = audioCtxGlobal.createGain();
                
                osc.connect(gainNode);
                gainNode.connect(audioCtxGlobal.destination);
                
                if (tipo === 'cierre' || tipo === 'tiempo') {
                    osc.type = 'square';
                    osc.frequency.setValueAtTime(587.33, audioCtxGlobal.currentTime);
                    osc.frequency.setValueAtTime(880, audioCtxGlobal.currentTime + 0.15);
                    gainNode.gain.setValueAtTime(0.5, audioCtxGlobal.currentTime);
                    gainNode.gain.exponentialRampToValueAtTime(0.0001, audioCtxGlobal.currentTime + 0.5);
                    osc.start();
                    osc.stop(audioCtxGlobal.currentTime + 0.5);
                } else if (tipo === 'exito') {
                    osc.type = 'triangle';
                    osc.frequency.setValueAtTime(523.25, audioCtxGlobal.currentTime);
                    osc.frequency.setValueAtTime(659.25, audioCtxGlobal.currentTime + 0.15);
                    gainNode.gain.setValueAtTime(0.4, audioCtxGlobal.currentTime);
                    gainNode.gain.exponentialRampToValueAtTime(0.0001, audioCtxGlobal.currentTime + 0.4);
                    osc.start();
                    osc.stop(audioCtxGlobal.currentTime + 0.4);
                }
            } catch (e) {
                console.log("Audio no disponible: ", e);
            }
        }
        window.reproducirAlertaMovilYCalle = reproducirAlertaMovilYCalle;

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
                tuercaBtn.title = 'Abrir / Cerrar Menú';
                
                tuercaBtn.style.position = 'fixed';
                tuercaBtn.style.top = '8px';
                tuercaBtn.style.right = '10px';
                tuercaBtn.style.zIndex = '99999';
                tuercaBtn.style.background = '#161b22';
                tuercaBtn.style.border = '1px solid #30363d';
                tuercaBtn.style.borderRadius = '8px';
                tuercaBtn.style.fontSize = '18px';
                tuercaBtn.style.width = '38px';
                tuercaBtn.style.height = '38px';
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
                            sidebar.style.minWidth = '290px';
                            sidebar.style.width = '290px';
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
    logo_display = '<span style="color: #f1c40f; font-size: 28px; font-weight: 900; font-style: italic; letter-spacing: 1.5px;">WOLF READY TO RUN</span>'

# --- INICIALIZAR REMATES Y LISTA DE CARRERAS DISPONIBLES PRIMERO ---
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

# --- REGLA: AUTOMÁTICAMENTE LAS ÚLTIMAS 6 CARRERAS CONSECUTIVAS PARA POLLA HÍPICA ---
total_carrs = st.session_state.get('total_carreras_semana', len(lista_carreras_disponibles))
inicio_polla_idx = max(1, total_carrs - 5)
ultimas_6_carreras = [f"Carrera {i}" for i in range(inicio_polla_idx, total_carrs + 1)]
st.session_state.carreras_habilitadas_polla = [c for c in ultimas_6_carreras if c in lista_carreras_disponibles]

ahora_dt = obtener_hora_venezuela_local()

# --- ESTILOS CSS GENERALES OPTIMIZADOS PARA TELÉFONOS MÓVILES ---
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
    @media (max-width: 768px) {
        [data-testid="stSidebar"] {
            min-width: 280px !important;
            max-width: 280px !important;
        }
        [data-testid="stSidebar"] > div:first-child {
            width: 280px !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }
    }
    @media (min-width: 769px) {
        [data-testid="stSidebar"] {
            min-width: 340px !important;
            max-width: 340px !important;
        }
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
    .block-container {
        padding-top: 0.2rem !important;
        padding-bottom: 1.5rem !important;
        padding-left: 0.3rem !important;
        padding-right: 0.3rem !important;
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
        gap: 4px !important;
        padding-bottom: 4px !important;
        scrollbar-width: thin;
    }
    div[data-testid="stHorizontalBlock"] > div {
        flex: 0 0 auto !important;
        width: auto !important;
        min-width: 90px !important;
        max-width: none !important;
    }
    .carreras-scroll-container div[data-testid="stHorizontalBlock"] > div {
        min-width: 48px !important;
        width: 48px !important;
    }
    
    div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"]:has(button) {
        gap: 3px !important;
        margin-top: -12px !important;
        margin-bottom: -12px !important;
    }
    div[data-testid="column"]:has(button) {
        padding: 0px 1px !important;
    }

    .stButton button {
        border-radius: 8px !important;
        font-weight: 800 !important;
        padding: 0.4rem 0.6rem !important;
        min-height: 42px !important;
        font-size: 12px !important;
        letter-spacing: 0.3px;
        white-space: nowrap !important;
        width: 100% !important;
    }
    
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #f1c40f 0%, #d4ac0d 100%) !important;
        color: #080a0f !important;
        font-size: 15px !important;
        font-weight: 900 !important;
        border: 2px solid #ffffff !important;
        box-shadow: 0px 4px 18px rgba(241, 196, 15, 0.6) !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button[kind="primary"]:hover {
        transform: scale(1.02);
        box-shadow: 0px 6px 22px rgba(241, 196, 15, 0.9) !important;
    }

    .subasta-header {
        font-size: clamp(13px, 3.2vw, 16px);
        font-weight: 800;
        color: #f1e05a;
        margin-bottom: 4px;
        border-bottom: 2px solid #f1e05a;
        padding-bottom: 2px;
    }
    
    .carrera-condicion-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 8px 10px;
        border-radius: 6px;
        font-size: 11px;
        color: #f0f6fc;
        margin-bottom: 8px;
        line-height: 1.3;
        word-break: break-word;
    }
    
    .incentivo-llamativo {
        background: linear-gradient(135deg, #1f1c2c 0%, #923d41 100%);
        border: 2px dashed #00ffff;
        padding: 12px 14px;
        border-radius: 12px;
        text-align: center;
        margin: 8px 0;
        box-shadow: 0px 0px 18px rgba(0, 255, 255, 0.4);
        width: 100%;
        box-sizing: border-box;
    }
    .incentivo-llamativo-monto {
        color: #ffffff;
        font-size: clamp(18px, 5vw, 24px);
        font-weight: 900;
        letter-spacing: 0.8px;
        text-shadow: 2px 2px 6px #000000, 0 0 12px rgba(0, 255, 255, 0.8);
        word-break: break-word;
    }

    .pote-cyber-card {
        background: linear-gradient(135deg, #0d1b2a 0%, #1b263b 100%);
        border: 2px solid #f1c40f;
        border-radius: 10px;
        padding: 10px 12px;
        text-align: center;
        margin: 4px 0;
        box-shadow: 0px 0px 15px rgba(241, 196, 15, 0.3);
        width: 100%;
        box-sizing: border-box;
    }
    .pote-cyber-title {
        color: #00ffff;
        font-size: 10px;
        font-weight: 900;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 3px;
        text-shadow: 0 0 6px rgba(0, 255, 255, 0.6);
    }
    .pote-cyber-value {
        color: #f1c40f;
        font-size: clamp(15px, 4vw, 20px);
        font-weight: 900;
        text-shadow: 2px 2px 5px #000000, 0 0 10px rgba(241, 196, 15, 0.8);
        word-break: break-word;
    }
    
    @keyframes parpadeoGanador {
        0% { transform: scale(1); box-shadow: 0 0 12px #f1c40f, inset 0 0 12px #f1c40f; }
        50% { transform: scale(1.02); box-shadow: 0 0 25px #00ffff, inset 0 0 18px #00ffff; }
        100% { transform: scale(1); box-shadow: 0 0 12px #f1c40f, inset 0 0 12px #f1c40f; }
    }
    .ganador-banner-epic {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border: 2px solid #f1c40f;
        border-radius: 12px;
        padding: 12px;
        text-align: center;
        margin: 10px 0;
        animation: parpadeoGanador 2s infinite ease-in-out;
    }
    .ganador-titulo-epic {
        color: #00ffff;
        font-size: 12px;
        font-weight: 900;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 4px;
        text-shadow: 0 0 6px rgba(0, 255, 255, 0.8);
    }
    .ganador-nombre-epic {
        color: #f1c40f;
        font-size: 20px;
        font-weight: 900;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        margin-bottom: 3px;
        text-shadow: 2px 2px 5px #000000, 0 0 10px rgba(241, 196, 15, 0.8);
    }
    .ganador-premio-epic {
        color: #2ed573;
        font-size: 15px;
        font-weight: 900;
        text-shadow: 1px 1px 3px #000000;
    }

    .ticket-jugador-card {
        background: #0d1117;
        border: 2px solid #30363d;
        border-radius: 8px;
        padding: 10px 12px;
        margin-bottom: 8px;
        box-shadow: 0px 3px 10px rgba(0,0,0,0.5);
    }
    .ticket-header-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px dashed #30363d;
        padding-bottom: 4px;
        margin-bottom: 6px;
        font-size: 11px;
        font-weight: 800;
        color: #f1c40f;
    }
    .ticket-body-row {
        font-size: 12px;
        color: #f0f6fc;
        margin-bottom: 3px;
        font-weight: 600;
    }
    
    .header-container-modern {
        background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 8px;
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.5);
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
        gap: 6px;
    }
    .header-user-card {
        display: flex;
        align-items: center;
        gap: 8px;
        background: #080a0f;
        border: 1px solid #30363d;
        padding: 4px 10px;
        border-radius: 6px;
    }
    .user-details {
        display: flex;
        flex-direction: column;
        text-align: right;
    }
    .u-name-container {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 4px;
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
        width: 30px;
        height: 30px;
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
        max-height: 95px;
        width: auto;
        object-fit: contain;
    }
    
    .reloj-digital-container {
        background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
        border: 1.2px solid #00ffff;
        border-radius: 8px;
        padding: 6px 14px;
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 10px;
        box-shadow: 0px 0px 12px rgba(0, 255, 255, 0.25);
    }
    .reloj-digital-txt {
        color: #00ffff;
        font-size: 16px;
        font-weight: 900;
        letter-spacing: 1.5px;
        text-shadow: 0 0 8px rgba(0, 255, 255, 0.8);
        font-family: monospace;
    }
    
    @keyframes parpadeoLed {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(0.9); }
        100% { opacity: 1; transform: scale(1); }
    }
    .led-estado {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 6px currentColor;
    }
    .led-verde {
        background-color: #2ed573;
        color: #2ed573;
        animation: parpadeoLed 1.5s infinite ease-in-out;
    }
    .led-rojo {
        background-color: #ff4757;
        color: #ff4757;
    }

    @media (min-width: 769px) {
        .imagen-carrera-pc-container {
            max-width: 380px !important;
            margin: 0 auto !important;
            display: block !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

usuario_en_sesion = st.session_state.usuario_activo
if usuario_en_sesion not in st.session_state.cuentas:
    st.session_state.cuentas[usuario_en_sesion] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}

vals_sesion = st.session_state.cuentas[usuario_en_sesion]
pujas_usu = vals_sesion['Pujas']
premios_usu = vals_sesion['Premios']
abonos_usu = vals_sesion['Abonos']
neto_usuario = pujas_usu - abonos_usu - premios_usu

if neto_usuario > 0:
    etiqueta_balance = f"Deuda: {formatear_bs(neto_usuario)}"
    color_balance = "#ff4757"
elif neto_usuario < 0:
    etiqueta_balance = f"Premio: {formatear_bs(abs(neto_usuario))}"
    color_balance = "#2ed573"
else:
    etiqueta_balance = "Al día: Bs. 0,00"
    color_balance = "#58a6ff"

# --- CABECERA SUPERIOR MODERNA ---
estado_global_remate = "cerrados" if all(st.session_state.carreras_cerradas_remate.get(c, False) for c in lista_carreras_disponibles) and lista_carreras_disponibles else "abiertos"
led_clase_css = "led-rojo" if estado_global_remate == "cerrados" else "led-verde"

if supabase:
    st.sidebar.success("🟢 Base de datos sincronizada")
else:
    st.sidebar.error("🔴 Sin conexión a Supabase")

col_h_izq, col_h_der = st.columns([1, 1], gap="small")
with col_h_izq:
    if st.button("💳 Reportar Pago Móvil", key="btn_ir_reportar_pago_top", use_container_width=True, type="primary"):
        st.session_state.menu_principal_opcion = "Cuentas"
        guardar_estado_global()
        st.rerun()

header_html = f"""
    <div class="header-container-modern" style="margin-top: 4px;">
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
        <div class="header-bottom-row-logo">
            {logo_display}
        </div>
    </div>
"""
st.markdown(header_html, unsafe_allow_html=True)

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
        .tabla-referencia {
            width: 100%;
            border-collapse: collapse;
            font-family: sans-serif;
            background-color: #ffffff;
            color: #000000;
            margin-bottom: 8px;
            table-layout: fixed;
        }
        .tabla-referencia th {
            border-top: 2px solid #dfc729;
            border-bottom: 2px solid #dfc729;
            padding: 5px 3px;
            text-align: left;
            font-weight: 800;
            background-color: #ffffff;
            color: #000000;
            font-size: 10px;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .tabla-referencia td {
            border-bottom: 1px solid #dfc729;
            padding: 5px 3px;
            background-color: #fbfbfb;
            color: #111111;
            font-size: 10px;
            vertical-align: middle;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .badge-numero {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 18px;
            height: 18px;
            font-weight: bold;
            font-size: 10px;
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
    <div style="background-color: #ffffff; padding: 2px; border-radius: 6px; overflow-x: auto; width: 100%;">
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
                    <td style="font-weight: 800; font-size: 11px;" title="{nombre_solo.upper()}{etiqueta_estado}">{nombre_solo.upper()}{etiqueta_estado}</td>
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

# --- GARANTIZAR ESTADO INICIAL DE MODALIDADES ---
if not st.session_state.carreras_activas_remate and lista_carreras_disponibles:
    st.session_state.carreras_activas_remate = list(lista_carreras_disponibles)

for mod in ["Adelantados", "Ciegos", "En Vivo"]:
    if mod not in st.session_state.carreras_por_modalidad:
        st.session_state.carreras_por_modalidad[mod] = []

if not st.session_state.carreras_habilitadas_dupleta and lista_carreras_disponibles:
    st.session_state.carreras_habilitadas_dupleta = list(lista_carreras_disponibles)
if not st.session_state.carreras_habilitadas_tripleta and lista_carreras_disponibles:
    st.session_state.carreras_habilitadas_tripleta = list(lista_carreras_disponibles)

# --- MENÚ PRINCIPAL HORIZONTAL ---
st.markdown('<div class="carrusel-horizontal-box">', unsafe_allow_html=True)
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

st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<hr style='margin: 0.2rem 0; border-color: #21262d;'>", unsafe_allow_html=True)

# --- BANNER MARQUESINA DINÁMICO ---
elementos_carrusel_info = []

carreras_adelantados = [c for c in st.session_state.carreras_por_modalidad.get("Adelantados", []) if c in lista_carreras_disponibles]
if carreras_adelantados:
    elementos_carrusel_info.append("ADELANTADOS: " + " | ".join(carreras_adelantados))

carreras_ciegos = [c for c in st.session_state.carreras_por_modalidad.get("Ciegos", []) if c in lista_carreras_disponibles]
if carreras_ciegos:
    elementos_carrusel_info.append("CIEGOS: " + " | ".join(carreras_ciegos))

carreras_envivo = [c for c in st.session_state.carreras_por_modalidad.get("En Vivo", []) if c in lista_carreras_disponibles]
if carreras_envivo:
    elementos_carrusel_info.append("🔴 EN VIVO: " + " | ".join(carreras_envivo))

carreras_dupleta = [c for c in st.session_state.carreras_habilitadas_dupleta if c in lista_carreras_disponibles]
if carreras_dupleta:
    elementos_carrusel_info.append("DUPLETA: " + " | ".join(carreras_dupleta))

carreras_tripleta = [c for c in st.session_state.carreras_habilitadas_tripleta if c in lista_carreras_disponibles]
if carreras_tripleta:
    elementos_carrusel_info.append("TRIPLETA: " + " | ".join(carreras_tripleta))

if not elementos_carrusel_info:
    elementos_carrusel_info.append("⏳ CONFIGURA LAS CARRERAS ASIGNADAS EN LA ZONA ADMIN")

texto_unido_marquesina = " &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ".join(elementos_carrusel_info)
html_banner_marquesina = f"""
<style>
    .marquee-container {{
        width: 100%;
        background: transparent;
        border: none;
        box-shadow: none;
        padding: 6px 0;
        margin-bottom: 8px;
        overflow: hidden;
        box-sizing: border-box;
        display: flex;
        align-items: center;
    }}
    .marquee-text {{
        display: inline-block;
        white-space: nowrap;
        animation: scrollRight 150s linear infinite !important;
        animation-play-state: running !important;
        font-family: 'Arial Black', Gadget, sans-serif;
        font-size: 13px;
        font-weight: 900;
        color: #00ffff;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        text-shadow: 0px 0px 8px rgba(0, 255, 255, 0.9), 2px 2px 2px #000000;
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
</style>
<div class="marquee-container">
    <div class="marquee-text">{texto_unido_marquesina}</div>
</div>
"""
components.html(html_banner_marquesina, height=36)

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
        .banner-slider-container {{ width: 100vw; height: 180px; margin: 0; padding: 0; overflow: hidden; position: relative; background-color: #080a0f; }}
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
                    }, 400);
                }}, 8000);
            }}
        }})();
    </script>
    """
    components.html(html_slider, height=185)
else:
    st.markdown("""
        <div style="background: linear-gradient(90deg, #11141d 0%, #1f2937 100%); padding: 12px; text-align: center; margin-bottom: 8px; border-radius: 6px;">
            <h3 style="color: #f1c40f; margin: 0; font-weight: 900; letter-spacing: 1px; font-size: 14px;">INH - HIPÓDROMO DE LA RINCONADA</h3>
            <p style="color: #8b949e; font-size: 10px; margin: 3px 0 0 0;">¡La pasión del hipismo venezolano en vivo!</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- BARRA LATERAL ---
st.sidebar.header("barra lateral")
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

with st.sidebar.expander("🔒 Estado Dupletas / Polla Hípica", expanded=False):
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
    keys_excluidos = [
        'banco_caballos_por_carrera', 
        'lista_usuarios', 
        'datos_pago_movil', 
        'reportes_pago', 
        'cuentas'
    ]
    for key in list(st.session_state.keys()):
        if key not in keys_excluidos:
            del st.session_state[key]
    guardar_estado_global()
    st.toast("🚨 Jornada reiniciada.")
    st.rerun()

menu_principal_opcion = st.session_state.menu_principal_opcion

# =========================================================================
# BLOQUE FRAGMENTADO UNIVERSAL EN TIEMPO REAL (OPTIMIZADO PARA EVITAR PARPADEOS)
# =========================================================================
@st.fragment(run_every=2.0)
def renderizar_tiempo_real_universal():
    cargar_estado_global(forzar_recarga=True)
    ahora_dt_frag = obtener_hora_venezuela_local()

    # --- DETECCIÓN DE SUPERACIÓN DE PUJA (OUTBID NOTIFICATION) ---
    if 'mis_caballos_previos' not in st.session_state:
        st.session_state.mis_caballos_previos = {}
    
    usuario_actual = st.session_state.usuario_activo
    for carr_k, rems in st.session_state.remates.items():
        for ej_k, info in rems.items():
            clave_cab = f"{carr_k}_{ej_k}"
            dueño_anterior = st.session_state.mis_caballos_previos.get(clave_cab)
            dueño_actual = info['jugador']
            if dueño_anterior == usuario_actual and dueño_actual != usuario_actual and dueño_actual != "Sin Postor":
                st.toast(f"⚠️ ¡Te superaron la puja en el ejemplar **{ej_k}** ({carr_k}) por {formatear_bs(info['monto'])}!", icon="🚨")
            st.session_state.mis_caballos_previos[clave_cab] = dueño_actual

    if st.session_state.menu_principal_opcion == "Remates":
        st.markdown('<div class="carrusel-horizontal-box">', unsafe_allow_html=True)
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
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<hr style='margin: 0.2rem 0; border-color: #21262d;'>", unsafe_allow_html=True)
        modo_actual_remate = st.session_state.sub_remate_opcion

        if not lista_carreras_disponibles:
            st.warning("⚠️ No hay carreras cargadas en el sistema.")
        else:
            carreras_asignadas_admin = st.session_state.carreras_por_modalidad.get(modo_actual_remate, [])
            
            if modo_actual_remate == "Ciegos":
                carreras_filtradas_visibles = [c for c in carreras_asignadas_admin if c in lista_carreras_disponibles][:2]
            else:
                carreras_filtradas_visibles = [
                    c for c in lista_carreras_disponibles 
                    if c in carreras_asignadas_admin and ((c in st.session_state.carreras_activas_remate) or st.session_state.carreras_cerradas_remate.get(c, False))
                ]
            
            if not carreras_filtradas_visibles:
                if modo_actual_remate == "Ciegos":
                    st.info("ℹ️ El Remate Ciego requiere exactamente dos carreras asignadas en la Zona Admin (1V y 6V).")
                else:
                    st.info(f"ℹ️ No hay carreras asignadas o habilitadas para la modalidad **{modo_actual_remate}**. Configúralas en Zona Admin.")
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

                hora_actual_envivo = ahora_dt_frag.strftime('%I:%M:%S %p')
                st.markdown(f"""
                    <div class="reloj-digital-container">
                        <span id="reloj-js-vivo" class="reloj-digital-txt">{hora_actual_envivo}</span>
                    </div>
                """, unsafe_allow_html=True)

                if carr_activa in st.session_state.imagenes_carreras:
                    try:
                        img_url_val = st.session_state.imagenes_carreras[carr_activa]
                        st.markdown(f'<div class="imagen-carrera-pc-container">', unsafe_allow_html=True)
                        st.image(img_url_val, caption=f"Imagen oficial - {carr_activa}", use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    except Exception:
                        pass

                carrera_cerrada = st.session_state.carreras_cerradas_remate.get(carr_activa, False)
                estado_icono = "🔴" if carrera_cerrada else "🟢"
                
                st.markdown(f"""
                    <div style="font-size: 13px; font-weight: 800; color: #f0f6fc; display: flex; align-items: center; gap: 6px; margin-top: 6px; margin-bottom: 6px;">
                        <span>{estado_icono}</span>
                        <span>{carr_activa}</span>
                        <span style="font-size: 10px; font-weight: 600; color: #8b949e; background: #161b22; padding: 1px 5px; border-radius: 4px; border: 1px solid #30363d;">{modo_actual_remate}</span>
                    </div>
                """, unsafe_allow_html=True)

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

                # --- ⏱️ CONTROL DE HORARIOS Y CONTEO EN VIVO ---
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
                    st.markdown(f"<div style='background:#161b22; padding:5px; border-radius:5px; margin-bottom:3px; border:1px solid #30363d; font-size:11px;'>🟢 Inicio Remate ({modo_actual_remate}): <b>{dt_inicio.strftime('%d/%m/%Y - %I:%M %p')}</b></div>", unsafe_allow_html=True)
                if dt_limite:
                    st.markdown(f"<div style='background:#161b22; padding:5px; border-radius:5px; margin-bottom:6px; border:1px solid #30363d; font-size:11px;'>⏰ Cierre Estricto ({modo_actual_remate}): <b>{dt_limite.strftime('%d/%m/%Y - %I:%M %p')}</b></div>", unsafe_allow_html=True)

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
                                st.toast(f"⏳ ¡ATENCIÓN! Faltan {txt_tiempo} para el cierre de {carr_activa} ({modo_actual_remate})", icon="🚨")
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
                            st.session_state.detalles_carreras[carr_activa]["hora_cierre_real"] = ahora_dt_frag.strftime('%I:%M:%S %p')
                            guardar_estado_global()
                            st.rerun()
                    elif estado_conteo == "CONTEO_10S":
                        tiempo_inicio = st.session_state.tiempo_inicio_conteo_modalidad.get(clave_mod_carr, ahora_dt_frag)
                        transcurridos = (ahora_dt_frag - tiempo_inicio).total_seconds()
                        
                        if transcurridos >= 10:
                            st.session_state.carreras_cerradas_remate[carr_activa] = True
                            st.session_state.estado_conteo_carrera_modalidad[clave_mod_carr] = "CERRADO"
                            st.session_state.detalles_carreras[carr_activa]["hora_cierre_real"] = ahora_dt_frag.strftime('%I:%M:%S %p')
                            guardar_estado_global()
                            st.rerun()
                        else:
                            restantes_10s = max(0, 10 - int(transcurridos))
                            if restantes_10s > 0:
                                html_anuncio_movil = f"""
                                <div style="position: sticky; top: 0px; z-index: 999999; width: 100%; background: linear-gradient(135deg, #2b0909 0%, #161b22 100%); border: 3px solid #ff4757; border-radius: 8px; padding: 6px 10px; text-align: center; box-shadow: 0px 4px 15px rgba(255, 71, 87, 0.6); margin-bottom: 8px;">
                                    <div style="color: #ff4757; font-size: 10px; font-weight: 900; letter-spacing: 1px; text-transform: uppercase;">⚠️ CIERRE INMINENTE ⚠️</div>
                                    <div id="cuenta-atras-vivo" style="color: #00ffff; font-size: 28px; font-weight: 900; font-family: monospace; letter-spacing: 2px; text-shadow: 0 0 10px rgba(0, 255, 255, 0.9);">{restantes_10s}</div>
                                    <div style="color: #f1c40f; font-size: 9px; font-weight: 700; text-transform: uppercase;">SEGUNDOS (Nuevas pujas reinician)</div>
                                </div>
                                <script>
                                    (function() {{
                                        let segs = {restantes_10s};
                                        const digito = document.getElementById("cuenta-atras-vivo");
                                        if (window.intervaloRelojVivo) {{
                                            clearInterval(window.intervaloRelojVivo);
                                        }}
                                        window.intervaloRelojVivo = setInterval(function() {{
                                            segs--;
                                            if (segs > 0) {{
                                                if (digito) digito.innerText = segs;
                                            }} else {{
                                                if (digito) {{
                                                    digito.parentElement.style.borderColor = "#f1c40f";
                                                    digito.parentElement.style.background = "linear-gradient(135deg, #3d3100 0%, #161b22 100%)";
                                                    digito.parentElement.innerHTML = "<div style='color: #f1c40f; font-size: 14px; font-weight: 900; text-transform: uppercase; text-shadow: 0 0 6px #f1c40f; padding: 4px;'>🔒 ¡CERRADO EL REMATE, SUERTE! 🐎</div>";
                                                }}
                                                clearInterval(window.intervaloRelojVivo);
                                            }}
                                        }}, 1000);
                                    }})();
                                </script>
                                """
                                components.html(html_anuncio_movil, height=75)

                if carrera_cerrada:
                    components.html("""
                        <div style="position: sticky; top: 0px; z-index: 999999; width: 100%; background: linear-gradient(135deg, #3d3100 0%, #161b22 100%); border: 3px solid #f1c40f; border-radius: 8px; padding: 8px; text-align: center; box-shadow: 0px 4px 15px rgba(241, 196, 15, 0.4); margin-bottom: 8px;">
                            <div style="color: #f1c40f; font-size: 15px; font-weight: 900; text-transform: uppercase; text-shadow: 0 0 8px #f1c40f;">🔒 ¡CERRADO EL REMATE, SUERTE! 🐎</div>
                        </div>
                    """, height=48)

                if carr_activa not in st.session_state.ejemplares_retirados:
                    st.session_state.ejemplares_retirados[carr_activa] = []
                if 'ejemplares_no_valido' not in st.session_state:
                    st.session_state.ejemplares_no_valido = {}
                if carr_activa not in st.session_state.ejemplares_no_valido:
                    st.session_state.ejemplares_no_valido[carr_activa] = []

                # --- ⚙️ GESTIÓN DE RETIROS DESPLEGABLE (EN REMATES) ---
                with st.expander(f"⚙️ Gestionar Retiros / No Válidos - {carr_activa}", expanded=False):
                    banco_carr_rem = st.session_state.banco_caballos_por_carrera.get(carr_activa, [])
                    ret_act = st.session_state.ejemplares_retirados.get(carr_activa, [])
                    noval_act = st.session_state.ejemplares_no_valido.get(carr_activa, [])
                    
                    n_ret = st.multiselect("Ejemplares Retirados", options=banco_carr_rem, default=[c for c in ret_act if c in banco_carr_rem], key=f"quick_ret_{carr_activa}")
                    n_noval = st.multiselect("Ejemplares No Valen", options=banco_carr_rem, default=[c for c in noval_act if c in banco_carr_rem], key=f"quick_noval_{carr_activa}")
                    
                    if st.button("💾 Guardar Cambios en Ejemplares", key=f"btn_quick_gestion_{carr_activa}", use_container_width=True, type="primary"):
                        st.session_state.ejemplares_retirados[carr_activa] = n_ret
                        st.session_state.ejemplares_no_valido[carr_activa] = n_noval
                        guardar_estado_global()
                        st.toast("✅ ¡Estado de ejemplares actualizado!")
                        st.rerun()

                # --- TABLA DE REMATES ---
                retirados_carr_activa = st.session_state.ejemplares_retirados.get(carr_activa, [])
                no_validos_carr_activa = st.session_state.ejemplares_no_valido.get(carr_activa, [])
                
                tabla_html = generar_tabla_html_remate(st.session_state.remates[carr_activa], retirados_carr_activa, no_validos_carr_activa)
                cantidad_filas = len(st.session_state.remates[carr_activa])
                altura_dinamica = min(max(130, (cantidad_filas * 32) + 45), 380)
                components.html(tabla_html, height=altura_dinamica, scrolling=True)
                
                excluidos_carr_activa = set(retirados_carr_activa) | set(no_validos_carr_activa)

                total_pote = sum([info['monto'] for cab_n, info in st.session_state.remates[carr_activa].items() if cab_n not in excluidos_carr_activa])
                monto_casa = total_pote * (porcentaje_casa / 100)
                pote_neto_base = total_pote - monto_casa

                if modo_actual_remate == "Adelantados":
                    incentivo_actual = float(detalles_carr.get('incentivo_adelantados', 0.0))
                elif modo_actual_remate == "Ciegos":
                    incentivo_actual = float(detalles_carr.get('incentivo_ciegos', 0.0))
                else:
                    incentivo_actual = float(detalles_carr.get('incentivo_envivo', 0.0))

                premio_total_calculado = pote_neto_base + incentivo_actual

                # --- 1. PREMIO TOTAL LLAMATIVO (ARRIBA) ---
                if incentivo_actual > 0 or premio_total_calculado > 0:
                    st.markdown(f"""
                        <div class="incentivo-llamativo">
                            <div style="font-size: 11px; font-weight: 900; color: #00ffff; text-transform: uppercase; margin-bottom: 3px; letter-spacing: 1px;">🎁 PREMIO TOTAL (INCLUYE INCENTIVO)</div>
                            <div class="incentivo-llamativo-monto">{formatear_bs(premio_total_calculado)}</div>
                        </div>
                    """, unsafe_allow_html=True)

                # --- 2. INCENTIVO (IZQUIERDA) Y POTE (DERECHA) ---
                col_m1, col_m2 = st.columns(2, gap="small")
                with col_m1:
                    st.markdown(f"""
                        <div class="pote-cyber-card">
                            <div class="pote-cyber-title" style="color: #2ed573;">🎁 INCENTIVO</div>
                            <div class="pote-cyber-value" style="color: #2ed573;">{formatear_bs(incentivo_actual)}</div>
                        </div>
                    """, unsafe_allow_html=True)
                with col_m2:
                    st.markdown(f"""
                        <div class="pote-cyber-card">
                            <div class="pote-cyber-title">💰 POTE ({carr_activa})</div>
                            <div class="pote-cyber-value">{formatear_bs(total_pote)}</div>
                        </div>
                    """, unsafe_allow_html=True)

                if carr_activa in st.session_state.historial_ganadores:
                    info_ganador_prev = st.session_state.historial_ganadores[carr_activa]
                    ganador_nombre = info_ganador_prev.get('Ganador', 'N/A')
                    premio_ganado = info_ganador_prev.get('Premio', '0')
                    caballo_ganador_str = info_ganador_prev.get('Caballo', 'N/A')

                    st.markdown(f"""
                        <div class="ganador-banner-epic">
                            <div class="ganador-titulo-epic">🏆 ¡RESULTADO OFICIAL - {carr_activa.upper()}! 🏆</div>
                            <div class="ganador-nombre-epic">🎉 {ganador_nombre} 🎉</div>
                            <div style="color: #00ffff; font-size: 14px; font-weight: 900; margin-bottom: 3px; text-shadow: 0 0 6px rgba(0,255,255,0.7);">🐎 EJEMPLAR: {caballo_ganador_str.upper()}</div>
                            <div class="ganador-premio-epic">💰 Premio Liquidado: {premio_ganado}</div>
                        </div>
                    """, unsafe_allow_html=True)

                if modo_actual_remate == "Adelantados":
                    with st.expander(f"🏆 Seleccionar y Liquidar Ganador - {carr_activa}", expanded=False):
                        if carr_activa not in st.session_state.historial_ganadores:
                            caballos_lista_ganador = [c for c in list(st.session_state.remates[carr_activa].keys()) if c not in excluidos_carr_activa]
                            if not caballos_lista_ganador:
                                caballos_lista_ganador = list(st.session_state.remates[carr_activa].keys())
                            col_g1, col_g2 = st.columns([3, 2], gap="small")
                            with col_g1:
                                caballo_ganador_elegido = st.selectbox("Ejemplar Ganador", caballos_lista_ganador, key=f"rem_sel_ganador_{carr_activa}", label_visibility="collapsed")
                            with col_g2:
                                if st.button("🏆 Liquidar Ganador", key=f"rem_btn_liquidar_{carr_activa}", use_container_width=True, type="primary"):
                                    pote_carr_total = sum([info['monto'] for cab_n, info in st.session_state.remates[carr_activa].items() if cab_n not in excluidos_carr_activa])
                                    monto_casa_calc = pote_carr_total * (porcentaje_casa / 100)
                                    
                                    incentivo_establecido = float(detalles_carr.get('incentivo_adelantados', 0.0))
                                    premio_final_liq = pote_carr_total - monto_casa_calc + incentivo_establecido
                                    
                                    info_g = st.session_state.remates[carr_activa][caballo_ganador_elegido]
                                    if info_g['jugador'] != "Sin Postor":
                                        if info_g['jugador'] not in st.session_state.cuentas:
                                            st.session_state.cuentas[info_g['jugador']] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                                        st.session_state.cuentas[info_g['jugador']]['Premios'] += premio_final_liq
                                    st.session_state.ganancia_casa += monto_casa_calc
                                    st.session_state.historial_ganadores[carr_activa] = {
                                        "Ganador": info_g['jugador'], 
                                        "Premio": formatear_bs(premio_final_liq),
                                        "Caballo": caballo_ganador_elegido
                                    }
                                    guardar_estado_global()
                                    st.rerun()
                        else:
                            st.info("ℹ️ Esta carrera ya tiene un ganador liquidado.")

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
                            st.markdown(f"🙈 **Remate Ciego - Asignación de Ejemplar ({carr_activa})**")
                            monto_fijo_carrera = detalles_carr.get('monto_fijo_ciego', 500.0)

                            caballos_disponibles_ciego = [
                                cab for cab, info in st.session_state.remates[carr_activa].items() 
                                if (info['jugador'] == "Sin Postor" or info['monto'] <= 0) and cab not in excluidos_carr_activa
                            ]

                            if not caballos_disponibles_ciego:
                                st.warning("⚠️ Todos los ejemplares disponibles de esta carrera ya han sido adquiridos.")
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
                                                st.session_state.remates[carr_activa][cb_disp] = {
                                                    "jugador": st.session_state.usuario_activo, 
                                                    "monto": monto_fijo_carrera
                                                }

                                                st.session_state.historial_jugadas.append({
                                                    "fecha": ahora_dt_frag.strftime('%d/%m/%Y %I:%M:%S %p'),
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
                                                
                                                components.html("<script>window.parent.reproducirAlertaMovilYCalle('exito');</script>", height=0, width=0)
                                                st.success(f"🎉 #{num_cb_parte} asignado a **{st.session_state.usuario_activo}** ({formatear_bs(monto_fijo_carrera)})!")
                                                st.rerun()
                        else:
                            st.markdown(f"⚡ **Registro Rápido de Puja - {carr_activa}**")
                            lista_caballos_activos = [c for c in list(st.session_state.remates[carr_activa].keys()) if c not in excluidos_carr_activa]
                            
                            if not lista_caballos_activos:
                                st.warning("No hay ejemplares disponibles para pujar.")
                            else:
                                k_sel_cab = f"rem_caballo_activo_click_{carr_activa}"
                                if k_sel_cab not in st.session_state or st.session_state[k_sel_cab] not in lista_caballos_activos:
                                    st.session_state[k_sel_cab] = lista_caballos_activos[0]
                                    
                                st.markdown(f"🔹 **1. Seleccionar Ejemplar (Disponibles: {len(lista_caballos_activos)}):**")
                                
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
                                            
                                            info_remate_cab = st.session_state.remates[carr_activa].get(cab_item, {})
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
                                                    div[data-testid="stVerticalBlock"] button[key="rem_btn_cab_{carr_activa}_{idx_cab}"] {{
                                                        {color_estilo}
                                                    }}
                                                    </style>
                                                """, unsafe_allow_html=True)

                                                if st.button(f"#{num_parte}", key=f"rem_btn_cab_{carr_activa}_{idx_cab}", use_container_width=True):
                                                    st.session_state[k_sel_cab] = cab_item
                                                    st.rerun()

                                            idx_cab += 1
                                
                                caballo_seleccionado = st.session_state[k_sel_cab]
                                propietario_actual_sel = st.session_state.remates[carr_activa][caballo_seleccionado].get('jugador', 'Sin Postor')
                                st.info(f"Ejemplar activo: **{caballo_seleccionado}** (Poseedor actual: **{propietario_actual_sel}**)")

                                puja_actual = st.session_state.remates[carr_activa][caballo_seleccionado]['monto']
                                opciones_escala = obtener_siguientes_montos(puja_actual)
                                monto_puja = st.selectbox("💰 **2. Monto de Puja**", opciones_escala, format_func=lambda x: formatear_bs(x), key=f"rem_sel_monto_{carr_activa}_{caballo_seleccionado}")
                                
                                if carrera_cerrada:
                                    st.button(f"🔒 CERRADO - NO DISPONIBLE", key=f"rem_btn_confirmar_{carr_activa}", use_container_width=True, type="primary", disabled=True)
                                else:
                                    st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
                                    if st.button(f"🔨 ¡CONFIRMAR PUJA DE {formatear_bs(monto_puja)}!", key=f"rem_btn_confirmar_{carr_activa}", use_container_width=True, type="primary"):
                                        if monto_puja <= puja_actual:
                                            st.error("El monto debe ser mayor a la puja actual.")
                                        else:
                                            st.session_state.remates[carr_activa][caballo_seleccionado] = {"jugador": st.session_state.usuario_activo, "monto": monto_puja}

                                            st.session_state.historial_jugadas.append({
                                                "fecha": ahora_dt_frag.strftime('%d/%m/%Y %I:%M:%S %p'),
                                                "jugador": st.session_state.usuario_activo,
                                                "tipo": f"Remate ({modo_actual_remate})",
                                                "carrera": carr_activa,
                                                "detalle": caballo_seleccionado,
                                                "monto": monto_puja
                                            })
                                            if estado_conteo == "CONTEO_10S":
                                                st.session_state.tiempo_inicio_conteo_modalidad[clave_mod_carr] = obtener_hora_venezuela_local()
                                            guardar_estado_global()
                                            
                                            components.html("<script>window.parent.reproducirAlertaMovilYCalle('exito');</script>", height=0, width=0)
                                            st.success("✅ ¡Puja registrada correctamente!")
                                            st.rerun()

renderizar_tiempo_real_universal()

# =========================================================================
# 2. MÓDULO DE DUPLETA, TRIPLETA Y POLLA HÍPICA
# =========================================================================
if menu_principal_opcion == "Dupletas":
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
        if st.button("🏇 POLLA HIPICA", key="sub_dup_polla", use_container_width=True, type="primary" if st.session_state.sub_dupleta_opcion == "POLLA HIPICA" else "secondary"):
            st.session_state.sub_dupleta_opcion = "POLLA HIPICA"
            guardar_estado_global()
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<hr style='margin: 0.2rem 0; border-color: #21262d;'>", unsafe_allow_html=True)
    sub_dup_actual = st.session_state.sub_dupleta_opcion

    st.markdown(f"<div class='subasta-header'>🎟️ Armado Visual de {sub_dup_actual}</div>", unsafe_allow_html=True)
    
    clave_mod_mult = sub_dup_actual
    dt_inicio_m = st.session_state.fechas_horas_inicio_modalidad_multiple.get(clave_mod_mult)
    dt_cierre_m = st.session_state.fechas_horas_cierre_modalidad_multiple.get(clave_mod_mult)

    if isinstance(dt_inicio_m, str):
        try: dt_inicio_m = datetime.fromisoformat(dt_inicio_m)
        except Exception: dt_inicio_m = None
    if isinstance(dt_cierre_m, str):
        try: dt_cierre_m = datetime.fromisoformat(dt_cierre_m)
        except Exception: dt_cierre_m = None

    bloqueo_por_horario = False
    if dt_inicio_m and ahora_dt < dt_inicio_m:
        bloqueo_por_horario = True
        st.warning(f"⏳ **AÚN NO ABRE:** Esta modalidad abre el {dt_inicio_m.strftime('%d/%m/%Y a las %I:%M %p')}.")
    elif dt_cierre_m and ahora_dt > dt_cierre_m:
        bloqueo_por_horario = True
        st.error(f"🔒 **CERRADO ESTRICTO (Hora Tope):** El horario de emisión finalizó el {dt_cierre_m.strftime('%d/%m/%Y a las %I:%M %p')}.")

    if dt_inicio_m:
        st.markdown(f"<div style='background:#161b22; padding:5px; border-radius:5px; margin-bottom:3px; border:1px solid #30363d; font-size:11px;'>🟢 Apertura ({sub_dup_actual}): <b>{dt_inicio_m.strftime('%d/%m/%Y - %I:%M %p')}</b></div>", unsafe_allow_html=True)
    if dt_cierre_m:
        st.markdown(f"<div style='background:#161b22; padding:5px; border-radius:5px; margin-bottom:6px; border:1px solid #30363d; font-size:11px;'>⏰ Cierre Estricto ({sub_dup_actual}): <b>{dt_cierre_m.strftime('%d/%m/%Y - %I:%M %p')}</b></div>", unsafe_allow_html=True)

    if st.session_state.dupleta_bloqueada or bloqueo_por_horario:
        st.error("🔒 **BLOQUEADO:** Emisión cerrada temporalmente (Hora tope vencida o bloqueo de administrador).")

    monto_unico_seccion = st.session_state.config_montos_especiales.get(sub_dup_actual, 500.0)

    if sub_dup_actual == "Dupleta":
        pote_total = sum([t['monto'] for t in st.session_state.dupletas_tickets if t.get('estado') == 'Pendiente'])
        carreras_permitidas = [c for c in st.session_state.carreras_habilitadas_dupleta if c in lista_carreras_disponibles]
    elif sub_dup_actual == "Tripleta":
        pote_total = sum([t['monto'] for t in st.session_state.tripleta_tickets if t.get('estado') == 'Pendiente'])
        carreras_permitidas = [c for c in st.session_state.carreras_habilitadas_tripleta if c in lista_carreras_disponibles]
    else: # POLLA HIPICA
        pote_total = sum([t['monto'] for t in st.session_state.polla_tickets])
        total_c = st.session_state.get('total_carreras_semana', len(lista_carreras_disponibles))
        inicio_p = max(1, total_c - 5)
        carreras_ult6 = [f"Carrera {i}" for i in range(inicio_p, total_c + 1)]
        carreras_permitidas = [c for c in carreras_ult6 if c in lista_carreras_disponibles]
        st.session_state.carreras_habilitadas_polla = carreras_permitidas

    st.markdown(f"""
        <div class="pote-cyber-card">
            <div class="pote-cyber-title">💰 POTE ACUMULADO DE {sub_dup_actual.upper()}</div>
            <div class="pote-cyber-value">{formatear_bs(pote_total)}</div>
        </div>
    """, unsafe_allow_html=True)

    cards_html_slider = ""
    for carr_h in carreras_permitidas:
        det_h = st.session_state.detalles_carreras.get(carr_h, {})
        cond_h = det_h.get('condicion', 'Carrera oficial')
        dist_h = det_h.get('distancia', '1200 mts')
        hora_h = det_h.get('hora', '02:00 PM')
        
        img_src_html = ""
        if carr_h in st.session_state.imagenes_carreras:
            img_src_html = f'<img src="{st.session_state.imagenes_carreras[carr_h]}" style="width:100%; height:260px; object-fit:cover; border-radius:8px; margin-bottom:10px;" />'
        else:
            img_src_html = f'<div style="width:100%; height:260px; background:#161b22; border:1px dashed #30363d; display:flex; align-items:center; justify-content:center; border-radius:8px; margin-bottom:10px; color:#8b949e; font-size:13px; font-weight:700;">{carr_h}</div>'

        cards_html_slider += f"""
            <div style="flex: 0 0 210px; background: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 12px; text-align: left; box-shadow: 0px 5px 15px rgba(0,0,0,0.7); display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    {img_src_html}
                    <div style="color: #f1c40f; font-size: 14px; font-weight: 900; margin-bottom: 5px;">{carr_h}</div>
                    <div style="color: #8b949e; font-size: 10px; line-height: 1.3; white-space: normal; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;">{cond_h}</div>
                </div>
                <div style="color: #ffffff; font-size: 10px; font-weight: 700; margin-top: 10px; border-top: 1px solid #21262d; padding-top: 6px;">📏 {dist_h} &nbsp;|&nbsp; ⏰ {hora_h}</div>
            </div>
        """

    if cards_html_slider:
        st.markdown("🖼️ **Carrusel de Carreras Disponibles (Tarjetas Verticales Amplias):**")
        st.markdown(f"""
            <div style="display: flex; overflow-x: auto; gap: 12px; padding-bottom: 12px; margin-bottom: 14px; scrollbar-width: thin;">
                {cards_html_slider}
            </div>
        """, unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(f"👤 **Jugador Activo:** `{st.session_state.usuario_activo}` &nbsp;|&nbsp; 💵 **Costo Ticket:** `{formatear_bs(monto_unico_seccion)}`")
        if sub_dup_actual == "POLLA HIPICA":
            st.markdown("<p style='color: #00ffff; font-size: 11px; font-weight: 700;'>ℹ️ <b>Regla de Polla Hípica:</b> Se juega en las últimas 6 carreras consecutivas de la semana. <u>Se permite registrar pollas/tickets repetidos</u>. Si hay varios ganadores con los mismos puntos máximos, <b>el pote se repartirá equitativamente entre ellos</b>.</p>", unsafe_allow_html=True)
        st.markdown("---")

        if not carreras_permitidas:
            st.warning(f"⚠️ No hay carreras habilitadas para **{sub_dup_actual}**.")
        else:
            seleccion_legs = []
            valido_legs = True
            carreras_usadas = set()

            if sub_dup_actual == "POLLA HIPICA":
                # --- MODELO VISUAL IDÉNTICO A LA IMAGEN PARA POLLA HÍPICA ---
                st.markdown("🎯 **Selección de Ejemplares (Modelo Bloque de Carreras con Grilla Numérica):**")
                
                for carr_leg in carreras_permitidas:
                    st.markdown(f"""
                        <div style="background: #1f3a2e; border: 1px solid #4e8a6d; border-radius: 8px 8px 0 0; padding: 6px 12px; font-weight: 900; color: #f1c40f; font-size: 14px; margin-top: 12px;">
                            🏁 {carr_leg}
                        </div>
                    """, unsafe_allow_html=True)

                    retirados_carr_t = st.session_state.ejemplares_retirados.get(carr_leg, [])
                    no_val_carr_t = st.session_state.get('ejemplares_no_valido', {}).get(carr_leg, [])
                    excluidos_carr_t = set(retirados_carr_t) | set(no_val_carr_t)

                    banco_cab_carr = st.session_state.banco_caballos_por_carrera.get(carr_leg, [])
                    if not banco_cab_carr:
                        banco_cab_carr = [f"{j} - Ejemplar {j}" for j in range(1, 11)]

                    k_sel_grid = f"grid_polla_{carr_leg}"
                    if k_sel_grid not in st.session_state or st.session_state[k_sel_grid] not in banco_cab_carr:
                        validos_ini = [c for c in banco_cab_carr if c not in excluidos_carr_t]
                        st.session_state[k_sel_grid] = validos_ini[0] if validos_ini else banco_cab_carr[0]

                    # Grilla de botones numéricos estilo la imagen adjunta
                    cols_grid = st.columns(min(6, len(banco_cab_carr)), gap="small")
                    for idx_cb, cb_item in enumerate(banco_cab_carr):
                        col_i = idx_cb % 6
                        num_p = cb_item.split(" - ")[0]
                        es_excluido = cb_item in excluidos_carr_t
                        es_seleccionado = (st.session_state[k_sel_grid] == cb_item)

                        with cols_grid[col_i]:
                            if es_excluido:
                                st.button(f"❌ {num_p}", key=f"btn_g_{carr_leg}_{idx_cb}", disabled=True, use_container_width=True)
                            else:
                                btn_type = "primary" if es_seleccionado else "secondary"
                                if st.button(f"{num_p}", key=f"btn_g_{carr_leg}_{idx_cb}", type=btn_type, use_container_width=True):
                                    st.session_state[k_sel_grid] = cb_item
                                    st.rerun()

                    cab_leg = st.session_state[k_sel_grid]
                    if cab_leg in excluidos_carr_t and banco_cab_carr:
                        idx_ret = banco_cab_carr.index(cab_leg) if cab_leg in banco_cab_carr else 0
                        siguiente_cab = None
                        for siguiente_c in banco_cab_carr[idx_ret + 1:] + banco_cab_carr[:idx_ret]:
                            if siguiente_c not in excluidos_carr_t:
                                siguiente_cab = siguiente_c
                                break
                        if siguiente_cab:
                            cab_leg = siguiente_cab
                            st.session_state[k_sel_grid] = cab_leg

                    seleccion_legs.append({"carrera": carr_leg, "ejemplar": cab_leg})
                    st.markdown("<div style='background: #11151c; padding: 6px; border: 1px solid #30363d; border-radius: 0 0 8px 8px; margin-bottom: 8px; font-size: 11px; color: #00ffff;'>Seleccionado en <b>{carr_leg}</b>: <b>{cab_leg}</b></div>".format(carr_leg=carr_leg, cab_leg=cab_leg), unsafe_allow_html=True)
            else:
                # Dupleta o Tripleta estándar
                cantidad_pasos = 2 if sub_dup_actual == "Dupleta" else 3
                for paso in range(cantidad_pasos):
                    st.markdown(f"🔹 **Paso {paso + 1} de {cantidad_pasos}**")
                    carr_leg = carreras_permitidas[paso % len(carreras_permitidas)]
                    st.markdown(f"🏁 **Carrera:** `{carr_leg}`")
                    
                    retirados_carr_t = st.session_state.ejemplares_retirados.get(carr_leg, [])
                    no_val_carr_t = st.session_state.get('ejemplares_no_valido', {}).get(carr_leg, [])
                    excluidos_carr_t = set(retirados_carr_t) | set(no_val_carr_t)

                    banco_cab_carr = st.session_state.banco_caballos_por_carrera.get(carr_leg, [])
                    caballos_in_carr = [c for c in banco_cab_carr if c not in excluidos_carr_t]
                    if not caballos_in_carr:
                        caballos_in_carr = banco_cab_carr if banco_cab_carr else ["1 - Ejemplar 1"]

                    cab_leg = st.selectbox(
                        f"Selecciona el Ejemplar para {carr_leg}", 
                        options=caballos_in_carr, 
                        key=f"ticket_cab_{sub_dup_actual}_{paso}"
                    )

                    if carr_leg in carreras_usadas:
                        valido_legs = False
                    carreras_usadas.add(carr_leg)
                    seleccion_legs.append({"carrera": carr_leg, "ejemplar": cab_leg})
                    st.markdown("---")

            if not st.session_state.dupleta_bloqueada and not bloqueo_por_horario:
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
                        if sub_dup_actual != "POLLA HIPICA":
                            for t in lista_tickets_activo:
                                t_legs_ordenadas = sorted(t['legs'], key=lambda x: x['carrera'])
                                t_firma = tuple((l['carrera'], l['ejemplar']) for l in t_legs_ordenadas)
                                if t_firma == firma_combinacion:
                                    duplicado = True
                                    break

                        if duplicado:
                            st.error("❌ **BLOQUEADO:** Ya existe un ticket con esta misma combinación.")
                        else:
                            prefijo_id = "DUP" if sub_dup_actual == "Dupleta" else ("TRIP" if sub_dup_actual == "Tripleta" else "POLLA")
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
                            
                            components.html("<script>window.parent.reproducirAlertaMovilYCalle('exito');</script>", height=0, width=0)
                            st.success(f"✅ ¡Ticket {ticket_id} emitido con éxito (Estado: PENDIENTE)!")
                            st.rerun()

    if sub_dup_actual == "POLLA HIPICA":
        st.markdown("---")
        st.markdown("### 🏆 Panel de Resultados y Tabla de Posiciones (Polla Hípica)")
        
        with st.container(border=True):
            st.markdown("🎯 **Cargar Resultados Oficiales por Carrera (Puntuación: 1° = 5 Ptos | 2° = 3 Ptos | 3° = 1 Pto)**")
            carr_res_sel = st.selectbox("Seleccionar Carrera", carreras_permitidas, key="sel_carrera_resultado_polla")
            
            banco_caballos_carr = st.session_state.banco_caballos_por_carrera.get(carr_res_sel, [])
            
            col_res1, col_res2, col_res3 = st.columns(3)
            with col_res1:
                res_1ro = st.selectbox("1er Lugar (5 Ptos)", options=["Sin Asignar"] + banco_caballos_carr, key=f"res_1ro_{carr_res_sel}")
            with col_res2:
                res_2do = st.selectbox("2do Lugar (3 Ptos)", options=["Sin Asignar"] + banco_caballos_carr, key=f"res_2do_{carr_res_sel}")
            with col_res3:
                res_3ro = st.selectbox("3er Lugar (1 Pto)", options=["Sin Asignar"] + banco_caballos_carr, key=f"res_3ro_{carr_res_sel}")

            if st.button("💾 Guardar Resultados Oficiales Carrera", key=f"btn_guardar_res_{carr_res_sel}", type="primary"):
                if 'resultados_oficiales_polla' not in st.session_state:
                    st.session_state.resultados_oficiales_polla = {}
                st.session_state.resultados_oficiales_polla[carr_res_sel] = {
                    "1ro": res_1ro, "2do": res_2do, "3ro": res_3ro
                }
                guardar_estado_global()
                st.success(f"✅ Resultados oficiales de **{carr_res_sel}** guardados correctamente.")
                st.rerun()

        st.markdown("#### 📊 Tabla de Posiciones y Puntuación en Vivo")
        
        tabla_puntuaciones = {} 
        resultados_oficiales = st.session_state.get('resultados_oficiales_polla', {})
        
        for t in st.session_state.polla_tickets:
            puntos_ticket = 0
            detalle_puntos = []
            
            for leg in t['legs']:
                carr_l = leg['carrera']
                ej_apostado = leg['ejemplar'].split(" (")[0]
                
                if carr_l in resultados_oficiales:
                    res_c = resultados_oficiales[carr_l]
                    
                    if res_c.get("1ro") != "Sin Asignar" and ej_apostado in res_c.get("1ro"):
                        puntos_ticket += 5
                        detalle_puntos.append(f"{carr_l}: 1° (+5)")
                    elif res_c.get("2do") != "Sin Asignar" and ej_apostado in res_c.get("2do"):
                        puntos_ticket += 3
                        detalle_puntos.append(f"{carr_l}: 2° (+3)")
                    elif res_c.get("3ro") != "Sin Asignar" and ej_apostado in res_c.get("3ro"):
                        puntos_ticket += 1
                        detalle_puntos.append(f"{carr_l}: 3° (+1)")
            
            tabla_puntuaciones[t['id']] = {
                "ticket": t['id'],
                "jugador": t['jugador'],
                "puntos": puntos_ticket,
                "monto": t['monto'],
                "detalle": " | ".join(detalle_puntos) if detalle_puntos else "Sin puntos aún"
            }

        if tabla_puntuaciones:
            df_posiciones = pd.DataFrame(list(tabla_puntuaciones.values()))
            df_posiciones = df_posiciones.sort_values(by="puntos", ascending=False).reset_index(drop=True)
            df_posiciones.index = df_posiciones.index + 1
            st.dataframe(df_posiciones, use_container_width=True)

            max_puntos_actual = df_posiciones["puntos"].max() if not df_posiciones.empty else 0
            
            if max_puntos_actual > 0 and len(resultados_oficiales) >= len(carreras_permitidas):
                tickets_ganadores_lista = [row for row in tabla_puntuaciones.values() if row['puntos'] == max_puntos_actual]
                cant_ganadores = len(tickets_ganadores_lista)
                pote_repartido = pote_total / cant_ganadores if cant_ganadores > 0 else 0

                nombres_ganadores_str = ", ".join([f"{g['ticket']} ({g['jugador']})" for g in tickets_ganadores_lista])
                
                st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #ffd700 0%, #ff8c00 100%); border: 3px solid #ffffff; border-radius: 10px; padding: 12px; text-align: center; color: #000000; font-weight: 900; margin-top: 10px; box-shadow: 0 0 15px rgba(255, 215, 0, 0.8);">
                        🏆 ¡POLLA HÍPICA FINALIZADA - POTES REPARTIDOS! 🏆<br>
                        Ganadores con <b>{max_puntos_actual} puntos</b>: {nombres_ganadores_str}<br>
                        💰 Pote total ({formatear_bs(pote_total)}) repartido entre {cant_ganadores} ganador(es): <b>{formatear_bs(pote_repartido)} c/u</b>.
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("ℹ️ No hay tickets registrados en la Polla Hípica para calcular posiciones.")

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
                
                estado_ticket_txt = t.get('estado', 'Pendiente')
                if "GANADOR" in estado_ticket_txt:
                    col_t4.markdown(f"📌 **Estado:** `<span style='color: #2ed573; font-weight: 900;'>{estado_ticket_txt}</span>`", unsafe_allow_html=True)
                else:
                    col_t4.markdown(f"📌 **Estado:** `{estado_ticket_txt}`")
                
                detalles_legs = " ➔ ".join([f"**{l['carrera']}**: {l['ejemplar']}" for l in t['legs']])
                st.markdown(f"> {detalles_legs}")
                st.caption(f"Emitido: {t['fecha']}")

                if sub_dup_actual != "POLLA HIPICA":
                    retirado_in_ticket = False
                    carrera_afectada = None
                    for leg in t['legs']:
                        carr_l = leg['carrera']
                        ej_l = leg['ejemplar'].split(" (")[0]
                        retirados_carr = st.session_state.ejemplares_retirados.get(carr_l, [])
                        noval_carr = st.session_state.get('ejemplares_no_valido', {}).get(carr_l, [])
                        if ej_l in retirados_carr or ej_l in noval_carr:
                            retirado_in_ticket = True
                            carrera_afectada = carr_l
                            break

                    if retirado_in_ticket:
                        if t.get('estado') == 'Pendiente':
                            t['estado'] = 'Nulo (Retirado/No Valido)'
                            jug_t = t['jugador']
                            monto_t = t['monto']
                            if jug_t in st.session_state.cuentas:
                                st.session_state.cuentas[jug_t]['Pujas'] = max(0.0, st.session_state.cuentas[jug_t]['Pujas'] - monto_t)
                            st.session_state.historial_jugadas.append({
                                "fecha": ahora_dt.strftime('%d/%m/%Y %I:%M:%S %p'),
                                "jugador": jug_t,
                                "tipo": "Ticket Anulado (Retiro/Invalidez)",
                                "carrera": carrera_afectada,
                                "detalle": f"Ticket {t['id']} anulado por retiro/invalidez",
                                "monto": -monto_t
                            })
                            guardar_estado_global()

                        st.error(f"❌ El ticket **{t['id']}** está **NULO** y su monto ha sido restado porque el ejemplar de la **{carrera_afectada}** fue retirado o marcado como no válido:")
                        
                        with st.form(key=f"form_modificar_ticket_{t['id']}_{idx_t}"):
                            nuevas_legs = []
                            for i_l, leg in enumerate(t['legs']):
                                carr_l = leg['carrera']
                                ej_actual = leg['ejemplar'].split(" (")[0]
                                
                                if carr_l == carrera_afectada:
                                    ret_carr = st.session_state.ejemplares_retirados.get(carr_l, [])
                                    noval_carr = st.session_state.get('ejemplares_no_valido', {}).get(carr_l, [])
                                    excl_carr = set(ret_carr) | set(noval_carr)
                                    disponibles_l = [c for c in list(st.session_state.remates.get(carr_l, {}).keys()) if c not in excl_carr]
                                    
                                    idx_def = 0
                                    if ej_actual in disponibles_l:
                                        idx_def = disponibles_l.index(ej_actual)

                                    nuevo_ej = st.selectbox(
                                        f"Elija nuevo ejemplar para {carr_l} (Invalido/Retirado: {ej_actual})",
                                        options=disponibles_l if disponibles_l else [ej_actual],
                                        index=idx_def,
                                        key=f"mod_ticket_{t['id']}_carr_{carr_l}"
                                    )
                                    nuevas_legs.append({"carrera": carr_l, "ejemplar": f"{nuevo_ej} (Cambiado por retiro/invalidez)"})
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
    st.markdown('<div id="reportar-pago-section"></div>', unsafe_allow_html=True)
    
    st.markdown("<div class='subasta-header'>📊 Mis Cuentas, Historial y Reporte de Pago Móvil</div>", unsafe_allow_html=True)
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

    with st.container(border=True):
        st.markdown("📱 **1. Datos para Pago Móvil**")
        p_movil = st.session_state.datos_pago_movil
        
        html_pago_movil_vertical = f"""
        <button onclick="navigator.clipboard.writeText(`Banco: {p_movil['banco']}\\nTeléfono: {p_movil['telefono']}\\nCédula/RIF: {p_movil['cedula']}`); alert('¡Datos copiados!');" style="width: 100%; background: #21262d; color: #00ffff; border: 1px solid #30363d; padding: 7px; border-radius: 6px; font-weight: 700; cursor: pointer; font-size: 11px; margin-bottom: 8px;">
            📋 COPIAR DATOS
        </button>
        <div style="background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 8px 10px; font-family: sans-serif; color: #f0f6fc; font-size: 11px;">
            <div style="margin-bottom: 4px;">🏦 <b>Banco:</b> {p_movil['banco']}</div>
            <div style="margin-bottom: 4px;">📱 <b>Teléfono:</b> {p_movil['telefono']}</div>
            <div>🆔 <b>Cédula/RIF:</b> {p_movil['cedula']}</div>
        </div>
        """
        components.html(html_pago_movil_vertical, height=105)

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
            banco_remitente = st.selectbox("Banco Emisor (de donde envió)", BANCOS_VENEZUELA)
            ref_pago = st.text_input("Últimos 4 dígitos o Referencia")
            
            if st.form_submit_button("📤 Enviar Reporte de Pago", use_container_width=True):
                if monto_rep > 0 and ref_pago:
                    nuevo_reporte = {
                        "jugador": jugador_actual,
                        "monto": monto_rep,
                        "banco": banco_remitente,
                        "referencia": ref_pago,
                        "fecha": ahora_dt.strftime('%d/%m/%Y %I:%M %p'),
                        "estado": "Pendiente de Aprobación"
                    }
                    st.session_state.reportes_pago.append(nuevo_reporte)
                    
                    idx_nuevo = len(st.session_state.reportes_pago) - 1
                    enviar_notificacion_telegram_pago(idx_nuevo, jugador_actual, monto_rep, banco_remitente, ref_pago)
                    
                    guardar_estado_global()
                    st.success("✅ ¡Reporte de pago enviado con éxito! Notificación enviada a Telegram.")
                    st.rerun()
                else:
                    st.error("⚠️ Ingrese un monto válido y la referencia.")

    st.markdown("<br>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("📋 **3. Mis Reportes Enviados**")
        mis_reportes = [r for r in st.session_state.reportes_pago if r['jugador'] == jugador_actual]
        if not mis_reportes:
            st.info("ℹ️ No has enviado reportes de pago todavía.")
        else:
            for rep in reversed(mis_reportes):
                st.markdown(f"🔹 *{rep['fecha']}* | **{formatear_bs(rep['monto'])}** | Banco: `{rep['banco']}` | Ref: `{rep['referencia']}` | 📌 `{rep['estado']}`")

    st.markdown("<br>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(f"### 🎟️ 4. Historial de Tickets y Asignaciones de `{jugador_actual}`")

        st.markdown("#### 🐎 Tickets de Remates Ganadores (Al Cierre)")
        remates_ganados_por_carrera = {}
        for carr_k, remates_carr in st.session_state.remates.items():
            carrera_remate_cerrada = st.session_state.carreras_cerradas_remate.get(carr_k, False)
            if carrera_remate_cerrada:
                for ej_k, info_rem in remates_carr.items():
                    if info_rem['jugador'] == jugador_actual and info_rem['monto'] > 0:
                        retirados_c = st.session_state.ejemplares_retirados.get(carr_k, [])
                        noval_c = st.session_state.get('ejemplares_no_valido', {}).get(carr_k, [])
                        if ej_k not in retirados_c and ej_k not in noval_c:
                            remates_ganados_por_carrera[carr_k] = {
                                "ejemplar": ej_k,
                                "monto": info_rem['monto']
                            }

        if remates_ganados_por_carrera:
            for carr_k, info_r in remates_ganados_por_carrera.items():
                detalles_c = st.session_state.detalles_carreras.get(carr_k, {})
                
                fecha_puja = "Jornada actual"
                for h in reversed(st.session_state.historial_jugadas):
                    if h.get('carrera') == carr_k and h.get('jugador') == jugador_actual and h.get('detalle') == info_r['ejemplar']:
                        fecha_puja = h.get('fecha', '')
                        break

                ticket_html = f"""
                    <div class="ticket-jugador-card">
                        <div class="ticket-header-row">
                            <span>🏷️ TICKET REMATE (OFICIAL)</span>
                            <span>📅 {fecha_puja}</span>
                        </div>
                        <div class="ticket-body-row">🏁 <b>Carrera:</b> {carr_k}</div>
                        <div class="ticket-body-row">🐎 <b>Ejemplar:</b> {info_r['ejemplar']}</div>
                        <div class="ticket-body-row" style="color: #f1c40f; margin-top: 6px;">💰 <b>Monto:</b> {formatear_bs(info_r['monto'])}</div>
                    </div>
                """
                st.markdown(ticket_html, unsafe_allow_html=True)
        else:
            st.info("ℹ️ Los tickets de remate se muestran aquí cuando se cierren las carreras.")

        st.markdown("---")
        tickets_usuario_dupletas = [t for t in st.session_state.dupletas_tickets if t['jugador'] == jugador_actual]
        tickets_usuario_tripletas = [t for t in st.session_state.tripleta_tickets if t['jugador'] == jugador_actual]
        tickets_usuario_pollas = [t for t in st.session_state.polla_tickets if t['jugador'] == jugador_actual]
        todos_tickets_multiples = tickets_usuario_dupletas + tickets_usuario_tripletas + tickets_usuario_pollas

        if todos_tickets_multiples:
            st.markdown("#### 🎟️ Tickets Múltiples")
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
                        <div class="ticket-body-row" style="color: #f1c40f; margin-top: 6px;">💰 <b>Monto:</b> {formatear_bs(t['monto'])}</div>
                    </div>
                """
                st.markdown(ticket_m_html, unsafe_allow_html=True)
        else:
            st.info("ℹ️ No hay tickets múltiples registrados.")

# =========================================================================
# 4. ZONA DE ADMINISTRADOR
# =========================================================================
elif menu_principal_opcion == "🔒 Zona Admin":
    st.markdown("<div class='subasta-header'>🔒 Panel de Configuración y Administración</div>", unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "✍️ Caballos", 
        "👥 Usuarios", 
        "⚙️ Dupleta/Polla", 
        "📺 Video", 
        "📊 Saldos", 
        "🖼️ Imágenes"
    ])

    with tab1:
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
                
                carreras_generadas = [f"Carrera {i}" for i in range(1, nueva_cantidad_carreras + 1)]
                
                for c_n in carreras_generadas:
                    if c_n not in st.session_state.banco_caballos_por_carrera:
                        st.session_state.banco_caballos_por_carrera[c_n] = [f"{j} - Ejemplar {j}" for j in range(1, 11)]
                    
                    if c_n not in st.session_state.remates:
                        st.session_state.remates[c_n] = {f"{j} - Ejemplar {j}": {"jugador": "Sin Postor", "monto": 0.0} for j in range(1, 11)}
                    
                    if c_n not in st.session_state.detalles_carreras:
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
                    
                    if c_n not in st.session_state.carreras_cerradas_remate:
                        st.session_state.carreras_cerradas_remate[c_n] = False
                    if c_n not in st.session_state.remates_cargados_en_cuentas:
                        st.session_state.remates_cargados_en_cuentas[c_n] = False
                    if c_n not in st.session_state.ejemplares_retirados:
                        st.session_state.ejemplares_retirados[c_n] = []
                    if 'ejemplares_no_valido' in st.session_state and c_n not in st.session_state.ejemplares_no_valido:
                        st.session_state.ejemplares_no_valido[c_n] = []

                st.session_state.carreras_activas_remate = list(carreras_generadas)
                st.session_state.carreras_habilitadas_dupleta = list(carreras_generadas)
                st.session_state.carreras_habilitadas_tripleta = list(carreras_generadas)
                
                inicio_p_adm = max(1, nueva_cantidad_carreras - 5)
                st.session_state.carreras_habilitadas_polla = [f"Carrera {i}" for i in range(inicio_p_adm, nueva_cantidad_carreras + 1)]
                
                if not st.session_state.carreras_por_modalidad.get("Adelantados"):
                    st.session_state.carreras_por_modalidad["Adelantados"] = list(carreras_generadas)

                guardar_estado_global()
                st.toast(f"✅ ¡Jornada ajustada a {nueva_cantidad_carreras} carreras con éxito!")
                st.rerun()

        st.markdown("---")
        with st.container(border=True):
            st.markdown("⚡ **Panel Didáctico: Carreras Activas para Remate General**")
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
            st.markdown("🎯 **Asignación Independiente de Carreras por Modalidad**")
            carreras_existentes = list(st.session_state.remates.keys())
            
            modalidades_dict = st.session_state.carreras_por_modalidad
            
            def_adel = [c for c in modalidades_dict.get("Adelantados", []) if c in carreras_existentes]
            def_ciego = [c for c in modalidades_dict.get("Ciegos", []) if c in carreras_existentes]
            def_envivo = [c for c in modalidades_dict.get("En Vivo", []) if c in carreras_existentes]

            sel_adel = st.multiselect("Carreras para Adelantados", options=carreras_existentes, default=def_adel, key="multiselect_carr_adelantados")
            sel_ciego = st.multiselect("Carreras para Ciegos (Seleccione exactamente 2 para 1V y 6V)", options=carreras_existentes, default=def_ciego, key="multiselect_carr_ciegos")
            sel_envivo = st.multiselect("Carreras para 🔴 En Vivo", options=carreras_existentes, default=def_envivo, key="multiselect_carr_envivo")

            if st.button("💾 Guardar Modalidades Independientes", key="btn_save_mod_independientes", use_container_width=True, type="primary"):
                st.session_state.carreras_por_modalidad["Adelantados"] = sel_adel
                st.session_state.carreras_por_modalidad["Ciegos"] = sel_ciego
                st.session_state.carreras_por_modalidad["En Vivo"] = sel_envivo
                guardar_estado_global()
                st.toast("✅ ¡Modalidades guardadas correctamente!")
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
        with st.container(border=True):
            st.markdown(f"⏰ **Control de Horarios Individuales por Modalidad ({carr_banco_sel})**")
            mod_seleccionada_horarios = st.selectbox("Seleccionar Modalidad para Configurar Horarios", ["Adelantados", "Ciegos", "En Vivo"], key=f"sel_mod_horarios_{carr_banco_sel}")
            
            clave_mod_carr_adm = f"{mod_seleccionada_horarios}_{carr_banco_sel}"
            
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                st.markdown(f"**🟢 Inicio ({mod_seleccionada_horarios})**")
                f_ini = st.date_input("Fecha Inicio", value=ahora_dt.date(), key=f"f_ini_{clave_mod_carr_adm}")
                
                c_hi1, c_hi2, c_hi3 = st.columns(3)
                with c_hi1:
                    h_ini_val = st.number_input("Hora (1-12)", min_value=1, max_value=12, value=2, key=f"hi_h_{clave_mod_carr_adm}")
                with c_hi2:
                    m_ini_val = st.number_input("Min (0-59)", min_value=0, max_value=59, value=0, key=f"hi_m_{clave_mod_carr_adm}")
                with c_hi3:
                    ampm_ini = st.selectbox("AM/PM", ["AM", "PM"], index=1, key=f"hi_ap_{clave_mod_carr_adm}")

            with col_h2:
                st.markdown(f"**⏰ Cierre Estricto ({mod_seleccionada_horarios})**")
                f_cier = st.date_input("Fecha Cierre", value=ahora_dt.date(), key=f"f_cier_{clave_mod_carr_adm}")
                
                c_hc1, c_hc2, c_hc3 = st.columns(3)
                with c_hc1:
                    h_cier_val = st.number_input("Hora (1-12)", min_value=1, max_value=12, value=2, key=f"hc_h_{clave_mod_carr_adm}")
                with c_hc2:
                    m_cier_val = st.number_input("Min (0-59)", min_value=0, max_value=59, value=30, key=f"hc_m_{clave_mod_carr_adm}")
                with c_hc3:
                    ampm_cier = st.selectbox("AM/PM", ["AM", "PM"], index=1, key=f"hc_ap_{clave_mod_carr_adm}")

            if st.button(f"💾 Guardar Horarios para {mod_seleccionada_horarios}", key=f"btn_save_horarios_{clave_mod_carr_adm}", use_container_width=True, type="primary"):
                h_i_24 = h_ini_val if ampm_ini == "AM" else (h_ini_val + 12 if h_ini_val < 12 else 12)
                if ampm_ini == "AM" and h_ini_val == 12: h_i_24 = 0
                
                h_c_24 = h_cier_val if ampm_cier == "AM" else (h_cier_val + 12 if h_cier_val < 12 else 12)
                if ampm_cier == "AM" and h_cier_val == 12: h_c_24 = 0

                dt_i_final = datetime.combine(f_ini, dtime(h_i_24, m_ini_val))
                dt_c_final = datetime.combine(f_cier, dtime(h_c_24, m_cier_val))

                st.session_state.fechas_horas_inicio_remate_modalidad[clave_mod_carr_adm] = dt_i_final
                st.session_state.fechas_horas_cierre_remate_modalidad[clave_mod_carr_adm] = dt_c_final
                st.session_state.estado_conteo_carrera_modalidad[clave_mod_carr_adm] = "INACTIVO"
                guardar_estado_global()
                st.toast(f"✅ ¡Horarios guardados para {carr_banco_sel} en modalidad {mod_seleccionada_horarios}!")
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

    with tab2:
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

    with tab3:
        st.markdown("### ⚙️ Configuración de Montos, Horarios y Carreras")
        with st.container(border=True):
            st.markdown("💰 **Montos Únicos**")
            monto_dup_cfg = st.number_input("Dupleta (Bs.)", min_value=0.0, value=float(st.session_state.config_montos_especiales.get("Dupleta", 500.0)), step=50.0, key="cfg_monto_dupleta")
            monto_trip_cfg = st.number_input("Tripleta (Bs.)", min_value=0.0, value=float(st.session_state.config_montos_especiales.get("Tripleta", 500.0)), step=50.0, key="cfg_monto_tripleta")
            monto_polla_cfg = st.number_input("Polla Hípica (Bs.)", min_value=0.0, value=float(st.session_state.config_montos_especiales.get("POLLA HIPICA", 1000.0)), step=50.0, key="cfg_monto_polla")
            
            if st.button("💾 Guardar Montos", key="btn_save_montos_cfg", use_container_width=True, type="primary"):
                st.session_state.config_montos_especiales["Dupleta"] = monto_dup_cfg
                st.session_state.config_montos_especiales["Tripleta"] = monto_trip_cfg
                st.session_state.config_montos_especiales["POLLA HIPICA"] = monto_polla_cfg
                guardar_estado_global()
                st.toast("✅ ¡Guardado!")
                st.rerun()

        st.markdown("---")
        with st.container(border=True):
            st.markdown("⏰ **Control de Horarios (Hora Tope) por Modalidad (Dupleta / Tripleta / Polla Hípica)**")
            mod_mult_sel = st.selectbox("Seleccionar Modalidad Múltiple", ["Dupleta", "Tripleta", "POLLA HIPICA"], key="sel_mod_multiple_horarios")
            
            col_hm1, col_hm2 = st.columns(2)
            with col_hm1:
                st.markdown(f"**🟢 Inicio ({mod_mult_sel})**")
                f_ini_m = st.date_input("Fecha Inicio Múltiple", value=ahora_dt.date(), key=f"f_ini_m_{mod_mult_sel}")
                
                c_hmi1, c_hmi2, c_hmi3 = st.columns(3)
                with c_hmi1:
                    h_ini_m_val = st.number_input("Hora (1-12)", min_value=1, max_value=12, value=2, key=f"him_h_{mod_mult_sel}")
                with c_hmi2:
                    m_ini_m_val = st.number_input("Min (0-59)", min_value=0, max_value=59, value=0, key=f"him_m_{mod_mult_sel}")
                with c_hmi3:
                    ampm_ini_m = st.selectbox("AM/PM", ["AM", "PM"], index=1, key=f"him_ap_{mod_mult_sel}")

            with col_hm2:
                st.markdown(f"**⏰ Cierre Estricto (Hora Tope) ({mod_mult_sel})**")
                f_cier_m = st.date_input("Fecha Cierre Múltiple", value=ahora_dt.date(), key=f"f_cier_m_{mod_mult_sel}")
                
                c_hmc1, c_hmc2, c_hmc3 = st.columns(3)
                with c_hmc1:
                    h_cier_m_val = st.number_input("Hora (1-12)", min_value=1, max_value=12, value=2, key=f"hcm_h_{mod_mult_sel}")
                with c_hmc2:
                    m_cier_m_val = st.number_input("Min (0-59)", min_value=0, max_value=59, value=30, key=f"hcm_m_{mod_mult_sel}")
                with c_hmc3:
                    ampm_cier_m = st.selectbox("AM/PM", ["AM", "PM"], index=1, key=f"hcm_ap_{mod_mult_sel}")

            if st.button(f"💾 Guardar Horarios para {mod_mult_sel}", key=f"btn_save_horarios_m_{mod_mult_sel}", use_container_width=True, type="primary"):
                h_im_24 = h_ini_m_val if ampm_ini_m == "AM" else (h_ini_m_val + 12 if h_ini_m_val < 12 else 12)
                if ampm_ini_m == "AM" and h_ini_m_val == 12: h_im_24 = 0
                
                h_cm_24 = h_cier_m_val if ampm_cier_m == "AM" else (h_cier_m_val + 12 if h_cier_m_val < 12 else 12)
                if ampm_cier_m == "AM" and h_cier_m_val == 12: h_cm_24 = 0

                dt_im_final = datetime.combine(f_ini_m, dtime(h_im_24, m_ini_m_val))
                dt_cm_final = datetime.combine(f_cier_m, dtime(h_cm_24, m_cm_24:=m_cier_m_val))

                st.session_state.fechas_horas_inicio_modalidad_multiple[mod_mult_sel] = dt_im_final
                st.session_state.fechas_horas_cierre_modalidad_multiple[mod_mult_sel] = dt_cm_final
                guardar_estado_global()
                st.toast(f"✅ ¡Horarios guardados para {mod_mult_sel}!")
                st.rerun()

        st.markdown("---")
        with st.container(border=True):
            st.markdown("🏇 **Carreras Habilitadas (Dupleta y Tripleta)**")
            carr_disp_all = list(st.session_state.remates.keys())
            
            def_dup = [c for c in st.session_state.carreras_habilitadas_dupleta if c in carr_disp_all]
            def_trip = [c for c in st.session_state.carreras_habilitadas_tripleta if c in carr_disp_all]

            sel_dup_hab = st.multiselect("Dupleta", options=carr_disp_all, default=def_dup, key="multiselect_hab_dup")
            sel_trip_hab = st.multiselect("Tripleta", options=carr_disp_all, default=def_trip, key="multiselect_hab_trip")

            if st.button("💾 Guardar Habilitadas", key="btn_save_carr_hab", use_container_width=True, type="primary"):
                st.session_state.carreras_habilitadas_dupleta = sel_dup_hab
                st.session_state.carreras_habilitadas_tripleta = sel_trip_hab
                guardar_estado_global()
                st.toast("✅ ¡Guardado!")
                st.rerun()

    with tab4:
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

    with tab5:
        st.markdown("### 📊 Saldos de Usuarios y Gestión de Pagos")
        
        with st.container(border=True):
            st.markdown("⚙️ **Configurar Datos de Pago Móvil para los Jugadores**")
            p_adm = st.session_state.datos_pago_movil
            n_banco = st.text_input("Banco", value=p_adm['banco'], key="adm_p_banco")
            n_tlf = st.text_input("Teléfono", value=p_adm['telefono'], key="adm_p_tlf")
            n_ci = st.text_input("Cédula / RIF", value=p_adm['cedula'], key="adm_p_ci")
            if st.button("💾 Guardar Datos de Pago Móvil", key="btn_save_pagomovil_adm", type="primary"):
                st.session_state.datos_pago_movil = {'banco': n_banco, 'telefono': n_tlf, 'cedula': n_ci}
                guardar_estado_global()
                st.toast("✅ ¡Datos de pago móvil actualizados!")
                st.rerun()

        st.markdown("---")
        st.markdown("📬 **Reportes de Pago Recibidos de Jugadores**")
        if not st.session_state.reportes_pago:
            st.info("ℹ️ No hay reportes de pago pendientes.")
        else:
            for idx_rep, rep in enumerate(reversed(st.session_state.reportes_pago)):
                with st.container(border=True):
                    col_r1, col_r2, col_r3 = st.columns([3, 3, 2])
                    col_r1.markdown(f"👤 **{rep['jugador']}** | 💰 **{formatear_bs(rep['monto'])}**")
                    col_r2.markdown(f"🏦 Banco: `{rep['banco']}` | Ref: `{rep['referencia']}`\n📅 {rep['fecha']}")
                    col_r3.markdown(f"📌 Estado: **{rep['estado']}**")
                    
                    if rep['estado'] == "Pendiente de Aprobación":
                        if st.button(f"✅ Aprobar y Abonar", key=f"btn_aprobar_rep_{idx_rep}", type="primary"):
                            jug_r = rep['jugador']
                            mnt_r = rep['monto']
                            if jug_r not in st.session_state.cuentas:
                                st.session_state.cuentas[jug_r] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                            st.session_state.cuentas[jug_r]['Abonos'] += mnt_r
                            rep['estado'] = "Aprobado (Abonado)"
                            guardar_estado_global()
                            st.success(f"✅ ¡Pago de {formatear_bs(mnt_r)} abonado a {jug_r}!")
                            st.rerun()

        st.markdown("---")
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
        
        col_op1, col_op2 = st.columns(2, gap="small")
        
        with col_op1:
            with st.container(border=True):
                st.markdown("#### 💵 Registrar Abono Directo")
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

    with tab6:
        st.markdown("### 🖼️ Imágenes por Carrera")
        carr_img_sel = st.selectbox("Seleccionar Carrera", lista_carreras_disponibles, key="adm_img_sel_carr")
        
        with st.container(border=True):
            st.markdown("📸 **Imagen de la Carrera (Optimizada para la Red)**")
            imagen_subida = st.file_uploader("Subir imagen (PNG, JPG)", type=["png", "jpg", "jpeg"], key=f"file_img_{carr_img_sel}")
            
            if imagen_subida is not None:
                if st.button("💾 Guardar Imagen", key=f"btn_save_img_{carr_img_sel}", use_container_width=True, type="primary"):
                    try:
                        from PIL import Image
                        img_pil = Image.open(imagen_subida)
                        
                        if img_pil.mode in ("RGBA", "P"):
                            img_pil = img_pil.convert("RGB")
                            
                        max_ancho = 800
                        if img_pil.width > max_ancho:
                            proporcion = max_ancho / img_pil.width
                            nuevo_alto = int(img_pil.height * proporcion)
                            img_pil = img_pil.resize((max_ancho, nuevo_alto), Image.Resampling.LANCZOS)
                            
                        buffer = io.BytesIO()
                        img_pil.save(buffer, format="JPEG", quality=75)
                        bytes_comprimidos = buffer.getvalue()
                        
                        b64_imagen = base64.b64encode(bytes_comprimidos).decode('utf-8')
                        st.session_state.imagenes_carreras[carr_img_sel] = f"data:image/jpeg;base64,{b64_imagen}"
                        guardar_estado_global()
                        st.toast("✅ ¡Imagen optimizada y guardada con éxito!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al procesar la imagen: {e}")

            if carr_img_sel in st.session_state.imagenes_carreras:
                try:
                    img_guardada = st.session_state.imagenes_carreras[carr_img_sel]
                    st.markdown(f'<div class="imagen-carrera-pc-container">', unsafe_allow_html=True)
                    st.image(img_guardada, caption=f"Imagen guardada - {carr_img_sel}", use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                except Exception:
                    pass
                
                if st.button("🗑️ Eliminar Imagen", key=f"btn_del_img_{carr_img_sel}", use_container_width=True):
                    del st.session_state.imagenes_carreras[carr_img_sel]
                    guardar_estado_global()
                    st.toast("🗑️ Removida")
                    st.rerun()

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
