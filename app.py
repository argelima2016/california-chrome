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
import firebase_admin
from firebase_admin import credentials, messaging
from PIL import Image

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
    st.error("⚠️ **ADVERTENCIA CRÍTICA:** No hay conexión con Supabase. Los datos entre la PC y los teléfonos no se sincronizarán.")

# --- INICIALIZACIÓN DE FIREBASE ADMIN (SEGURIZADO CON SECRETS) ---
if not firebase_admin._apps:
    try:
        if "firebase" in st.secrets:
            firebase_secrets = dict(st.secrets["firebase"])
            cred = credentials.Certificate(firebase_secrets)
            firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"⚠️ Error al inicializar Firebase Admin: {e}")

def enviar_notificacion_push(fcm_token: str, titulo: str, cuerpo: str):
    if not fcm_token or fcm_token == "Sin Token":
        return False
    try:
        message = messaging.Message(
            notification=messaging.Notification(title=titulo, body=cuerpo),
            token=fcm_token,
        )
        response = messaging.send(message)
        print("Notificación enviada exitosamente:", response)
        return True
    except Exception as e:
        print(f"Error al enviar notificación: {e}")
        return False

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
                [{"text": "🔗 ABRIR PANEL DE PAGOS EN LA APP", "url": URL_DE_TU_APP}]
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

