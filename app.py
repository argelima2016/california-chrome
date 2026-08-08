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
st.set_page_config(page_title="WOLF READY TO RUN", layout="wide", page_icon="🐺", initial_sidebar_state="collapsed")

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
        requests.post(url, json=payload, timeout=5)
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
        'carreras_por_modalidad': {"Adelantados": [], "Ciegos": ["1V", "6V"], "En Vivo": []},
        'mapeo_ciegos': {"1V": "", "6V": ""},
        'total_carreras_semana': 10,
        'porcentaje_casa': 30,
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
        'dupleta_bloqueada', 'carreras_activas_remate', 'carreras_por_modalidad', 'mapeo_ciegos',
        'total_carreras_semana', 'porcentaje_casa', 'url_video_en_vivo', 'imagenes_carreras', 'admin_tab_seleccionada',
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

# --- VIGILANTE DE SINCRONIZACIÓN SEGURO (CADA 6 SEGUNDOS) ---
@st.fragment(run_every=6.0)
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

# --- SCRIPT JS GLOBAL PARA AUDIO, VOZ Y DESBLOQUEO DE NAVEGADOR ---
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

        window.parent.addEventListener('click', inicializarAudio, { once: true });
        window.parent.addEventListener('touchstart', inicializarAudio, { once: true });

        function hablarNumero(texto) {
            if ('speechSynthesis' in window.parent) {
                window.parent.speechSynthesis.cancel();
                let utterance = new SpeechSynthesisUtterance(texto);
                utterance.lang = 'es-ES';
                utterance.rate = 1.25;
                window.parent.speechSynthesis.speak(utterance);
            }
        }
        window.parent.hablarNumero = hablarNumero;

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
        window.parent.reproducirAlertaMovilYCalle = reproducirAlertaMovilYCalle;

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
        }
        setInterval(sincronizacionEnVivo, 1000);
    </script>
""", height=0, width=0)

# --- BOTÓN FLOTANTE PARA ACTIVAR AUDIO MANUALMENTE ---
components.html(r"""
    <div style="position: fixed; bottom: 10px; right: 10px; z-index: 999999;">
        <button onclick="window.parent.inicializarAudio && window.parent.inicializarAudio(); alert('🔊 ¡Audio activado correctamente para alertas y voz!');" style="background: linear-gradient(135deg, #f1c40f 0%, #d4ac0d 100%); color: #080a0f; border: 2px solid #ffffff; padding: 8px 12px; border-radius: 20px; font-weight: 900; font-size: 11px; cursor: pointer; box-shadow: 0 4px 15px rgba(241,196,15,0.6);">
            🔊 ACTIVAR AUDIO / VOZ
        </button>
    </div>
