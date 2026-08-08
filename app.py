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

# --- VIGILANTE DE SINCRONIZACIÓN SEGURO (CADA 8 SEGUNDOS) ---
@st.fragment(run_every=8.0)
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

# --- ESTILOS CSS GENERALES Y DISEÑO MEJORADO DE POTES ---
st.markdown("""
    <style>
    * { box-sizing: border-box !important; }
    .stApp { background-color: #080a0f; color: #f0f6fc; overflow-x: hidden !important; }
    [data-testid="stSidebar"] { display: none !important; visibility: hidden !important; opacity: 0 !important; width: 0px !important; min-width: 0px !important; }
    [data-testid="stToolbar"] { display: none !important; visibility: hidden !important; opacity: 0 !important; pointer-events: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    footer, #MainMenu { visibility: hidden !important; display: none !important; }
    .block-container { padding-top: 0.2rem !important; padding-bottom: 1.5rem !important; padding-left: 0.3rem !important; padding-right: 0.3rem !important; max-width: 100% !important; margin: 0 auto !important; }
    
    div[data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; overflow-x: auto !important; overflow-y: hidden !important; -webkit-overflow-scrolling: touch !important; width: 100% !important; gap: 4px !important; padding-bottom: 4px !important; scrollbar-width: thin; }
    div[data-testid="stHorizontalBlock"] > div { flex: 0 0 auto !important; width: auto !important; min-width: 90px !important; max-width: none !important; }
    .carreras-scroll-container div[data-testid="stHorizontalBlock"] > div { min-width: 48px !important; width: 48px !important; }

    .stButton button { border-radius: 8px !important; font-weight: 800 !important; padding: 0.4rem 0.6rem !important; min-height: 42px !important; font-size: 12px !important; width: 100% !important; }
    div.stButton > button[kind="primary"] { background: linear-gradient(135deg, #f1c40f 0%, #d4ac0d 100%) !important; color: #080a0f !important; font-size: 15px !important; font-weight: 900 !important; border: 2px solid #ffffff !important; box-shadow: 0px 4px 18px rgba(241, 196, 15, 0.6) !important; text-transform: uppercase !important; }

    .subasta-header { font-size: clamp(13px, 3.2vw, 16px); font-weight: 800; color: #f1e05a; margin-bottom: 4px; border-bottom: 2px solid #f1e05a; padding-bottom: 2px; }
    .carrera-condicion-card { background-color: #161b22; border: 1px solid #30363d; padding: 8px 10px; border-radius: 6px; font-size: 11px; color: #f0f6fc; margin-bottom: 8px; line-height: 1.3; }
    
    .dashboard-pote-card { background: linear-gradient(135deg, #0d1b2a 0%, #1b263b 100%); border: 2px solid #f1c40f; border-radius: 12px; padding: 12px 14px; text-align: center; margin: 8px 0; box-shadow: 0px 4px 20px rgba(241, 196, 15, 0.25); width: 100%; box-sizing: border-box; }
    .dp-header { color: #00ffff; font-size: 11px; font-weight: 900; letter-spacing: 1.2px; text-transform: uppercase; margin-bottom: 4px; }
    .dp-total-value { color: #f1c40f; font-size: clamp(20px, 5.5vw, 28px); font-weight: 900; margin-bottom: 10px; }
    .dp-grid { display: flex; justify-content: space-around; align-items: center; border-top: 1px dashed rgba(241, 196, 15, 0.4); padding-top: 8px; gap: 8px; }
    .dp-item { display: flex; flex-direction: column; flex: 1; align-items: center; }
    .dp-divider { width: 1px; height: 26px; background-color: rgba(241, 196, 15, 0.4); }
    .dp-label { font-size: 9px; font-weight: 800; text-transform: uppercase; color: #8b949e; margin-bottom: 2px; }
    .dp-val { font-size: clamp(13px, 3.5vw, 16px); font-weight: 900; }

    @keyframes parpadeoGanador {
        0% {{ transform: scale(1); box-shadow: 0 0 12px #f1c40f, inset 0 0 12px #f1c40f; }}
        50% {{ transform: scale(1.02); box-shadow: 0 0 25px #00ffff, inset 0 0 18px #00ffff; }}
        100% {{ transform: scale(1); box-shadow: 0 0 12px #f1c40f, inset 0 0 12px #f1c40f; }}
    }
    .ganador-banner-epic { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); border: 2px solid #f1c40f; border-radius: 12px; padding: 12px; text-align: center; margin: 10px 0; animation: parpadeoGanador 2s infinite ease-in-out; }
    .ganador-titulo-epic { color: #00ffff; font-size: 12px; font-weight: 900; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 4px; }
    .ganador-nombre-epic { color: #f1c40f; font-size: 20px; font-weight: 900; letter-spacing: 0.8px; text-transform: uppercase; margin-bottom: 3px; }
    .ganador-premio-epic { color: #2ed573; font-size: 15px; font-weight: 900; }

    .ticket-jugador-card { background: #0d1117; border: 2px solid #30363d; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; box-shadow: 0px 3px 10px rgba(0,0,0,0.5); }
    .ticket-header-row { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #30363d; padding-bottom: 4px; margin-bottom: 6px; font-size: 11px; font-weight: 800; color: #f1c40f; }
    .ticket-body-row { font-size: 12px; color: #f0f6fc; margin-bottom: 3px; font-weight: 600; }
    
    .header-container-modern { background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); border: 1px solid #30363d; border-radius: 10px; padding: 10px 14px; margin-bottom: 8px; display: flex; flex-direction: column; gap: 10px; width: 100%; }
    .header-top-row { display: flex; justify-content: space-between; align-items: center; width: 100%; gap: 6px; }
    .header-user-card { display: flex; align-items: center; gap: 8px; background: #080a0f; border: 1px solid #30363d; padding: 4px 10px; border-radius: 6px; }
    .user-details { display: flex; flex-direction: column; text-align: right; }
    .u-name-container { display: flex; align-items: center; justify-content: flex-end; gap: 4px; }
    .u-name { color: #f0f6fc; font-size: 12px; font-weight: 800; }
    .u-bal { font-size: 10px; font-weight: 700; }
    .u-avatar-badge { width: 30px; height: 30px; background: #1f6feb; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; }
    .header-logo-img { max-height: 95px; width: auto; object-fit: contain; }
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

# --- CABECERA SUPERIOR ---
estado_global_remate = "cerrados" if all(st.session_state.carreras_cerradas_remate.get(c, False) for c in list(st.session_state.remates.keys())) and list(st.session_state.remates.keys()) else "abiertos"
led_clase_css = "led-rojo" if estado_global_remate == "cerrados" else "led-verde"

col_h_izq, _ = st.columns([1, 1], gap="small")
with col_h_izq:
    if st.button("💳 Reportar Pago Móvil", key="btn_ir_reportar_pago_top", use_container_width=True, type="primary"):
        st.session_state.menu_principal_opcion = "Cuentas"
        guardar_estado_global()
        st.rerun()

st.markdown(f"""
    <div class="header-container-modern" style="margin-top: 4px;">
        <div class="header-top-row">
            <div></div>
            <div class="header-user-card">
                <div class="user-details">
                    <div class="u-name-container">
                        <span class="u-name">{usuario_en_sesion}</span>
                        <span class="led-estado {led_clase_css}"></span>
                    </div>
                    <span class="u-bal" style="color: {color_balance};">{etiqueta_balance}</span>
                </div>
                <div class="u-avatar-badge">🐺</div>
            </div>
        </div>
        <div style="text-align: center; border-top: 1px solid #21262d; padding-top: 8px;">
            {logo_display}
        </div>
    </div>
""", unsafe_allow_html=True)

def obtener_abreviatura_carrera(nombre_carrera, modo_actual=""):
    if modo_actual == "Ciegos":
        return "1V" if nombre_carrera == "1V" else "6V"
    match = re.search(r'\d+', nombre_carrera)
    return f"C{match.group(0)}" if match else nombre_carrera[:3].upper()

def generar_tabla_html_remate(remates_dict, retirados_list, no_validos_list=[]):
    html = """
    <style>
        .tabla-referencia { width: 100%; border-collapse: collapse; font-family: sans-serif; background-color: #ffffff; color: #000000; margin-bottom: 8px; table-layout: fixed; }
        .tabla-referencia th { border-top: 2px solid #dfc729; border-bottom: 2px solid #dfc729; padding: 5px 3px; text-align: left; font-weight: 800; background-color: #ffffff; color: #000000; font-size: 10px; }
        .tabla-referencia td { border-bottom: 1px solid #dfc729; padding: 5px 3px; background-color: #fbfbfb; color: #111111; font-size: 10px; vertical-align: middle; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .badge-numero { display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 18px; font-weight: bold; font-size: 10px; border-radius: 2px; }
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
        num = int(match_num.group(1)) if match_num else 0
        nombre_solo = cab.split(" - ", 1)[1] if " - " in cab else cab
        
        es_retirado = cab in retirados_list
        es_novale = cab in no_validos_list
        clase_fila = "retirado-row" if es_retirado else ("novale-row" if es_novale else "")
        etiqueta_estado = " (RETIRADO)" if es_retirado else (" (NO VALE)" if es_novale else "")
        
        html += f"""
                <tr class="{clase_fila}">
                    <td><span class="badge-numero" style="background:#333; color:#fff;">{num}</span></td>
                    <td style="font-weight: 800; font-size: 11px;">{nombre_solo.upper()}{etiqueta_estado}</td>
                    <td>{info['jugador']}</td>
                    <td style="font-weight: bold;">{formatear_bs(info['monto'])}</td>
                </tr>
        """
    html += "</tbody></table></div>"
    return html

# --- MENÚ PRINCIPAL HORIZONTAL (MANTENIDO EXACTAMENTE IGUAL) ---
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

# --- BANNER Y MARQUESINA ---
elementos_carrusel_info = []
carreras_adelantados = [c for c in st.session_state.carreras_por_modalidad.get("Adelantados", []) if c in lista_carreras_disponibles]
if carreras_adelantados:
    elementos_carrusel_info.append("ADELANTADOS: " + " | ".join(carreras_adelantados))
elementos_carrusel_info.append("CIEGOS: 1V | 6V")
carreras_envivo = [c for c in st.session_state.carreras_por_modalidad.get("En Vivo", []) if c in lista_carreras_disponibles]
if carreras_envivo:
    elementos_carrusel_info.append("🔴 EN VIVO: " + " | ".join(carreras_envivo))

texto_unido_marquesina = " &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ".join(elementos_carrusel_info)
st.markdown(f'<div style="width: 100%; overflow: hidden; padding: 6px 0; font-family: Arial Black; font-size: 13px; color: #00ffff; text-transform: uppercase;">{texto_unido_marquesina}</div>', unsafe_allow_html=True)

if banner_b64:
    st.markdown(f'<div style="width: 100%; height: 160px; margin-bottom: 8px; border-radius: 6px; overflow:hidden;"><img src="data:image/png;base64,{banner_b64}" style="width: 100%; height: 100%; object-fit: cover;" /></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
menu_principal_opcion = st.session_state.menu_principal_opcion

# =========================================================================
# BLOQUE FRAGMENTADO UNIVERSAL EN TIEMPO REAL (INSTANTÁNEO)
# =========================================================================
@st.fragment(run_every=8.0)
def renderizar_tiempo_real_universal():
    cargar_estado_global(forzar_recarga=True)
    ahora_dt_frag = obtener_hora_venezuela_local()

    if st.session_state.menu_principal_opcion == "Remates":
        # SUBMENÚ HORIZONTAL DE REMATES MANTENIDO EXACTAMENTE IGUAL
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

        st.markdown("<hr style='margin: 0.2rem 0; border-color: #21262d;'>", unsafe_allow_html=True)
        modo_actual_remate = st.session_state.sub_remate_opcion

        if modo_actual_remate == "Ciegos":
            carreras_filtradas_visibles = ["1V", "6V"]
        else:
            carreras_asignadas_admin = st.session_state.carreras_por_modalidad.get(modo_actual_remate, [])
            carreras_filtradas_visibles = [c for c in lista_carreras_disponibles if c in carreras_asignadas_admin]

        if carreras_filtradas_visibles:
            carr_activa = st.session_state.get("carrera_remate_activa_seleccionada", carreras_filtradas_visibles[0])
            if carr_activa not in carreras_filtradas_visibles:
                carr_activa = carreras_filtradas_visibles[0]
                st.session_state["carrera_remate_activa_seleccionada"] = carr_activa

            # SELECCIONADOR DE CARRERAS HORIZONTAL (MANTENIDO IGUAL)
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

            if carr_activa not in st.session_state.remates:
                num_ej = 14 if modo_actual_remate == "Ciegos" else 10
                st.session_state.remates[carr_activa] = {f"{j} - Ejemplar {j}": {"jugador": "Sin Postor", "monto": 0.0} for j in range(1, num_ej + 1)}

            retirados_c = st.session_state.ejemplares_retirados.get(carr_activa, [])
            noval_c = st.session_state.ejemplares_no_valido.get(carr_activa, [])
            excluidos_c = set(retirados_c) | set(noval_c)

            tabla_html = generar_tabla_html_remate(st.session_state.remates[carr_activa], retirados_c, noval_c)
            components.html(tabla_html, height=min(max(130, (len(st.session_state.remates[carr_activa]) * 32) + 45), 380), scrolling=True)

            total_pote = sum([info['monto'] for cab_n, info in st.session_state.remates[carr_activa].items() if cab_n not in excluidos_c])
            porcentaje_casa_val = st.session_state.get('porcentaje_casa', 30)
            incentivo_actual = float(st.session_state.detalles_carreras.get(carr_activa, {}).get(f'incentivo_{modo_actual_remate.lower()}', 0.0))
            premio_total = (total_pote * (1 - porcentaje_casa_val / 100)) + incentivo_actual

            st.markdown(f"""
                <div class="dashboard-pote-card">
                    <div class="dp-header">🏆 PREMIO TOTAL (INCLUYE INCENTIVO)</div>
                    <div class="dp-total-value">{formatear_bs(premio_total)}</div>
                    <div class="dp-grid">
                        <div class="dp-item"><span class="dp-label">💰 POTE</span><span class="dp-val" style="color: #f1c40f;">{formatear_bs(total_pote)}</span></div>
                        <div class="dp-divider"></div>
                        <div class="dp-item"><span class="dp-label">🎁 INCENTIVO</span><span class="dp-val" style="color: #2ed573;">{formatear_bs(incentivo_actual)}</span></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            if carr_activa in st.session_state.historial_ganadores:
                ig = st.session_state.historial_ganadores[carr_activa]
                st.markdown(f"""
                    <div class="ganador-banner-epic">
                        <div class="ganador-titulo-epic">🏆 ¡RESULTADO OFICIAL - {carr_activa.upper()}! 🏆</div>
                        <div class="ganador-nombre-epic">🎉 {ig.get('Ganador', 'N/A')} 🎉</div>
                        <div style="color: #00ffff; font-size: 13px; font-weight: 900;">🐎 {ig.get('Caballo', '').upper()}</div>
                        <div class="ganador-premio-epic">💰 {ig.get('Premio', '0')}</div>
                    </div>
                """, unsafe_allow_html=True)

            if modo_actual_remate == "Adelantados":
                with st.expander(f"⚙️ Gestionar Retiros / Liquidar Ganador - {carr_activa}", expanded=False):
                    banco_c = st.session_state.banco_caballos_por_carrera.get(carr_activa, [])
                    n_ret = st.multiselect("Retirados", options=banco_c, default=[c for c in retirados_c if c in banco_c], key=f"ret_{carr_activa}")
                    n_nov = st.multiselect("No Valen", options=banco_c, default=[c for c in noval_c if c in banco_c], key=f"nov_{carr_activa}")
                    if st.button("💾 Guardar Retiros", key=f"btn_ret_{carr_activa}", type="primary"):
                        st.session_state.ejemplares_retirados[carr_activa] = n_ret
                        st.session_state.ejemplares_no_valido[carr_activa] = n_nov
                        guardar_estado_global()
                        st.rerun()

                    if carr_activa not in st.session_state.historial_ganadores:
                        cab_g = [c for c in list(st.session_state.remates[carr_activa].keys()) if c not in excluidos_c]
                        gan_sel = st.selectbox("Ganador", cab_g if cab_g else list(st.session_state.remates[carr_activa].keys()), key=f"gan_{carr_activa}")
                        if st.button("🏆 Liquidar", key=f"liq_{carr_activa}", type="primary"):
                            info_g = st.session_state.remates[carr_activa][gan_sel]
                            if info_g['jugador'] != "Sin Postor":
                                if info_g['jugador'] not in st.session_state.cuentas:
                                    st.session_state.cuentas[info_g['jugador']] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                                st.session_state.cuentas[info_g['jugador']]['Premios'] += premio_total
                            st.session_state.ganancia_casa += total_pote * (porcentaje_casa_val / 100)
                            st.session_state.historial_ganadores[carr_activa] = {"Ganador": info_g['jugador'], "Premio": formatear_bs(premio_total), "Caballo": gan_sel}
                            guardar_estado_global()
                            st.rerun()

            # Panel de Pujas Rápido
            st.markdown("---")
            lista_activos = [c for c in list(st.session_state.remates[carr_activa].keys()) if c not in excluidos_c]
            if lista_activos:
                k_sel = f"sel_cab_{carr_activa}"
                if k_sel not in st.session_state or st.session_state[k_sel] not in lista_activos:
                    st.session_state[k_sel] = lista_activos[0]
                
                sel_c = st.selectbox("Seleccionar Ejemplar para Pujar", lista_activos, key=k_sel)
                puja_actual = st.session_state.remates[carr_activa][sel_c]['monto']
                monto_p = st.selectbox("Monto de Puja", obtener_siguientes_montos(puja_actual), format_func=lambda x: formatear_bs(x), key=f"monto_{carr_activa}")
                
                if st.button(f"🔨 CONFIRMAR PUJA ({formatear_bs(monto_p)})", key=f"pujar_{carr_activa}", type="primary", use_container_width=True):
                    st.session_state.remates[carr_activa][sel_c] = {"jugador": usuario_en_sesion, "monto": monto_p}
                    if usuario_en_sesion not in st.session_state.cuentas:
                        st.session_state.cuentas[usuario_en_sesion] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                    st.session_state.cuentas[usuario_en_sesion]['Pujas'] += monto_p
                    guardar_estado_global()
                    st.success("✅ ¡Puja registrada!")
                    st.rerun()

renderizar_tiempo_real_universal()

# =========================================================================
# MÓDULOS SECUNDARIOS (DUPLETAS, CUENTAS, ADMIN)
# =========================================================================
if menu_principal_opcion == "Dupletas":
    st.markdown("<div class='subasta-header'>🎟️ Módulo de Dupleta, Tripleta y Polla Hípica</div>", unsafe_allow_html=True)
    col_d1, col_d2, col_d3 = st.columns(3, gap="small")
    with col_d1:
        if st.button("Dupleta", key="d_dup", use_container_width=True, type="primary" if st.session_state.sub_dupleta_opcion == "Dupleta" else "secondary"):
            st.session_state.sub_dupleta_opcion = "Dupleta"
            guardar_estado_global()
            st.rerun()
    with col_d2:
        if st.button("Tripleta", key="d_tri", use_container_width=True, type="primary" if st.session_state.sub_dupleta_opcion == "Tripleta" else "secondary"):
            st.session_state.sub_dupleta_opcion = "Tripleta"
            guardar_estado_global()
            st.rerun()
    with col_d3:
        if st.button("POLLA", key="d_pol", use_container_width=True, type="primary" if st.session_state.sub_dupleta_opcion == "POLLA HIPICA" else "secondary"):
            st.session_state.sub_dupleta_opcion = "POLLA HIPICA"
            guardar_estado_global()
            st.rerun()

    sub_dup = st.session_state.sub_dupleta_opcion
    monto_tkt = st.session_state.config_montos_especiales.get(sub_dup, 500.0)
    pote_m = sum([t['monto'] for t in (st.session_state.dupletas_tickets if sub_dup=="Dupleta" else st.session_state.tripleta_tickets if sub_dup=="Tripleta" else st.session_state.polla_tickets) if t.get('estado')=='Pendiente'])

    st.markdown(f"""
        <div class="pote-cyber-card">
            <div class="dp-header">POTE ACUMULADO DE {sub_dup}</div>
            <div class="dp-total-value">{formatear_bs(pote_m)}</div>
        </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(f"👤 Jugador: `{usuario_en_sesion}` | Costo: `{formatear_bs(monto_tkt)}`")
        if st.button(f"🚀 Emitir Ticket de {sub_dup}", key="emitir_tkt", type="primary", use_container_width=True):
            ticket_id = f"TKT-{len(st.session_state.dupletas_tickets)+1:04d}"
            nuevo_t = {"id": ticket_id, "jugador": usuario_en_sesion, "monto": monto_tkt, "legs": [{"carrera": "Carrera 1", "ejemplar": "1 - Ejemplar 1"}], "estado": "Pendiente", "fecha": ahora_dt.strftime('%d/%m %I:%M %p')}
            st.session_state.dupletas_tickets.append(nuevo_t)
            st.session_state.cuentas[usuario_en_sesion]['Pujas'] += monto_tkt
            guardar_estado_global()
            st.success("✅ ¡Ticket emitido con éxito!")
            st.rerun()

elif menu_principal_opcion == "Cuentas":
    st.markdown("<div class='subasta-header'>📊 Mis Cuentas y Reporte de Pago Móvil</div>", unsafe_allow_html=True)
    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    col_c1.metric("Compras", formatear_bs(vals_sesion['Pujas']))
    col_c2.metric("Premios", formatear_bs(vals_sesion['Premios']))
    col_c3.metric("Pagos", formatear_bs(vals_sesion['Abonos']))
    col_c4.metric("Neto", formatear_bs(neto_usuario))

    with st.container(border=True):
        st.markdown("📱 **Datos para Pago Móvil**")
        pm = st.session_state.datos_pago_movil
        st.info(f"Banco: {pm['banco']} | Teléfono: {pm['telefono']} | Cédula: {pm['cedula']}")
        
        with st.form("rep_pago"):
            m_p = st.number_input("Monto (Bs.)", min_value=1.0, step=100.0)
            ref_p = st.text_input("Referencia (Últimos 4 dígitos)")
            if st.form_submit_button("📤 Enviar Reporte", type="primary"):
                if m_p > 0 and ref_p:
                    st.session_state.reportes_pago.append({"jugador": usuario_en_sesion, "monto": m_p, "banco": pm['banco'], "referencia": ref_p, "fecha": ahora_dt.strftime('%d/%m %I:%M'), "estado": "Pendiente"})
                    enviar_notificacion_telegram_pago(0, usuario_en_sesion, m_p, pm['banco'], ref_p)
                    guardar_estado_global()
                    st.success("✅ Reporte enviado.")
                    st.rerun()

elif menu_principal_opcion == "🔒 Zona Admin":
    st.markdown("<div class='subasta-header'>🔒 Panel de Administración</div>", unsafe_allow_html=True)
    at1, at2, at3 = st.tabs(["⚙️ Controles", "✍️ Caballos", "📊 Saldos"])
    with at1:
        us_sel = st.selectbox("Usuario Activo", st.session_state.lista_usuarios, key="adm_u_act")
        if us_sel != st.session_state.usuario_activo:
            st.session_state.usuario_activo = us_sel
            guardar_estado_global()
            st.rerun()
    with at2:
        st.markdown("Gestión de banco de caballos.")
    with at3:
        st.metric("Ganancia Total Casa", formatear_bs(st.session_state.ganancia_casa))