# --- SCRIPT JS GLOBAL PARA AUDIO Y VOZ ---
components.html(r"""
    <script>
        let audioCtxGlobal = null;
        function inicializarAudio() {
            if (!audioCtxGlobal) {
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                if (AudioContext) { audioCtxGlobal = new AudioContext(); }
            }
            if (audioCtxGlobal && audioCtxGlobal.state === 'suspended') { audioCtxGlobal.resume(); }
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

        function sincronizacionEnVivo() {
            const doc = window.parent.document;
            const selectors = ['header[data-testid="stHeader"]', 'footer', '.stDeployButton', 'div[data-testid="stStatusWidget"]', '[data-testid="stToolbar"]', '#MainMenu', 'a[href*="streamlit.io"]'];
            selectors.forEach(selector => {
                doc.querySelectorAll(selector).forEach(el => {
                    if (el) { el.style.display = 'none'; el.style.visibility = 'hidden'; el.style.opacity = '0'; el.remove(); }
                });
            });
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
        if logo_b64: break

logo_display = f'<img src="data:image/png;base64,{logo_b64}" class="header-logo-img" />' if logo_b64 else '<span style="color: #f1c40f; font-size: 28px; font-weight: 900;">WOLF READY TO RUN</span>'
banner_b64 = cargar_base64_archivo("Gemini_Generated_Image_mn48tzmn48tzmn48.png")

# Inicialización de remates
if not st.session_state.remates:
    for i in range(1, st.session_state.total_carreras_semana + 1):
        carr_nombre = f"Carrera {i}"
        st.session_state.banco_caballos_por_carrera[carr_nombre] = [f"{j} - Ejemplar {j}" for j in range(1, 11)]
        st.session_state.remates[carr_nombre] = {f"{j} - Ejemplar {j}": {"jugador": "Sin Postor", "monto": 0.0} for j in range(1, 11)}
        st.session_state.detalles_carreras[carr_nombre] = {"condicion": "Condición estándar", "distancia": "1200 mts", "hora": "02:00 PM", "monto_fijo_ciego": 500.0, "incentivo_adelantados": 0.0, "incentivo_ciegos": 0.0, "incentivo_envivo": 0.0, "hora_cierre_real": "No registrada"}

for ciego_key in ["1V", "6V"]:
    if ciego_key not in st.session_state.remates:
        st.session_state.banco_caballos_por_carrera[ciego_key] = [f"{j} - Ejemplar {j}" for j in range(1, 15)]
        st.session_state.remates[ciego_key] = {f"{j} - Ejemplar {j}": {"jugador": "Sin Postor", "monto": 0.0} for j in range(1, 15)}
        st.session_state.detalles_carreras[ciego_key] = {"condicion": f"Remate Ciego {ciego_key}", "distancia": "1200 mts", "hora": "02:00 PM", "monto_fijo_ciego": 500.0, "incentivo_adelantados": 0.0, "incentivo_ciegos": 0.0, "incentivo_envivo": 0.0, "hora_cierre_real": "No registrada"}

if "1V" not in st.session_state.carreras_por_modalidad.get("Ciegos", []):
    st.session_state.carreras_por_modalidad["Ciegos"] = ["1V", "6V"]

lista_carreras_disponibles = [c for c in st.session_state.remates.keys() if c not in ["1V", "6V"]]
total_carrs = st.session_state.get('total_carreras_semana', 10)
inicio_polla_idx = max(1, total_carrs - 5)
st.session_state.carreras_habilitadas_polla = [f"Carrera {i}" for i in range(inicio_polla_idx, total_carrs + 1) if f"Carrera {i}" in st.session_state.remates]

ahora_dt = obtener_hora_venezuela_local()

# Estilos CSS generales
st.markdown("""
    <style>
    * { box-sizing: border-box !important; }
    .stApp { background-color: #080a0f; color: #f0f6fc; overflow-x: hidden !important; }
    [data-testid="stSidebar"], [data-testid="stToolbar"], header[data-testid="stHeader"], footer, #MainMenu { display: none !important; visibility: hidden !important; }
    .block-container { padding-top: 0.2rem !important; padding-bottom: 1.5rem !important; max-width: 100% !important; }
    div[data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; overflow-x: auto !important; width: 100% !important; gap: 4px !important; }
    .stButton button { border-radius: 8px !important; font-weight: 800 !important; min-height: 42px !important; font-size: 12px !important; width: 100% !important; }
    div.stButton > button[kind="primary"] { background: linear-gradient(135deg, #f1c40f 0%, #d4ac0d 100%) !important; color: #080a0f !important; font-weight: 900 !important; border: 2px solid #ffffff !important; }
    .subasta-header { font-size: 15px; font-weight: 800; color: #f1e05a; margin-bottom: 4px; border-bottom: 2px solid #f1e05a; padding-bottom: 2px; }
    .dashboard-pote-card { background: linear-gradient(135deg, #0d1b2a 0%, #1b263b 100%); border: 2px solid #f1c40f; border-radius: 12px; padding: 12px; text-align: center; margin: 8px 0; }
    .dp-total-value { color: #f1c40f; font-size: 24px; font-weight: 900; }
    .ticket-jugador-card { background: #0d1117; border: 2px solid #30363d; border-radius: 8px; padding: 10px; margin-bottom: 8px; }
    .header-container-modern { background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); border: 1px solid #30363d; border-radius: 10px; padding: 10px; margin-bottom: 8px; }
    .header-user-card { display: flex; align-items: center; gap: 8px; background: #080a0f; border: 1px solid #30363d; padding: 4px 10px; border-radius: 6px; }
    .led-estado { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
    .led-verde { background-color: #2ed573; box-shadow: 0 0 6px #2ed573; }
    .led-rojo { background-color: #ff4757; box-shadow: 0 0 6px #ff4757; }
    .header-logo-img { max-height: 80px; width: auto; object-fit: contain; }
    </style>
""", unsafe_allow_html=True)

usuario_en_sesion = st.session_state.usuario_activo
if usuario_en_sesion not in st.session_state.cuentas:
    st.session_state.cuentas[usuario_en_sesion] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}

vals_sesion = st.session_state.cuentas[usuario_en_sesion]
neto_usuario = vals_sesion['Pujas'] - vals_sesion['Abonos'] - vals_sesion['Premios']
etiqueta_balance = f"Deuda: {formatear_bs(neto_usuario)}" if neto_usuario > 0 else (f"Premio: {formatear_bs(abs(neto_usuario))}" if neto_usuario < 0 else "Al día: Bs. 0,00")
color_balance = "#ff4757" if neto_usuario > 0 else ("#2ed573" if neto_usuario < 0 else "#58a6ff")

# --- CABECERA SUPERIOR ---
col_h_izq, col_h_der = st.columns([1, 1], gap="small")
with col_h_izq:
    if st.button("💳 Reportar Pago Móvil", key="btn_ir_reportar_pago_top", use_container_width=True, type="primary"):
        st.session_state.menu_principal_opcion = "Cuentas"
        guardar_estado_global()
        st.rerun()

st.markdown(f"""
    <div class="header-container-modern">
        <div style="display: flex; justify-content: flex-end; align-items: center;">
            <div class="header-user-card">
                <div style="display: flex; flex-direction: column; text-align: right;">
                    <div style="display: flex; align-items: center; justify-content: flex-end; gap: 4px;">
                        <span style="color: #f0f6fc; font-size: 12px; font-weight: 800;">{usuario_en_sesion}</span>
                        <span class="led-estado led-verde"></span>
                    </div>
                    <span style="font-size: 10px; font-weight: 700; color: {color_balance};">{etiqueta_balance}</span>
                </div>
                <div style="width: 30px; height: 30px; background: #1f6feb; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px;">🐺</div>
            </div>
        </div>
        <div style="text-align: center; border-top: 1px solid #21262d; padding-top: 8px; margin-top: 6px;">
            {logo_display}
        </div>
    </div>
""", unsafe_allow_html=True)

def obtener_abreviatura_carrera(nombre_carrera, modo_actual=""):
    if modo_actual == "Ciegos":
        return nombre_carrera
    match = re.search(r'\d+', nombre_carrera)
    return f"C{match.group(0)}" if match else nombre_carrera[:3].upper()

def generar_tabla_html_remate(remates_dict, retirados_list, no_validos_list=[]):
    html = """
    <style>
        .tabla-referencia { width: 100%; border-collapse: collapse; font-family: sans-serif; background-color: #ffffff; color: #000000; margin-bottom: 8px; }
        .tabla-referencia th { border-top: 2px solid #dfc729; border-bottom: 2px solid #dfc729; padding: 5px 3px; text-align: left; font-weight: 800; font-size: 10px; background: #fff; }
        .tabla-referencia td { border-bottom: 1px solid #dfc729; padding: 5px 3px; background: #fbfbfb; font-size: 10px; }
        .retirado-row td { background-color: #ffe6e6 !important; color: #990000 !important; text-decoration: line-through; }
        .novale-row td { background-color: #fff3cd !important; color: #856404 !important; font-style: italic; }
    </style>
    <div style="background-color: #ffffff; padding: 2px; border-radius: 6px; overflow-x: auto;">
        <table class="tabla-referencia">
            <thead><tr><th style="width: 12%;">No</th><th style="width: 35%;">Ejemplar</th><th style="width: 25%;">Comprador</th><th style="width: 28%;">Monto</th></tr></thead>
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
        html += f'<tr class="{clase_fila}"><td>{num}</td><td style="font-weight: 800;">{nombre_solo.upper()}{etiqueta_estado}</td><td>{info["jugador"]}</td><td>{formatear_bs(info["monto"])}</td></tr>'
    html += "</tbody></table></div>"
    return html

# --- MENÚ PRINCIPAL HORIZONTAL ---
col_menu1, col_menu2, col_menu3, col_menu4 = st.columns(4, gap="small")
with col_menu1:
    if st.button("REMATES", key="m_rem", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Remates" else "secondary"):
        st.session_state.menu_principal_opcion = "Remates"
        guardar_estado_global()
        st.rerun()
with col_menu2:
    if st.button("DUPLETA", key="m_dup", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Dupletas" else "secondary"):
        st.session_state.menu_principal_opcion = "Dupletas"
        guardar_estado_global()
        st.rerun()
with col_menu3:
    if st.button("CUENTAS", key="m_cue", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Cuentas" else "secondary"):
        st.session_state.menu_principal_opcion = "Cuentas"
        guardar_estado_global()
        st.rerun()
with col_menu4:
    if st.button("⚙️ CONFIG", key="m_cfg", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "🔒 Zona Admin" else "secondary"):
        st.session_state.menu_principal_opcion = "🔒 Zona Admin"
        guardar_estado_global()
        st.rerun()

st.markdown("<hr style='margin: 0.2rem 0; border-color: #21262d;'>", unsafe_allow_html=True)
menu_principal_opcion = st.session_state.menu_principal_opcion

# =========================================================================
# 1. MÓDULO DE REMATES
# =========================================================================
if menu_principal_opcion == "Remates":
    col_so1, col_so2, col_so3 = st.columns(3, gap="small")
    with col_so1:
        if st.button("Adelantados", key="s_adel", use_container_width=True, type="primary" if st.session_state.sub_remate_opcion == "Adelantados" else "secondary"):
            st.session_state.sub_remate_opcion = "Adelantados"
            guardar_estado_global()
            st.rerun()
    with col_so2:
        if st.button("Ciegos", key="s_cieg", use_container_width=True, type="primary" if st.session_state.sub_remate_opcion == "Ciegos" else "secondary"):
            st.session_state.sub_remate_opcion = "Ciegos"
            guardar_estado_global()
            st.rerun()
    with col_so3:
        if st.button("🔴 En Vivo", key="s_envi", use_container_width=True, type="primary" if st.session_state.sub_remate_opcion == "En Vivo" else "secondary"):
            st.session_state.sub_remate_opcion = "En Vivo"
            guardar_estado_global()
            st.rerun()

    st.markdown("<hr style='margin: 0.2rem 0; border-color: #21262d;'>", unsafe_allow_html=True)
    modo_actual_remate = st.session_state.sub_remate_opcion

    carreras_filtradas_visibles = ["1V", "6V"] if modo_actual_remate == "Ciegos" else [c for c in lista_carreras_disponibles if c in st.session_state.carreras_por_modalidad.get(modo_actual_remate, [])]
    
    if not carreras_filtradas_visibles:
        st.info(f"ℹ️ No hay carreras configuradas para **{modo_actual_remate}**. Ve a **⚙️ CONFIG > ✍️ Banco de Caballos** para asignarlas.")
    else:
        if "carrera_remate_activa_seleccionada" not in st.session_state or st.session_state["carrera_remate_activa_seleccionada"] not in carreras_filtradas_visibles:
            st.session_state["carrera_remate_activa_seleccionada"] = carreras_filtradas_visibles[0]
        
        carr_activa = st.session_state["carrera_remate_activa_seleccionada"]

        cols_carreras = st.columns(len(carreras_filtradas_visibles), gap="small")
        for idx, c_nombre in enumerate(carreras_filtradas_visibles):
            with cols_carreras[idx]:
                if st.button(obtener_abreviatura_carrera(c_nombre, modo_actual_remate), key=f"c_btn_{idx}", use_container_width=True, type="primary" if c_nombre == carr_activa else "secondary"):
                    st.session_state["carrera_remate_activa_seleccionada"] = c_nombre
                    guardar_estado_global()
                    st.rerun()

        st.markdown("---")
        retirados_carr_activa = st.session_state.ejemplares_retirados.get(carr_activa, [])
        no_validos_carr_activa = st.session_state.ejemplares_no_valido.get(carr_activa, [])
        
        tabla_html = generar_tabla_html_remate(st.session_state.remates[carr_activa], retirados_carr_activa, no_validos_carr_activa)
        components.html(tabla_html, height=220, scrolling=True)

        total_pote = sum([info['monto'] for cab_n, info in st.session_state.remates[carr_activa].items() if cab_n not in (set(retirados_carr_activa) | set(no_validos_carr_activa))])
        st.markdown(f"""
            <div class="dashboard-pote-card">
                <div style="color: #00ffff; font-size: 11px; font-weight: 900;">🏆 POTE TOTAL</div>
                <div class="dp-total-value">{formatear_bs(total_pote)}</div>
            </div>
        """, unsafe_allow_html=True)

# =========================================================================
# 2. MÓDULO DE DUPLETA, TRIPLETA Y POLLA HÍPICA
# =========================================================================
elif menu_principal_opcion == "Dupletas":
    col_d1, col_d2, col_d3 = st.columns(3, gap="small")
    with col_d1:
        if st.button("🎟️ Dupleta", key="d_dup", use_container_width=True, type="primary" if st.session_state.sub_dupleta_opcion == "Dupleta" else "secondary"):
            st.session_state.sub_dupleta_opcion = "Dupleta"
            guardar_estado_global()
            st.rerun()
    with col_d2:
        if st.button("🎟️ Tripleta", key="d_tri", use_container_width=True, type="primary" if st.session_state.sub_dupleta_opcion == "Tripleta" else "secondary"):
            st.session_state.sub_dupleta_opcion = "Tripleta"
            guardar_estado_global()
            st.rerun()
    with col_d3:
        if st.button("🏇 POLLA", key="d_pol", use_container_width=True, type="primary" if st.session_state.sub_dupleta_opcion == "POLLA HIPICA" else "secondary"):
            st.session_state.sub_dupleta_opcion = "POLLA HIPICA"
            guardar_estado_global()
            st.rerun()

    st.markdown("<hr style='margin: 0.2rem 0; border-color: #21262d;'>", unsafe_allow_html=True)
    sub_dup_actual = st.session_state.sub_dupleta_opcion

    st.markdown(f"<div class='subasta-header'>🎟️ Armado de {sub_dup_actual}</div>", unsafe_allow_html=True)
    pote_total = sum([t['monto'] for t in (st.session_state.dupletas_tickets if sub_dup_actual == "Dupleta" else st.session_state.tripleta_tickets if sub_dup_actual == "Tripleta" else st.session_state.polla_tickets)])
    
    st.markdown(f"""
        <div class="dashboard-pote-card">
            <div style="color: #00ffff; font-size: 11px; font-weight: 900;">💰 POTE ACUMULADO</div>
            <div class="dp-total-value">{formatear_bs(pote_total)}</div>
        </div>
    """, unsafe_allow_html=True)

# =========================================================================
# 3. MÓDULO DE CUENTAS
# =========================================================================
elif menu_principal_opcion == "Cuentas":
    st.markdown("<div class='subasta-header'>📊 Mis Cuentas y Reporte de Pago Móvil</div>", unsafe_allow_html=True)
    jugador_actual = st.session_state.usuario_activo
    vals = st.session_state.cuentas.get(jugador_actual, {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0})
    
    col_cu1, col_cu2, col_cu3, col_cu4 = st.columns(4, gap="small")
    col_cu1.metric("🛒 Compras", formatear_bs(vals['Pujas']))
    col_cu2.metric("🏆 Premios", formatear_bs(vals['Premios']))
    col_cu3.metric("💳 Pagos", formatear_bs(vals['Abonos']))
    col_cu4.metric("⚖️ Neto", formatear_bs(vals['Pujas'] - vals['Abonos'] - vals['Premios']))

# =========================================================================
# 4. ZONA DE ADMINISTRADOR (CON TODAS LAS PESTAÑAS COMPLETAS)
# =========================================================================
elif menu_principal_opcion == "🔒 Zona Admin":
    st.markdown("<div class='subasta-header'>🔒 Panel de Configuración y Administración</div>", unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "⚙️ Controles", "✍️ Caballos", "👥 Usuarios", "⚙️ Dupleta/Polla", "📺 Video", "📊 Saldos", "🖼️ Imágenes"
    ])

    with tab1:
        st.markdown("### ⚙️ Controles Generales de la Jornada")
        usuario_seleccionado_admin = st.selectbox("Usuario Activo", options=st.session_state.lista_usuarios, index=st.session_state.lista_usuarios.index(st.session_state.usuario_activo))
        if usuario_seleccionado_admin != st.session_state.usuario_activo:
            st.session_state.usuario_activo = usuario_seleccionado_admin
            guardar_estado_global()
            st.rerun()
        
        porcentaje_casa_val = st.slider("Porcentaje de retención de la casa (%)", 0, 50, int(st.session_state.get('porcentaje_casa', 30)))
        if porcentaje_casa_val != st.session_state.get('porcentaje_casa', 30):
            st.session_state.porcentaje_casa = porcentaje_casa_val
            guardar_estado_global()

    with tab2:
        st.markdown("### ✍️ Banco de Caballos y Asignación por Modalidad")
        nueva_cantidad_carreras = st.number_input("Total de carreras de la semana", min_value=1, max_value=25, value=int(st.session_state.total_carreras_semana), step=1)
        if st.button("💾 Actualizar Total de Carreras", type="primary"):
            st.session_state.total_carreras_semana = nueva_cantidad_carreras
            carreras_generadas = [f"Carrera {i}" for i in range(1, nueva_cantidad_carreras + 1)]
            for c_n in carreras_generadas:
                if c_n not in st.session_state.banco_caballos_por_carrera:
                    st.session_state.banco_caballos_por_carrera[c_n] = [f"{j} - Ejemplar {j}" for j in range(1, 11)]
                if c_n not in st.session_state.remates:
                    st.session_state.remates[c_n] = {f"{j} - Ejemplar {j}": {"jugador": "Sin Postor", "monto": 0.0} for j in range(1, 11)}
            guardar_estado_global()
            st.success("¡Carreras actualizadas!")
            st.rerun()

        st.markdown("---")
        carreras_existentes = [c for c in st.session_state.banco_caballos_por_carrera.keys() if c not in ["1V", "6V"]]
        modalidades_dict = st.session_state.carreras_por_modalidad
        
        sel_adel = st.multiselect("Carreras para Adelantados", options=carreras_existentes, default=[c for c in modalidades_dict.get("Adelantados", []) if c in carreras_existentes])
        sel_envivo = st.multiselect("Carreras para 🔴 En Vivo", options=carreras_existentes, default=[c for c in modalidades_dict.get("En Vivo", []) if c in carreras_existentes])

        if st.button("💾 Guardar Asignación de Carreras", type="primary"):
            st.session_state.carreras_por_modalidad["Adelantados"] = sel_adel
            st.session_state.carreras_por_modalidad["En Vivo"] = sel_envivo
            guardar_estado_global()
            st.success("¡Asignaciones guardadas con éxito!")
            st.rerun()

    with tab3:
        st.markdown("### 👥 Registro y Gestión de Usuarios")
        nuevo_usuario_input = st.text_input("Nuevo Usuario", placeholder="Ej: JUAN")
        if st.button("➕ Registrar Usuario", type="primary"):
            usuario_limpio = nuevo_usuario_input.strip().upper()
            if usuario_limpio and usuario_limpio not in st.session_state.lista_usuarios:
                st.session_state.lista_usuarios.append(usuario_limpio)
                st.session_state.cuentas[usuario_limpio] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                guardar_estado_global()
                st.success(f"¡Usuario {usuario_limpio} registrado!")
                st.rerun()

    with tab4:
        st.markdown("### ⚙️ Configuración de Montos Múltiples")
        st.session_state.config_montos_especiales["Dupleta"] = st.number_input("Dupleta (Bs.)", value=float(st.session_state.config_montos_especiales.get("Dupleta", 500.0)), step=50.0)
        st.session_state.config_montos_especiales["Tripleta"] = st.number_input("Tripleta (Bs.)", value=float(st.session_state.config_montos_especiales.get("Tripleta", 500.0)), step=50.0)
        st.session_state.config_montos_especiales["POLLA HIPICA"] = st.number_input("Polla Hípica (Bs.)", value=float(st.session_state.config_montos_especiales.get("POLLA HIPICA", 1000.0)), step=50.0)
        if st.button("💾 Guardar Montos", type="primary"):
            guardar_estado_global()
            st.success("¡Montos guardados!")

    with tab5:
        st.markdown("### 📺 Transmisión en Vivo")
        nueva_url = st.text_input("URL de YouTube en Vivo", value=st.session_state.get('url_video_en_vivo', ''))
        if st.button("💾 Guardar URL", type="primary"):
            st.session_state.url_video_en_vivo = nueva_url.strip()
            guardar_estado_global()
            st.success("¡URL guardada!")

    with tab6:
        st.markdown("### 📊 Saldos y Cuentas de Usuarios")
        usuarios_futuros = [u for u in st.session_state.lista_usuarios if u != "CASA"]
        if usuarios_futuros:
            datos_cuentas = []
            for j in usuarios_futuros:
                vals = st.session_state.cuentas.get(j, {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0})
                datos_cuentas.append({"Usuario": j, "Compras": formatear_bs(vals['Pujas']), "Premios": formatear_bs(vals['Premios']), "Pagos": formatear_bs(vals['Abonos']), "Neto": formatear_bs(vals['Pujas'] - vals['Abonos'] - vals['Premios'])})
            st.dataframe(pd.DataFrame(datos_cuentas), use_container_width=True, hide_index=True)
        st.metric("Ganancia Casa", formatear_bs(st.session_state.ganancia_casa))

    with tab7:
        st.markdown("### 🖼️ Imágenes por Carrera")
        carr_img_sel = st.selectbox("Seleccionar Carrera para Imagen", list(st.session_state.remates.keys()))
        imagen_subida = st.file_uploader("Subir imagen", type=["png", "jpg", "jpeg"])
        if imagen_subida and st.button("💾 Guardar Imagen", type="primary"):
            img_pil = Image.open(imagen_subida).convert("RGB")
            buffer = io.BytesIO()
            img_pil.save(buffer, format="JPEG", quality=75)
            st.session_state.imagenes_carreras[carr_img_sel] = f"data:image/jpeg;base64,{base64.b64encode(buffer.getvalue()).decode('utf-8')}"
            guardar_estado_global()
            st.success("¡Imagen guardada!")

# Transmisión en vivo global
if st.session_state.get('url_video_en_vivo', '').strip():
    st.markdown("<br><hr style='border-color: #30363d;'>", unsafe_allow_html=True)
    st.markdown("### 📺 TRANSMISIÓN EN VIVO")
    yt_match = re.search(r'(?:v=|\/embed\/|youtu\.be\/|\/v\/|\/e\/|watch\?v=|&v=)([^#&?]{11})', st.session_state.url_video_en_vivo)
    if yt_match:
        st.video(f"https://www.youtube.com/embed/{yt_match.group(1)}?playsinline=1")
    else:
        st.video(st.session_state.url_video_en_vivo)