""", height=40)

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

# --- CARGAR ARCHIVOS BASE64 (LOGO Y BANNER) ---
def cargar_base64_archivo(nombre_archivo):
    ruta_directorio = os.path.dirname(os.path.abspath(__file__))
    try:
        ruta_imagen = os.path.join(ruta_directorio, nombre_archivo)
        if os.path.exists(ruta_imagen):
            with open(ruta_imagen, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode('utf-8')
    except Exception:
        pass
    return ""

logo_b64 = cargar_base64_archivo("1001397336_preview_rev_1.png")
if not logo_b64:
    for alt in ["1001397336_preview_rev_1.jpg", "logo.png", "logo.jpg"]:
        logo_b64 = cargar_base64_archivo(alt)
        if logo_b64:
            break

if logo_b64:
    logo_display = f'<img src="data:image/png;base64,{logo_b64}" class="header-logo-img" />'
else:
    logo_display = '<span style="color: #f1c40f; font-size: 28px; font-weight: 900; font-style: italic; letter-spacing: 1.5px;">WOLF READY TO RUN</span>'

banner_b64 = cargar_base64_archivo("Gemini_Generated_Image_mn48tzmn48tzmn48.png")

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

for ciego_key in ["1V", "6V"]:
    if ciego_key not in st.session_state.remates:
        st.session_state.banco_caballos_por_carrera[ciego_key] = [f"{j} - Ejemplar {j}" for j in range(1, 15)]
        st.session_state.remates[ciego_key] = {f"{j} - Ejemplar {j}": {"jugador": "Sin Postor", "monto": 0.0} for j in range(1, 15)}
        st.session_state.detalles_carreras[ciego_key] = {
            "condicion": f"Remate Ciego {ciego_key}", 
            "distancia": "1200 mts", 
            "hora": "02:00 PM", 
            "monto_fijo_ciego": 500.0, 
            "incentivo_adelantados": 0.0,
            "incentivo_ciegos": 0.0,
            "incentivo_envivo": 0.0,
            "hora_cierre_real": "No registrada"
        }

if "1V" not in st.session_state.carreras_por_modalidad.get("Ciegos", []):
    st.session_state.carreras_por_modalidad["Ciegos"] = ["1V", "6V"]

lista_carreras_disponibles = [c for c in st.session_state.remates.keys() if c not in ["1V", "6V"]]

total_carrs = st.session_state.get('total_carreras_semana', 10)
inicio_polla_idx = max(1, total_carrs - 5)
ultimas_6_carreras = [f"Carrera {i}" for i in range(inicio_polla_idx, total_carrs + 1)]
st.session_state.carreras_habilitadas_polla = [c for c in ultimas_6_carreras if c in st.session_state.remates]

ahora_dt = obtener_hora_venezuela_local()

# --- ESTILOS CSS GENERALES ---
st.markdown("""
    <style>
    * { box-sizing: border-box !important; }
    .stApp { background-color: #080a0f; color: #f0f6fc; overflow-x: hidden !important; }
    [data-testid="stSidebar"] { display: none !important; visibility: hidden !important; opacity: 0 !important; width: 0px !important; min-width: 0px !important; }
    [data-testid="stToolbar"] { display: none !important; visibility: hidden !important; opacity: 0 !important; pointer-events: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    footer, #MainMenu { visibility: hidden !important; display: none !important; }
    .block-container { padding-top: 0.2rem !important; padding-bottom: 1.5rem !important; padding-left: 0.3rem !important; padding-right: 0.3rem !important; max-width: 100% !important; margin: 0 auto !important; overflow-x: hidden !important; }
    div[data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; overflow-x: auto !important; overflow-y: hidden !important; -webkit-overflow-scrolling: touch !important; width: 100% !important; gap: 4px !important; padding-bottom: 4px !important; scrollbar-width: thin; }
    div[data-testid="stHorizontalBlock"] > div { flex: 0 0 auto !important; width: auto !important; min-width: 90px !important; max-width: none !important; }
    .carreras-scroll-container div[data-testid="stHorizontalBlock"] > div { min-width: 48px !important; width: 48px !important; }
    div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"]:has(button) { gap: 3px !important; margin-top: -12px !important; margin-bottom: -12px !important; }
    div[data-testid="column"]:has(button) { padding: 0px 1px !important; }
    .stButton button { border-radius: 8px !important; font-weight: 800 !important; padding: 0.4rem 0.6rem !important; min-height: 42px !important; font-size: 12px !important; letter-spacing: 0.3px; white-space: nowrap !important; width: 100% !important; }
    div.stButton > button[kind="primary"] { background: linear-gradient(135deg, #f1c40f 0%, #d4ac0d 100%) !important; color: #080a0f !important; font-size: 15px !important; font-weight: 900 !important; border: 2px solid #ffffff !important; box-shadow: 0px 4px 18px rgba(241, 196, 15, 0.6) !important; text-transform: uppercase !important; letter-spacing: 1px !important; transition: all 0.2s ease-in-out; }
    .subasta-header { font-size: clamp(13px, 3.2vw, 16px); font-weight: 800; color: #f1e05a; margin-bottom: 4px; border-bottom: 2px solid #f1e05a; padding-bottom: 2px; }
    .carrera-condicion-card { background-color: #161b22; border: 1px solid #30363d; padding: 8px 10px; border-radius: 6px; font-size: 11px; color: #f0f6fc; margin-bottom: 8px; line-height: 1.3; word-break: break-word; }
    .dashboard-pote-card { background: linear-gradient(135deg, #0d1b2a 0%, #1b263b 100%); border: 2px solid #f1c40f; border-radius: 12px; padding: 12px 14px; text-align: center; margin: 8px 0; box-shadow: 0px 4px 20px rgba(241, 196, 15, 0.25); width: 100%; box-sizing: border-box; }
    .dp-header { color: #00ffff; font-size: 11px; font-weight: 900; letter-spacing: 1.2px; text-transform: uppercase; margin-bottom: 4px; }
    .dp-total-value { color: #f1c40f; font-size: clamp(20px, 5.5vw, 28px); font-weight: 900; margin-bottom: 10px; word-break: break-word; }
    .dp-grid { display: flex; justify-content: space-around; align-items: center; border-top: 1px dashed rgba(241, 196, 15, 0.4); padding-top: 8px; gap: 8px; }
    .dp-item { display: flex; flex-direction: column; flex: 1; align-items: center; }
    .dp-divider { width: 1px; height: 26px; background-color: rgba(241, 196, 15, 0.4); }
    .dp-label { font-size: 9px; font-weight: 800; text-transform: uppercase; color: #8b949e; margin-bottom: 2px; }
    .dp-val { font-size: clamp(13px, 3.5vw, 16px); font-weight: 900; word-break: break-word; }
    @keyframes parpadeoGanador { 0% { transform: scale(1); box-shadow: 0 0 12px #f1c40f; } 50% { transform: scale(1.02); box-shadow: 0 0 25px #00ffff; } 100% { transform: scale(1); box-shadow: 0 0 12px #f1c40f; } }
    .ganador-banner-epic { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); border: 2px solid #f1c40f; border-radius: 12px; padding: 12px; text-align: center; margin: 10px 0; animation: parpadeoGanador 2s infinite ease-in-out; }
    .ganador-titulo-epic { color: #00ffff; font-size: 12px; font-weight: 900; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 4px; }
    .ganador-nombre-epic { color: #f1c40f; font-size: 20px; font-weight: 900; text-transform: uppercase; margin-bottom: 3px; }
    .ganador-premio-epic { color: #2ed573; font-size: 15px; font-weight: 900; }
    .ticket-jugador-card { background: #0d1117; border: 2px solid #30363d; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; box-shadow: 0px 3px 10px rgba(0,0,0,0.5); }
    .ticket-header-row { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #30363d; padding-bottom: 4px; margin-bottom: 6px; font-size: 11px; font-weight: 800; color: #f1c40f; }
    .ticket-body-row { font-size: 12px; color: #f0f6fc; margin-bottom: 3px; font-weight: 600; }
    .header-container-modern { background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); border: 1px solid #30363d; border-radius: 10px; padding: 10px 14px; margin-bottom: 8px; display: flex; flex-direction: column; gap: 10px; width: 100%; box-sizing: border-box; }
    .header-top-row { display: flex; justify-content: space-between; align-items: center; width: 100%; gap: 6px; }
    .header-user-card { display: flex; align-items: center; gap: 8px; background: #080a0f; border: 1px solid #30363d; padding: 4px 10px; border-radius: 6px; }
    .user-details { display: flex; flex-direction: column; text-align: right; }
    .u-name-container { display: flex; align-items: center; justify-content: flex-end; gap: 4px; }
    .u-name { color: #f0f6fc; font-size: 12px; font-weight: 800; }
    .u-bal { font-size: 10px; font-weight: 700; }
    .u-avatar-badge { width: 30px; height: 30px; background: #1f6feb; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; }
    .header-bottom-row-logo { text-align: center; border-top: 1px solid #21262d; padding-top: 8px; }
    .header-logo-img { max-height: 95px; width: auto; object-fit: contain; }
    @keyframes parpadeoLed { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.9); } 100% { opacity: 1; transform: scale(1); } }
    .led-estado { width: 8px; height: 8px; border-radius: 50%; display: inline-block; box-shadow: 0 0 6px currentColor; }
    .led-verde { background-color: #2ed573; color: #2ed573; animation: parpadeoLed 1.5s infinite ease-in-out; }
    .led-rojo { background-color: #ff4757; color: #ff4757; }
    @media (min-width: 769px) { .imagen-carrera-pc-container { max-width: 380px !important; margin: 0 auto !important; display: block !important; } }
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
estado_global_remate = "cerrados" if all(st.session_state.carreras_cerradas_remate.get(c, False) for c in list(st.session_state.remates.keys())) and list(st.session_state.remates.keys()) else "abiertos"
led_clase_css = "led-rojo" if estado_global_remate == "cerrados" else "led-verde"

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
        if nombre_carrera == "1V": return "1V"
        elif nombre_carrera == "6V": return "6V"
    match = re.search(r'\d+', nombre_carrera)
    if match:
        return f"C{match.group(0)}"
    return nombre_carrera[:3].upper()

def generar_tabla_html_remate(remates_dict, retirados_list, no_validos_list=[]):
    html = """
    <style>
        .tabla-referencia { width: 100%; border-collapse: collapse; font-family: sans-serif; background-color: #ffffff; color: #000000; margin-bottom: 8px; table-layout: fixed; }
        .tabla-referencia th { border-top: 2px solid #dfc729; border-bottom: 2px solid #dfc729; padding: 5px 3px; text-align: left; font-weight: 800; background-color: #ffffff; color: #000000; font-size: 10px; overflow: hidden; text-overflow: ellipsis; }
        .tabla-referencia td { border-bottom: 1px solid #dfc729; padding: 5px 3px; background-color: #fbfbfb; color: #111111; font-size: 10px; vertical-align: middle; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .badge-numero { display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 18px; font-weight: bold; font-size: 10px; border-radius: 2px; box-sizing: border-box; }
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
if not st.session_state.carreras_activas_remate and [c for c in st.session_state.remates.keys() if c not in ["1V", "6V"]]:
    st.session_state.carreras_activas_remate = [c for c in st.session_state.remates.keys() if c not in ["1V", "6V"]]

for mod in ["Adelantados", "Ciegos", "En Vivo"]:
    if mod not in st.session_state.carreras_por_modalidad:
        st.session_state.carreras_por_modalidad[mod] = []

lista_carreras_disponibles = [c for c in st.session_state.remates.keys() if c not in ["1V", "6V"]]

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

elementos_carrusel_info.append("CIEGOS: 1V | 6V")

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
    .marquee-container {{ width: 100%; background: transparent; border: none; box-shadow: none; padding: 6px 0; margin-bottom: 8px; overflow: hidden; box-sizing: border-box; display: flex; align-items: center; }}
    .marquee-text {{ display: inline-block; white-space: nowrap; animation: scrollRight 150s linear infinite !important; font-family: 'Arial Black', Gadget, sans-serif; font-size: 13px; font-weight: 900; color: #00ffff; text-transform: uppercase; letter-spacing: 1.2px; text-shadow: 0px 0px 8px rgba(0, 255, 255, 0.9), 2px 2px 2px #000000; padding-right: 100%; }}
    @keyframes scrollRight {{ 0% {{ transform: translateX(-100%); }} 100% {{ transform: translateX(100%); }} }}
</style>
<div class="marquee-container">
    <div class="marquee-text">{texto_unido_marquesina}</div>
</div>
"""
components.html(html_banner_marquesina, height=36)

# --- IMAGEN FIJA ÚNICA DE LA CARTELERA ---
if banner_b64:
    st.markdown(f"""
        <div style="width: 100%; height: 180px; margin: 0 0 8px 0; overflow: hidden; border-radius: 6px;">
            <img src="data:image/png;base64,{banner_b64}" style="width: 100%; height: 100%; object-fit: cover; display: block;" />
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <div style="background: linear-gradient(90deg, #11141d 0%, #1f2937 100%); padding: 12px; text-align: center; margin-bottom: 8px; border-radius: 6px;">
            <h3 style="color: #f1c40f; margin: 0; font-weight: 900; letter-spacing: 1px; font-size: 14px;">INH - HIPÓDROMO DE LA RINCONADA</h3>
            <p style="color: #8b949e; font-size: 10px; margin: 3px 0 0 0;">¡La pasión del hipismo venezolano en vivo!</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
menu_principal_opcion = st.session_state.menu_principal_opcion

# =========================================================================
# BLOQUE FRAGMENTADO UNIVERSAL EN TIEMPO REAL (OPTIMIZADO CADA 8 SEGUNDOS)
# =========================================================================
@st.fragment(run_every=8.0)
def renderizar_tiempo_real_universal():
    cargar_estado_global(forzar_recarga=True)
    ahora_dt_frag = obtener_hora_venezuela_local()

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

        if not list(st.session_state.remates.keys()):
            st.warning("⚠️ No hay carreras cargadas en el sistema.")
        else:
            if modo_actual_remate == "Ciegos":
                carreras_filtradas_visibles = ["1V", "6V"]
            else:
                carreras_asignadas_admin = st.session_state.carreras_por_modalidad.get(modo_actual_remate, [])
                carreras_filtradas_visibles = [
                    c for c in lista_carreras_disponibles 
                    if c in carreras_asignadas_admin and ((c in st.session_state.carreras_activas_remate) or st.session_state.carreras_cerradas_remate.get(c, False))
                ]
            
            if not carreras_filtradas_visibles:
                st.info(f"ℹ️ No hay carreras asignadas o habilitadas para la modalidad **{modo_actual_remate}**. Configúralas en Zona Admin.")
            else:
                if "carrera_remate_activa_seleccionada" not in st.session_state or st.session_state["carrera_remate_activa_seleccionada"] not in carreras_filtradas_visibles:
                    carr_activa = carreras_filtradas_visibles[0]
                    st.session_state["carrera_remate_activa_seleccionada"] = carr_activa
                else:
                    carr_activa = st.session_state["carrera_remate_activa_seleccionada"]

                if carr_activa not in st.session_state.remates:
                    num_ej = 14 if modo_actual_remate == "Ciegos" else 10
                    st.session_state.remates[carr_activa] = {f"{j} - Ejemplar {j}": {"jugador": "Sin Postor", "monto": 0.0} for j in range(1, num_ej + 1)}

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

                carrera_real_mapeada = carr_activa
                if modo_actual_remate == "Ciegos":
                    mapeo = st.session_state.get('mapeo_ciegos', {})
                    carrera_real_mapeada = mapeo.get(carr_activa, "")
                    if carrera_real_mapeada and carrera_real_mapeada in st.session_state.banco_caballos_por_carrera:
                        banco_real = st.session_state.banco_caballos_por_carrera[carrera_real_mapeada]
                        total_real = len(banco_real)
                        monto_fijo_ciego = st.session_state.detalles_carreras.get(carr_activa, {}).get('monto_fijo_ciego', 500.0)
                        
                        if carrera_real_mapeada in st.session_state.historial_ganadores:
                            st.session_state.historial_ganadores[carr_activa] = st.session_state.historial_ganadores[carrera_real_mapeada]

                        if total_real < 14:
                            st.error(f"⚠️ La carrera mapeada ({carrera_real_mapeada}) tiene {total_real} ejemplares (< 14). ¡Las apuestas de este Remate Ciego han sido ANULADAS!")
                            for cb_k, cb_inf in st.session_state.remates[carr_activa].items():
                                if cb_inf['jugador'] != "Sin Postor" and cb_inf['jugador'] != "CASA":
                                    jug_ant = cb_inf['jugador']
                                    mnt_ant = cb_inf['monto']
                                    if jug_ant in st.session_state.cuentas:
                                        st.session_state.cuentas[jug_ant]['Pujas'] = max(0.0, st.session_state.cuentas[jug_ant]['Pujas'] - mnt_ant)
                                    st.session_state.remates[carr_activa][cb_k] = {"jugador": "Sin Postor", "monto": 0.0}
                            guardar_estado_global()
                        else:
                            for idx_h, caballo_real in enumerate(banco_real):
                                num_h = idx_h + 1
                                slot_ciego = f"{num_h} - Ejemplar {num_h}"
                                if slot_ciego in st.session_state.remates[carr_activa]:
                                    if num_h > 14:
                                        actual_postor = st.session_state.remates[carr_activa][slot_ciego]['jugador']
                                        if actual_postor == "Sin Postor":
                                            st.session_state.remates[carr_activa][slot_ciego] = {"jugador": "CASA", "monto": monto_fijo_ciego}

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
                
                info_mapeo_txt = f" (Mapeada a: {carrera_real_mapeada})" if (modo_actual_remate == "Ciegos" and carrera_real_mapeada) else ""
                st.markdown(f"""
                    <div style="font-size: 13px; font-weight: 800; color: #f0f6fc; display: flex; align-items: center; gap: 6px; margin-top: 6px; margin-bottom: 6px;">
                        <span>{estado_icono}</span>
                        <span>{carr_activa}{info_mapeo_txt}</span>
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

                dt_limite_efectivo = dt_limite
                if dt_limite and modo_actual_remate == "En Vivo":
                    dt_limite_efectivo = dt_limite - timedelta(seconds=10)

                if dt_inicio and carrera_cerrada:
                    if ahora_dt_frag >= dt_inicio:
                        st.session_state.carreras_cerradas_remate[carr_activa] = False
                        guardar_estado_global()
                        carrera_cerrada = False

                if dt_inicio:
                    st.markdown(f"<div style='background:#161b22; padding:5px; border-radius:5px; margin-bottom:3px; border:1px solid #30363d; font-size:11px;'>🟢 Inicio Remate ({modo_actual_remate}): <b>{dt_inicio.strftime('%d/%m/%Y - %I:%M %p')}</b></div>", unsafe_allow_html=True)
                if dt_limite:
                    aviso_en_vivo_txt = " (Cierra 10s antes)" if modo_actual_remate == "En Vivo" else ""
                    st.markdown(f"<div style='background:#161b22; padding:5px; border-radius:5px; margin-bottom:6px; border:1px solid #30363d; font-size:11px;'>⏰ Cierre Estricto ({modo_actual_remate}): <b>{dt_limite.strftime('%d/%m/%Y - %I:%M %p')}</b>{aviso_en_vivo_txt}</div>", unsafe_allow_html=True)

                if dt_limite_efectivo and not carrera_cerrada:
                    diferencia_segundos = (dt_limite_efectivo - ahora_dt_frag).total_seconds()
                    
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
                                        if (window.intervaloRelojVivo) {{ clearInterval(window.intervaloRelojVivo); }}
                                        if (window.parent.hablarNumero) {{ window.parent.hablarNumero(segs.toString()); }}
                                        window.intervaloRelojVivo = setInterval(function() {{
                                            segs--;
                                            if (segs > 0) {{
                                                if (digito) digito.innerText = segs;
                                                if (window.parent.hablarNumero) {{ window.parent.hablarNumero(segs.toString()); }}
                                            }} else {{
                                                if (digito) {{
                                                    digito.parentElement.style.borderColor = "#f1c40f";
                                                    digito.parentElement.style.background = "linear-gradient(135deg, #3d3100 0%, #161b22 100%)";
                                                    digito.parentElement.innerHTML = "<div style='color: #f1c40f; font-size: 14px; font-weight: 900; text-transform: uppercase; text-shadow: 0 0 6px #f1c40f; padding: 4px;'>🔒 ¡CERRADO EL REMATE, SUERTE! 🐎</div>";
                                                }}
                                                if (window.parent.hablarNumero) {{ window.parent.hablarNumero("Cerrado"); }}
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

                if modo_actual_remate == "Adelantados":
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
                else:
                    target_sync_key = carrera_real_mapeada if modo_actual_remate == "Ciegos" else carr_activa
                    if target_sync_key in st.session_state.ejemplares_retirados:
                        st.session_state.ejemplares_retirados[carr_activa] = st.session_state.ejemplares_retirados[target_sync_key]
                    if target_sync_key in st.session_state.get('ejemplares_no_valido', {}):
                        st.session_state.ejemplares_no_valido[carr_activa] = st.session_state.ejemplares_no_valido[target_sync_key]

                retirados_carr_activa = st.session_state.ejemplares_retirados.get(carr_activa, [])
                no_validos_carr_activa = st.session_state.ejemplares_no_valido.get(carr_activa, [])
                
                tabla_html = generar_tabla_html_remate(st.session_state.remates[carr_activa], retirados_carr_activa, no_validos_carr_activa)
                cantidad_filas = len(st.session_state.remates[carr_activa])
                altura_dinamica = min(max(130, (cantidad_filas * 32) + 45), 380)
                components.html(tabla_html, height=altura_dinamica, scrolling=True)
                
                excluidos_carr_activa = set(retirados_carr_activa) | set(no_validos_carr_activa)

                total_pote = sum([info['monto'] for cab_n, info in st.session_state.remates[carr_activa].items() if cab_n not in excluidos_carr_activa])
                porcentaje_casa_val = st.session_state.get('porcentaje_casa', 30)
                monto_casa = total_pote * (porcentaje_casa_val / 100)
                pote_neto_base = total_pote - monto_casa

                if modo_actual_remate == "Adelantados":
                    incentivo_actual = float(detalles_carr.get('incentivo_adelantados', 0.0))
                elif modo_actual_remate == "Ciegos":
                    incentivo_actual = float(detalles_carr.get('incentivo_ciegos', 0.0))
                else:
                    incentivo_actual = float(detalles_carr.get('incentivo_envivo', 0.0))

                premio_total_calculado = pote_neto_base + incentivo_actual

                st.markdown(f"""
                    <div class="dashboard-pote-card">
                        <div class="dp-header">🏆 PREMIO TOTAL (INCLUYE INCENTIVO)</div>
                        <div class="dp-total-value">{formatear_bs(premio_total_calculado)}</div>
                        <div class="dp-grid">
                            <div class="dp-item">
                                <span class="dp-label">💰 POTE ({carr_activa})</span>
                                <span class="dp-val" style="color: #f1c40f;">{formatear_bs(total_pote)}</span>
                            </div>
                            <div class="dp-divider"></div>
                            <div class="dp-item">
                                <span class="dp-label">🎁 INCENTIVO</span>
                                <span class="dp-val" style="color: #2ed573;">{formatear_bs(incentivo_actual)}</span>
                            </div>
                        </div>
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
                            <div style="color: #00ffff; font-size: 14px; font-weight: 900; margin-bottom: 3px;">🐎 EJEMPLAR: {caballo_ganador_str.upper()}</div>
                            <div class="ganador-premio-epic">💰 Premio Liquidado: {premio_ganado}</div>
                        </div>
                    """, unsafe_allow_html=True)

                if modo_actual_remate == "Adelantados":
                    with st.expander(f"GANADOR - {carr_activa}", expanded=False):
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
                                    monto_casa_calc = pote_carr_total * (porcentaje_casa_val / 100)
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

                fuera_de_horario = False
                if dt_inicio and ahora_dt_frag < dt_inicio:
                    fuera_de_horario = True
                    st.error("⏳ **REMATES CERRADOS:** Aún no es la hora de apertura para esta modalidad.")
                elif (dt_limite_efectivo and ahora_dt_frag >= dt_limite_efectivo) or carrera_cerrada:
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
        st.error(f"🔒 **CERRADO ESTRICTO:** El horario de emisión finalizó el {dt_cierre_m.strftime('%d/%m/%Y a las %I:%M %p')}.")

    if dt_inicio_m:
        st.markdown(f"<div style='background:#161b22; padding:5px; border-radius:5px; margin-bottom:3px; border:1px solid #30363d; font-size:11px;'>🟢 Apertura ({sub_dup_actual}): <b>{dt_inicio_m.strftime('%d/%m/%Y - %I:%M %p')}</b></div>", unsafe_allow_html=True)
    if dt_cierre_m:
        st.markdown(f"<div style='background:#161b22; padding:5px; border-radius:5px; margin-bottom:6px; border:1px solid #30363d; font-size:11px;'>⏰ Cierre Estricto ({sub_dup_actual}): <b>{dt_cierre_m.strftime('%d/%m/%Y - %I:%M %p')}</b></div>", unsafe_allow_html=True)

    if st.session_state.dupleta_bloqueada or bloqueo_por_horario:
        st.error("🔒 **BLOQUEADO:** Emisión cerrada temporalmente.")

    monto_unico_seccion = st.session_state.config_montos_especiales.get(sub_dup_actual, 500.0)

    if sub_dup_actual == "Dupleta":
        pote_total = sum([t['monto'] for t in st.session_state.dupletas_tickets if t.get('estado') == 'Pendiente'])
        carreras_permitidas = [c for c in st.session_state.carreras_habilitadas_dupleta if c in lista_carreras_disponibles]
    elif sub_dup_actual == "Tripleta":
        pote_total = sum([t['monto'] for t in st.session_state.tripleta_tickets if t.get('estado') == 'Pendiente'])
        carreras_permitidas = [c for c in st.session_state.carreras_habilitadas_tripleta if c in lista_carreras_disponibles]
    else: 
        pote_total = sum([t['monto'] for t in st.session_state.polla_tickets])
        total_c = st.session_state.get('total_carreras_semana', 10)
        inicio_p = max(1, total_c - 5)
        carreras_ult6 = [f"Carrera {i}" for i in range(inicio_p, total_c + 1)]
        carreras_permitidas = [c for c in carreras_ult6 if c in lista_carreras_disponibles]
        st.session_state.carreras_habilitadas_polla = carreras_permitidas

    st.markdown(f"""
        <div class="pote-cyber-card" style="background: linear-gradient(135deg, #0d1b2a 0%, #1b263b 100%); border: 2px solid #f1c40f; border-radius: 12px; padding: 12px; text-align: center; margin: 8px 0;">
            <div style="color: #00ffff; font-size: 11px; font-weight: 900; letter-spacing: 1px;">💰 POTE ACUMULADO DE {sub_dup_actual.upper()}</div>
            <div style="color: #f1c40f; font-size: 24px; font-weight: 900;">{formatear_bs(pote_total)}</div>
        </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(f"👤 **Jugador Activo:** `{st.session_state.usuario_activo}` &nbsp;|&nbsp; 💵 **Costo Ticket:** `{formatear_bs(monto_unico_seccion)}`")
        if sub_dup_actual == "POLLA HIPICA":
            st.markdown("<p style='color: #00ffff; font-size: 11px; font-weight: 700;'>ℹ️ <b>Regla de Polla Hípica:</b> Se juega en las últimas 6 carreras consecutivas. El pote se reparte equitativamente entre los máximos ganadores de puntos.</p>", unsafe_allow_html=True)
        st.markdown("---")

        if not carreras_permitidas:
            st.warning(f"⚠️ No hay carreras habilitadas para **{sub_dup_actual}**.")
        else:
            seleccion_legs = []
            valido_legs = True
            carreras_usadas = set()

            if sub_dup_actual == "POLLA HIPICA":
                st.markdown("🎯 **Selección de Ejemplares:**")
                for carr_leg in carreras_permitidas:
                    match_c = re.search(r'\d+', carr_leg)
                    num_c_str = match_c.group(0) if match_c else carr_leg
                    
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

                    st.markdown(f"🏁 **{carr_leg}**")
                    chunk_size = 7
                    for i_chunk in range(0, len(banco_cab_carr), chunk_size):
                        chunk_items = banco_cab_carr[i_chunk:i_chunk + chunk_size]
                        cols_g = st.columns(len(chunk_items), gap="small")
                        for idx_sub, cb_item in enumerate(chunk_items):
                            num_p = cb_item.split(" - ")[0]
                            es_excluido = cb_item in excluidos_carr_t
                            es_seleccionado = (st.session_state[k_sel_grid] == cb_item)

                            with cols_g[idx_sub]:
                                if es_excluido:
                                    st.button(f"❌ {num_p}", key=f"btn_g_{carr_leg}_{i_chunk}_{idx_sub}", disabled=True, use_container_width=True)
                                else:
                                    btn_type = "primary" if es_seleccionado else "secondary"
                                    if st.button(f"{num_p}", key=f"btn_g_{carr_leg}_{i_chunk}_{idx_sub}", type=btn_type, use_container_width=True):
                                        st.session_state[k_sel_grid] = cb_item
                                        st.rerun()

                    cab_leg = st.session_state[k_sel_grid]
                    seleccion_legs.append({"carrera": carr_leg, "ejemplar": cab_leg})
            else:
                cantidad_pasos = 2 if sub_dup_actual == "Dupleta" else 3
                for paso in range(cantidad_pasos):
                    st.markdown(f"🔹 **Paso {paso + 1} de {cantidad_pasos}**")
                    carr_leg = carreras_permitidas[paso % len(carreras_permitidas)]
                    
                    retirados_carr_t = st.session_state.ejemplares_retirados.get(carr_leg, [])
                    no_val_carr_t = st.session_state.get('ejemplares_no_valido', {}).get(carr_leg, [])
                    excluidos_carr_t = set(retirados_carr_t) | set(no_val_carr_t)

                    banco_cab_carr = st.session_state.banco_caballos_por_carrera.get(carr_leg, [])
                    caballos_in_carr = [c for c in banco_cab_carr if c not in excluidos_carr_t]
                    if not caballos_in_carr:
                        caballos_in_carr = banco_cab_carr if banco_cab_carr else ["1 - Ejemplar 1"]

                    cab_leg = st.selectbox(f"Selecciona el Ejemplar para {carr_leg}", options=caballos_in_carr, key=f"ticket_cab_{sub_dup_actual}_{paso}")

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

                            if sub_dup_actual == "Dupleta": st.session_state.dupletas_tickets.append(nuevo_ticket_dict)
                            elif sub_dup_actual == "Tripleta": st.session_state.tripleta_tickets.append(nuevo_ticket_dict)
                            else: st.session_state.polla_tickets.append(nuevo_ticket_dict)

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
                            st.success(f"✅ ¡Ticket {ticket_id} emitido con éxito!")
                            st.rerun()

    if sub_dup_actual == "POLLA HIPICA":
        st.markdown("---")
        st.markdown("### 🏆 Panel de Resultados y Tabla de Posiciones (Polla Hípica)")
        with st.container(border=True):
            carr_res_sel = st.selectbox("Seleccionar Carrera", carreras_permitidas, key="sel_carrera_resultado_polla")
            banco_caballos_carr = st.session_state.banco_caballos_por_carrera.get(carr_res_sel, [])
            
            col_res1, col_res2, col_res3 = st.columns(3)
            with col_res1: res_1ro = st.selectbox("1er Lugar (5 Ptos)", options=["Sin Asignar"] + banco_caballos_carr, key=f"res_1ro_{carr_res_sel}")
            with col_res2: res_2do = st.selectbox("2do Lugar (3 Ptos)", options=["Sin Asignar"] + banco_caballos_carr, key=f"res_2do_{carr_res_sel}")
            with col_res3: res_3ro = st.selectbox("3er Lugar (1 Pto)", options=["Sin Asignar"] + banco_caballos_carr, key=f"res_3ro_{carr_res_sel}")

            if st.button("💾 Guardar Resultados Oficiales Carrera", key=f"btn_guardar_res_{carr_res_sel}", type="primary"):
                if 'resultados_oficiales_polla' not in st.session_state: st.session_state.resultados_oficiales_polla = {}
                st.session_state.resultados_oficiales_polla[carr_res_sel] = {"1ro": res_1ro, "2do": res_2do, "3ro": res_3ro}
                guardar_estado_global()
                st.success(f"✅ Resultados de **{carr_res_sel}** guardados.")
                st.rerun()

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
            tabla_puntuaciones[t['id']] = {"ticket": t['id'], "jugador": t['jugador'], "puntos": puntos_ticket, "monto": t['monto'], "detalle": " | ".join(detalle_puntos) if detalle_puntos else "Sin puntos aún"}

        if tabla_puntuaciones:
            df_posiciones = pd.DataFrame(list(tabla_puntuaciones.values())).sort_values(by="puntos", ascending=False).reset_index(drop=True)
            df_posiciones.index = df_posiciones.index + 1
            st.dataframe(df_posiciones, use_container_width=True)

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
                    nuevo_reporte = {
                        "jugador": jugador_actual, "monto": monto_rep, "banco": banco_remitente,
                        "referencia": ref_pago, "fecha": ahora_dt.strftime('%d/%m/%Y %I:%M %p'), "estado": "Pendiente de Aprobación"
                    }
                    st.session_state.reportes_pago.append(nuevo_reporte)
                    idx_nuevo = len(st.session_state.reportes_pago) - 1
                    enviar_notificacion_telegram_pago(idx_nuevo, jugador_actual, monto_rep, banco_remitente, ref_pago)
                    guardar_estado_global()
                    st.success("✅ ¡Reporte enviado con éxito!")
                    st.rerun()
                else:
                    st.error("⚠️ Ingrese un monto válido y la referencia.")

# =========================================================================
# 4. ZONA DE ADMINISTRADOR
# =========================================================================
elif menu_principal_opcion == "🔒 Zona Admin":
    st.markdown("<div class='subasta-header'>🔒 Panel de Configuración y Administración</div>", unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "⚙️ Controles & Jornada", "✍️ Banco de Caballos", "👥 Usuarios", 
        "⚙️ Dupleta/Polla", "📺 Video", "📊 Saldos", "🖼️ Imágenes"
    ])

    with tab1:
        st.markdown("### ⚙️ Controles Generales de la Jornada")
        with st.container(border=True):
            usuario_seleccionado_admin = st.selectbox(
                "Cambiar de Usuario en Sesión",
                options=st.session_state.lista_usuarios,
                index=st.session_state.lista_usuarios.index(st.session_state.usuario_activo) if st.session_state.usuario_activo in st.session_state.lista_usuarios else 0,
                key="admin_select_usuario_activo"
            )
            if usuario_seleccionado_admin != st.session_state.usuario_activo:
                st.session_state.usuario_activo = usuario_seleccionado_admin
                guardar_estado_global()
                st.rerun()

        with st.container(border=True):
            porcentaje_casa_val = st.slider("Porcentaje de retención de la Casa (%)", 0, 50, int(st.session_state.get('porcentaje_casa', 30)), key="admin_slider_retencion_casa")
            if porcentaje_casa_val != st.session_state.get('porcentaje_casa', 30):
                st.session_state.porcentaje_casa = porcentaje_casa_val
                guardar_estado_global()

        with st.container(border=True):
            if st.button("🗑️ Reiniciar Toda la Jornada", key="admin_btn_reiniciar_jornada", use_container_width=True):
                keys_excluidos = ['banco_caballos_por_carrera', 'lista_usuarios', 'datos_pago_movil', 'reportes_pago', 'cuentas']
                for key in list(st.session_state.keys()):
                    if key not in keys_excluidos:
                        del st.session_state[key]
                guardar_estado_global()
                st.toast("🚨 Jornada reiniciada.")
                st.rerun()

    with tab2:
        st.markdown("### ✍️ Banco de Caballos")
        with st.container(border=True):
            nueva_cantidad_carreras = st.number_input("¿Cuántas carreras van a correr esta semana?", min_value=1, max_value=25, value=int(st.session_state.total_carreras_semana), step=1, key="input_total_carreras_semana")
            if st.button("💾 Actualizar Carreras", key="btn_actualizar_cant_carreras", use_container_width=True, type="primary"):
                st.session_state.total_carreras_semana = nueva_cantidad_carreras
                carreras_generadas = [f"Carrera {i}" for i in range(1, nueva_cantidad_carreras + 1)]
                for c_n in carreras_generadas:
                    if c_n not in st.session_state.banco_caballos_por_carrera:
                        st.session_state.banco_caballos_por_carrera[c_n] = [f"{j} - Ejemplar {j}" for j in range(1, 11)]
                    if c_n not in st.session_state.remates:
                        st.session_state.remates[c_n] = {f"{j} - Ejemplar {j}": {"jugador": "Sin Postor", "monto": 0.0} for j in range(1, 11)}
                st.session_state.carreras_activas_remate = list(carreras_generadas)
                guardar_estado_global()
                st.toast(f"✅ ¡Jornada ajustada a {nueva_cantidad_carreras} carreras!")
                st.rerun()

    with tab3:
        st.markdown("### 👥 Registro de Usuarios")
        with st.container(border=True):
            nuevo_usuario_input = st.text_input("Nuevo Usuario", placeholder="Ej: JUAN", key="input_nuevo_usuario_reg")
            if st.button("➕ Registrar", key="btn_registrar_nuevo_usuario", use_container_width=True, type="primary"):
                usuario_limpio = nuevo_usuario_input.strip().upper()
                if usuario_limpio and usuario_limpio not in st.session_state.lista_usuarios:
                    st.session_state.lista_usuarios.append(usuario_limpio)
                    if usuario_limpio not in st.session_state.cuentas:
                        st.session_state.cuentas[usuario_limpio] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                    guardar_estado_global()
                    st.rerun()

    with tab5:
        st.markdown("### 📺 Video en Vivo")
        with st.container(border=True):
            nueva_url_video = st.text_input("URL de YouTube", value=st.session_state.get('url_video_en_vivo', ''), key="input_live_video_url")
            if st.button("💾 Guardar URL de Video", key="btn_save_video_url", use_container_width=True, type="primary"):
                st.session_state.url_video_en_vivo = nueva_url_video.strip()
                guardar_estado_global()
                st.rerun()

    with tab7:
        st.markdown("### 🖼️ Imágenes por Carrera")
        todas_carrs_img = list(st.session_state.remates.keys())
        carr_img_sel = st.selectbox("Seleccionar Carrera para Imagen", todas_carrs_img, key="adm_img_sel_carr")
        with st.container(border=True):
            imagen_subida = st.file_uploader("Subir imagen", type=["png", "jpg", "jpeg"], key=f"file_img_{carr_img_sel}")
            if imagen_subida is not None:
                if st.button("💾 Guardar Imagen", key=f"btn_save_img_{carr_img_sel}", use_container_width=True, type="primary"):
                    try:
                        from PIL import Image
                        img_pil = Image.open(imagen_subida)
                        if img_pil.mode in ("RGBA", "P"): img_pil = img_pil.convert("RGB")
                        max_ancho = 800
                        if img_pil.width > max_ancho:
                            proporcion = max_ancho / img_pil.width
                            img_pil = img_pil.resize((max_ancho, int(img_pil.height * proporcion)), Image.Resampling.LANCZOS)
                        buffer = io.BytesIO()
                        img_pil.save(buffer, format="JPEG", quality=75)
                        b64_imagen = base64.b64encode(buffer.getvalue()).decode('utf-8')
                        st.session_state.imagenes_carreras[carr_img_sel] = f"data:image/jpeg;base64,{b64_imagen}"
                        guardar_estado_global()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

# =========================================================================
# TRANSMISIÓN EN VIVO GLOBAL
# =========================================================================
url_live_video = st.session_state.get('url_video_en_vivo', '').strip()
if url_live_video:
    st.markdown("<br><hr style='border-color: #30363d;'>", unsafe_allow_html=True)
    st.markdown("### 📺 TRANSMISIÓN EN VIVO")
    yt_match = re.search(r'(?:v=|\/embed\/|youtu\.be\/|\/v\/|\/e\/|watch\?v=|&v=)([^#&?]{11})', url_live_video)
    if yt_match:
        st.video(f"https://www.youtube.com/embed/{yt_match.group(1)}?playsinline=1")
    else:
        st.video(url_live_video)
