import streamlit as st
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
    "1001397336.jpg",
    "1001397336.png",
    "1001394095_preview_rev_1_2.png",
    "1001394095_preview_rev_1_2.jpg",
    "logo.png",
    "logo.jpg"
]

img_b64 = get_image_base64(nombres_archivos)

if img_b64:
    logo_display = f'<img src="data:image/jpeg;base64,{img_b64}" class="header-logo-img" />'
else:
    logo_display = '<span style="color: #f1c40f; font-size: 16px; font-weight: 900; font-style: italic;">CALIFORNIA CHROME</span>'

ahora_dt = obtener_hora_venezuela_local()
hora_texto = ahora_dt.strftime('%I:%M:%S %p')
fecha_texto = ahora_dt.strftime('%d/%m/%Y')

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stApp {
        background-color: #080a0f;
        color: #f0f6fc;
    }
    header[data-testid="stHeader"] {
        display: none !important;
    }
    div[data-testid="stTabs"] {
        display: none !important;
    }
    .block-container {
        padding-top: 0.4rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
        max-width: 1400px !important;
        margin: 0 auto !important;
    }
    .header-container {
        background: linear-gradient(180deg, #000000 0%, #11141d 100%) !important;
        width: 100% !important;
        padding: 10px 20px !important;
        display: flex !important;
        flex-direction: row !important;
        justify-content: space-between !important;
        align-items: center !important;
        border-bottom: 2px solid #30363d !important;
        border-radius: 8px !important;
        box-sizing: border-box !important;
        gap: 15px;
        margin-bottom: 12px !important;
    }
    .header-left-clock {
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        background: #0d1117 !important;
        border: 1px solid #30363d !important;
        padding: 6px 12px !important;
        border-radius: 8px !important;
        text-align: left !important;
        flex-shrink: 0;
    }
    .clock-time {
        color: #58a6ff !important;
        font-size: 14px !important;
        font-weight: 800 !important;
        line-height: 1.15;
    }
    .clock-date {
        color: #8b949e !important;
        font-size: 10px !important;
        font-weight: 600 !important;
    }
    .header-center-logo {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        flex: 1 !important;
        min-width: 0 !important;
        overflow: hidden !important;
        padding: 0 4px !important;
    }
    .header-logo-img {
        max-height: 80px !important;
        max-width: 100% !important;
        width: auto !important;
        object-fit: contain !important;
        display: block !important;
        filter: drop-shadow(0px 3px 6px rgba(0,0,0,0.9));
    }
    .user-info-container {
        display: flex !important;
        align-items: center !important;
        gap: 10px !important;
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        padding: 5px 12px !important;
        border-radius: 20px !important;
        flex-shrink: 0;
    }
    .user-text-info {
        display: flex !important;
        flex-direction: column !important;
        text-align: right !important;
        line-height: 1.15 !important;
    }
    .user-name {
        color: #ffffff !important;
        font-size: 11px !important;
        font-weight: 800 !important;
    }
    .user-balance {
        color: #58a6ff !important;
        font-size: 11px !important;
        font-weight: 800 !important;
    }
    .user-avatar {
        background-color: #f1c40f !important;
        color: #000000 !important;
        border-radius: 50% !important;
        width: 36px !important;
        height: 36px !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        font-size: 16px !important;
        font-weight: bold !important;
        box-shadow: 0px 2px 4px rgba(0,0,0,0.5);
        flex-shrink: 0;
    }
    div.row-widget.stHorizontal > div {
        gap: 6px !important;
    }
    .stButton button {
        width: 100% !important;
        border-radius: 6px !important;
        font-weight: 700 !important;
        padding: 0.2rem 0.4rem !important;
        min-height: 32px !important;
        font-size: 12px !important;
        letter-spacing: 0.2px;
        white-space: nowrap !important;
    }
    div[data-testid="column"] {
        width: auto !important;
        flex: 1 !important;
        min-width: 0 !important;
        padding: 0 3px !important;
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
    }
    .incentivo-elegante {
        background: linear-gradient(135deg, #0d1117 100%, #161b22 0%);
        border: 1px solid #f1c40f;
        padding: 10px 14px;
        border-radius: 6px;
        text-align: center;
        margin: 8px 0;
        box-shadow: 0px 2px 8px rgba(241, 196, 15, 0.15);
    }
    .incentivo-elegante-titulo {
        color: #f1c40f;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 3px;
    }
    .incentivo-elegante-monto {
        color: #ffffff;
        font-size: 18px;
        font-weight: 800;
        letter-spacing: 0.3px;
    }
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN GLOBAL DE ESTADOS ---
def inicializar_estado_global():
    if 'menu_principal_opcion' not in st.session_state:
        st.session_state.menu_principal_opcion = "Remates"
    if 'sub_remate_opcion' not in st.session_state:
        st.session_state.sub_remate_opcion = "En Vivo"
    if 'sub_dupleta_opcion' not in st.session_state:
        st.session_state.sub_dupleta_opcion = "Dupleta"
    if 'usuario_activo' not in st.session_state:
        st.session_state.usuario_activo = "CASA"
    if 'lista_usuarios' not in st.session_state:
        st.session_state.lista_usuarios = ["CASA"]
    if 'banco_caballos_por_carrera' not in st.session_state:
        st.session_state.banco_caballos_por_carrera = {}
    if 'remates' not in st.session_state:
        st.session_state.remates = {}
    if 'detalles_carreras' not in st.session_state:
        st.session_state.detalles_carreras = {}
    if 'historial_ganadores' not in st.session_state:
        st.session_state.historial_ganadores = {}
    if 'carreras_cerradas_remate' not in st.session_state:
        st.session_state.carreras_cerradas_remate = {}
    if 'remates_cargados_en_cuentas' not in st.session_state:
        st.session_state.remates_cargados_en_cuentas = {}
    if 'fechas_horas_cierre_remate' not in st.session_state:
        st.session_state.fechas_horas_cierre_remate = {}
    if 'estado_conteo_carrera' not in st.session_state:
        st.session_state.estado_conteo_carrera = {}
    if 'tiempo_inicio_conteo' not in st.session_state:
        st.session_state.tiempo_inicio_conteo = {}
    if 'cuentas' not in st.session_state:
        st.session_state.cuentas = {"CASA": {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}}
    if 'historial_jugadas' not in st.session_state:
        st.session_state.historial_jugadas = []
    if 'ganancia_casa' not in st.session_state:
        st.session_state.ganancia_casa = 0.0
    if 'dupletas_tickets' not in st.session_state:
        st.session_state.dupletas_tickets = []
    if 'tripleta_tickets' not in st.session_state:
        st.session_state.tripleta_tickets = []
    if 'polla_tickets' not in st.session_state:
        st.session_state.polla_tickets = []
    if 'carreras_habilitadas_dupleta' not in st.session_state:
        st.session_state.carreras_habilitadas_dupleta = []
    if 'carreras_habilitadas_tripleta' not in st.session_state:
        st.session_state.carreras_habilitadas_tripleta = []
    if 'carreras_habilitadas_polla' not in st.session_state:
        st.session_state.carreras_habilitadas_polla = []
    if 'config_montos_especiales' not in st.session_state:
        st.session_state.config_montos_especiales = {
            "Dupleta": 500.0,
            "Tripleta": 500.0,
            "Polla Hipica": 1000.0
        }
    if 'dupleta_bloqueada' not in st.session_state:
        st.session_state.dupleta_bloqueada = False
    if 'carreras_activas_remate' not in st.session_state:
        st.session_state.carreras_activas_remate = []
    if 'carreras_por_modalidad' not in st.session_state:
        st.session_state.carreras_por_modalidad = {"Adelantados": [], "Ciegos": [], "En Vivo": []}
    if 'total_carreras_semana' not in st.session_state:
        st.session_state.total_carreras_semana = 10
    if 'programa_pdf_bytes' not in st.session_state:
        st.session_state.programa_pdf_bytes = None
    if 'programa_pdf_nombre' not in st.session_state:
        st.session_state.programa_pdf_nombre = None
    if 'texto_completo_pdf' not in st.session_state:
        st.session_state.texto_completo_pdf = ""
    if 'imagenes_carreras' not in st.session_state:
        st.session_state.imagenes_carreras = {}
    if 'admin_tab_seleccionada' not in st.session_state:
        st.session_state.admin_tab_seleccionada = "✍️ Banco de Caballos"
    if 'url_video_en_vivo' not in st.session_state:
        st.session_state.url_video_en_vivo = ""

inicializar_estado_global()

def formatear_bs(monto):
    numero_formateado = f"{monto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"Bs. {numero_formateado}"

# --- CÁLCULO DE DATOS PARA EL USUARIO EN SESIÓN ---
usuario_en_sesion = st.session_state.usuario_activo
if usuario_en_sesion not in st.session_state.cuentas:
    st.session_state.cuentas[usuario_en_sesion] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}

vals_sesion = st.session_state.cuentas[usuario_en_sesion]
neto_usuario = vals_sesion['Pujas'] - vals_sesion['Abonos'] - vals_sesion['Premios']
if neto_usuario > 0:
    etiqueta_balance = f"Deuda: {formatear_bs(neto_usuario)}"
elif neto_usuario < 0:
    etiqueta_balance = f"Premio: {formatear_bs(abs(neto_usuario))}"
else:
    etiqueta_balance = "Al día: Bs. 0,00"

# --- CABECERA SUPERIOR OPTIMIZADA ---
st.markdown(f"""
    <div class="header-container">
        <div class="header-left-clock">
            <span class="clock-time">🕒 {hora_texto}</span>
            <span class="clock-date">📅 {fecha_texto}</span>
        </div>
        <div class="header-center-logo">
            {logo_display}
        </div>
        <div class="user-info-container">
            <div class="user-text-info">
                <span class="user-name">{usuario_en_sesion}</span>
                <span class="user-balance">{etiqueta_balance}</span>
            </div>
            <div class="user-avatar">👤</div>
        </div>
    </div>
""", unsafe_allow_html=True)

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

def generar_tabla_html_remate(remates_dict):
    html = """
    <style>
        .tabla-referencia {
            width: 100%;
            border-collapse: collapse;
            font-family: sans-serif;
            background-color: #ffffff;
            color: #000000;
            margin-bottom: 10px;
        }
        .tabla-referencia th {
            border-top: 2px solid #dfc729;
            border-bottom: 2px solid #dfc729;
            padding: 5px 4px;
            text-align: left;
            font-weight: 800;
            background-color: #ffffff;
            color: #000000;
            font-size: 11px;
        }
        .tabla-referencia td {
            border-bottom: 1px solid #dfc729;
            padding: 5px 4px;
            background-color: #fbfbfb;
            color: #111111;
            font-size: 11px;
            vertical-align: middle;
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
    </style>
    <div style="background-color: #ffffff; padding: 3px; border-radius: 6px; overflow-x: auto;">
        <table class="tabla-referencia">
            <thead>
                <tr>
                    <th style="width: 8%;">No</th>
                    <th style="width: 37%;">Ejemplar</th>
                    <th style="width: 27%;">Comprador</th>
                    <th style="width: 28%;">Monto Actual</th>
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
        
        html += f"""
                <tr>
                    <td><span class="badge-numero {badge_class}">{num}</span></td>
                    <td style="font-weight: 800; font-size: 12px;">{nombre_solo.upper()}</td>
                    <td>{info['jugador']}</td>
                    <td style="font-weight: bold; color: #000000;">{formatear_bs(info['monto'])}</td>
                </tr>
        """
    html += """
            </tbody>
        </table>
    </div>
    """
    return html

def procesar_texto_flexible(texto_a_procesar):
    try:
        lineas = texto_a_procesar.split('\n')
        carrera_actual_detectada = None
        banco_temporal = {}
        detalles_temporal = {}
        
        map_numeros = {
            'primera': 1, 'segunda': 2, 'tercera': 3, 'cuarta': 4,
            'quinta': 5, 'sexta': 6, 'septima': 7, 'octava': 8,
            'novena': 9, 'decima': 10, 'undecima': 11, 'duodecima': 12
        }

        for linea in lineas:
            linea_limpia = linea.strip()
            if not linea_limpia:
                continue
            
            linea_lower = linea_limpia.lower()
            
            es_nueva_carrera = False
            num_carr = None

            if "carrera" in linea_lower or any(k in linea_lower for k in map_numeros.keys()):
                match_digito = re.search(r'(\d+)', linea_lower)
                if match_digito and ("carrera" in linea_lower or len(linea_limpia) < 50):
                    num_carr = int(match_digito.group(1))
                    es_nueva_carrera = True
                else:
                    for palabra, num in map_numeros.items():
                        if palabra in linea_lower:
                            num_carr = num
                            es_nueva_carrera = True
                            break

            if es_nueva_carrera and num_carr:
                carrera_actual_detectada = f"Carrera {num_carr}"
                if carrera_actual_detectada not in banco_temporal:
                    banco_temporal[carrera_actual_detectada] = []
                
                cond = linea_limpia
                dist = "1200 mts"
                hora = "02:00 PM"

                match_dist = re.search(r'(\d+[\.,]?\d*\s*(?:mts|metros|mt))', linea_lower)
                if match_dist:
                    dist = match_dist.group(1).upper()

                match_h = re.search(r'(\d{1,2}:\d{2}\s*(?:am|pm)?)', linea_lower)
                if match_h:
                    hora = match_h.group(1).upper()

                detalles_temporal[carrera_actual_detectada] = {
                    "condicion": cond, 
                    "distancia": dist, 
                    "hora": hora,
                    "monto_fijo_ciego": 500.0,
                    "incentivo": 0.0
                }
                continue

            if carrera_actual_detectada:
                if "mts" in linea_lower or "metros" in linea_lower:
                    if detalles_temporal[carrera_actual_detectada]["distancia"] == "1200 mts":
                        detalles_temporal[carrera_actual_detectada]["distancia"] = linea_limpia
                if re.search(r'\d{1,2}:\d{2}', linea_lower):
                    match_h2 = re.search(r'\d{1,2}:\d{2}\s*(?:am|pm)?', linea_lower)
                    if match_h2 and detalles_temporal[carrera_actual_detectada]["hora"] == "02:00 PM":
                        detalles_temporal[carrera_actual_detectada]["hora"] = match_h2.group(0).upper()

                match_ejemplar = re.match(r'^(?:[Pp][Oo][Ss]\.?\s*)?(\d{1,2})[\s\-\.\)]+(.+)', linea_limpia)
                if match_ejemplar:
                    num_pos = int(match_ejemplar.group(1))
                    nom_ej = match_ejemplar.group(2).strip()
                    palabras_excluir = ['retirado', 'jinete', 'entrenador', 'distancia', 'premio', 'propietario', 'condicion', 'hipodromo', 'metros', 'haras', 'stud', 'aprox', 'ejemplar']
                    if 1 <= num_pos <= 25 and len(nom_ej) > 1 and not any(p in nom_ej.lower() for p in palabras_excluir):
                        formato_ej = f"{num_pos} - {nom_ej.title()}"
                        if formato_ej not in banco_temporal[carrera_actual_detectada]:
                            banco_temporal[carrera_actual_detectada].append(formato_ej)

        if banco_temporal:
            for c_key in banco_temporal:
                banco_temporal[c_key].sort(key=lambda x: int(re.match(r'^(\d+)', x).group(1)))
            st.session_state.banco_caballos_por_carrera = banco_temporal
            st.session_state.detalles_carreras = detalles_temporal
            for c_key, c_vals in banco_temporal.items():
                if c_key not in st.session_state.remates:
                    st.session_state.remates[c_key] = {}
                for ev in c_vals:
                    if ev not in st.session_state.remates[c_key]:
                        st.session_state.remates[c_key][ev] = {"jugador": "Sin Postor", "monto": 0.0}
            todas_carr = list(banco_temporal.keys())
            st.session_state.carreras_activas_remate = list(todas_carr)
            st.session_state.carreras_habilitadas_dupleta = list(todas_carr)
            st.session_state.carreras_habilitadas_tripleta = list(todas_carr)
            st.session_state.carreras_habilitadas_polla = list(todas_carr)
            st.session_state.total_carreras_semana = len(todas_carr)
            for mod in st.session_state.carreras_por_modalidad:
                if not st.session_state.carreras_por_modalidad[mod]:
                    if mod == "Ciegos":
                        st.session_state.carreras_por_modalidad[mod] = todas_carr[:2]
                    else:
                        st.session_state.carreras_por_modalidad[mod] = list(todas_carr)
            return True
    except Exception as e:
        st.error(f"Error procesando el texto: {e}")
    return False

if not st.session_state.remates:
    for i in range(1, st.session_state.total_carreras_semana + 1):
        carr_nombre = f"Carrera {i}"
        st.session_state.banco_caballos_por_carrera[carr_nombre] = [f"{j} - Ejemplar {j}" for j in range(1, 11)]
        st.session_state.remates[carr_nombre] = {f"{j} - Ejemplar {j}": {"jugador": "Sin Postor", "monto": 0.0} for j in range(1, 11)}
        st.session_state.detalles_carreras[carr_nombre] = {"condicion": "Condición estándar", "distancia": "1200 mts", "hora": "02:00 PM", "monto_fijo_ciego": 500.0, "incentivo": 0.0}

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
col_menu1, col_menu2, col_menu3 = st.columns(3, gap="small")

with col_menu1:
    if st.button("REMATES", key="menu_btn_remates_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Remates" else "secondary"):
        st.session_state.menu_principal_opcion = "Remates"
        st.rerun()

with col_menu2:
    if st.button("DUPLETAS/POLLAS HÍPICAS", key="menu_btn_dupletas_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Dupletas" else "secondary"):
        st.session_state.menu_principal_opcion = "Dupletas"
        st.rerun()

with col_menu3:
    if st.button("CUENTAS", key="menu_btn_cuentas_top", use_container_width=True, type="primary" if st.session_state.menu_principal_opcion == "Cuentas" else "secondary"):
        st.session_state.menu_principal_opcion = "Cuentas"
        st.rerun()

st.markdown("<hr style='margin: 0.3rem 0; border-color: #21262d;'>", unsafe_allow_html=True)

# --- CARRUSEL AUTOMÁTICO DE IMÁGENES DEL HIPÓDROMO LA RINCONADA (8 SEGUNDOS) ---
ruta_actual_dir = os.path.dirname(os.path.abspath(__file__))

nombres_banners_posibles = [
    "1001398079.jpg", "1001398079.png",
    "1001398078.jpg", "1001398078.png",
    "1001398058.jpg", "1001398058.png",
    "rinconada.jpg", "rinconada.png"
]

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
        .banner-slider-container {{
            width: 100%;
            max-width: 1200px;
            height: 240px;
            margin: 0 auto 12px auto;
            border-radius: 8px;
            overflow: hidden;
            border: 2px solid #f1c40f;
            box-shadow: 0px 4px 14px rgba(0,0,0,0.8);
            position: relative;
            background-color: #0d1117;
        }}
        .banner-slide-img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: opacity 1.2s ease-in-out;
            display: block;
        }}
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
                    imgElement.style.opacity = 0.15;
                    setTimeout(function() {{
                        imgElement.src = images[index];
                        imgElement.style.opacity = 1;
                    }}, 400);
                }}, 8000);
            }}
        }})();
    </script>
    """
    components.html(html_slider, height=255)
else:
    st.markdown("""
        <div style="background: linear-gradient(90deg, #11141d 0%, #1f2937 100%); border: 2px solid #f1c40f; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 10px;">
            <h3 style="color: #f1c40f; margin: 0; font-weight: 900; letter-spacing: 1px;">INH - HIPÓDROMO DE LA RINCONADA</h3>
            <p style="color: #8b949e; font-size: 12px; margin: 4px 0 0 0;">¡La pasión del hipismo venezolano en vivo!</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- BARRA LATERAL (IZQUIERDA) ---
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
        st.rerun()

with st.sidebar.expander("🏠 Retención de la Casa", expanded=False):
    porcentaje_casa = st.slider("Retención (%)", 0, 50, 30, key="sb_slider_retencion_casa")

with st.sidebar.expander("🔒 Estado Dupletas / Polla", expanded=False):
    if st.session_state.dupleta_bloqueada:
        st.markdown("<p style='color: #ff4757; font-weight: bold;'>🔴 BLOQUEADAS</p>", unsafe_allow_html=True)
        if st.button("🔓 Desbloquear", key="sb_btn_desbloquear_dupleta"):
            st.session_state.dupleta_bloqueada = False
            st.rerun()
    else:
        st.markdown("<p style='color: #00d2d3; font-weight: bold;'>🟢 ABIERTAS</p>", unsafe_allow_html=True)
        if st.button("🔒 Bloquear", key="sb_btn_bloquear_dupleta"):
            st.session_state.dupleta_bloqueada = True
            st.rerun()

# --- SECCIÓN EN BARRA LATERAL PARA CIERRE ESTRICTO Y LIQUIDACIÓN ---
with st.sidebar.expander("🏁 Cierre y Liquidación de Remates", expanded=False):
    carr_seleccionada_liq = st.selectbox("Gestionar Carrera", lista_carreras_disponibles, key="sb_liq_sel_carrera")
    c_cerrada_actual = st.session_state.carreras_cerradas_remate.get(carr_seleccionada_liq, False)
    
    col_cz1, col_cz2 = st.columns(2)
    with col_cz1:
        fecha_cierre_adm = st.date_input("Fecha límite", value=ahora_dt.date(), key=f"sb_f_cierre_{carr_seleccionada_liq}")
    with col_cz2:
        hora_cierre_adm = st.time_input("Hora límite", value=datetime.now().time(), key=f"sb_h_cierre_{carr_seleccionada_liq}")
    
    if st.button("💾 Guardar Hora de Cierre Estricto", key=f"sb_btn_guardar_h_{carr_seleccionada_liq}", use_container_width=True):
        dt_cierre_estricto = datetime.combine(fecha_cierre_adm, hora_cierre_adm)
        st.session_state.fechas_horas_cierre_remate[carr_seleccionada_liq] = dt_cierre_estricto
        st.session_state.estado_conteo_carrera[carr_seleccionada_liq] = "INACTIVO"
        st.toast(f"✅ Cierre estricto guardado para {carr_seleccionada_liq}")
        st.rerun()

    st.markdown("---")
    if not c_cerrada_actual:
        if st.button("🔒 Cerrar Remate Manualmente", key=f"sb_liq_cerrar_{carr_seleccionada_liq}", use_container_width=True, type="primary"):
            st.session_state.carreras_cerradas_remate[carr_seleccionada_liq] = True
            st.session_state.estado_conteo_carrera[carr_seleccionada_liq] = "CERRADO"
            
            if not st.session_state.remates_cargados_en_cuentas.get(carr_seleccionada_liq, False):
                for cab, info in st.session_state.remates[carr_seleccionada_liq].items():
                    if info['jugador'] != "Sin Postor" and info['monto'] > 0:
                        if info['jugador'] not in st.session_state.cuentas:
                            st.session_state.cuentas[info['jugador']] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                        st.session_state.cuentas[info['jugador']]['Pujas'] += info['monto']
                st.session_state.remates_cargados_en_cuentas[carr_seleccionada_liq] = True
            st.rerun()
    else:
        if st.button("🔓 Reabrir Remate", key=f"sb_liq_reabrir_{carr_seleccionada_liq}", use_container_width=True):
            st.session_state.carreras_cerradas_remate[carr_seleccionada_liq] = False
            st.session_state.remates_cargados_en_cuentas[carr_seleccionada_liq] = False
            st.rerun()

with st.sidebar.expander("🔒 Zona Administrador", expanded=False):
    es_admin_activo = (st.session_state.menu_principal_opcion == "🔒 Zona Admin")
    if st.button("⚙️ Entrar a Zona Admin", key="sb_btn_ir_admin", use_container_width=True, type="primary" if es_admin_activo else "secondary"):
        st.session_state.menu_principal_opcion = "🔒 Zona Admin"
        st.rerun()

if st.sidebar.button("🗑️ Reiniciar Jornada", key="sb_btn_reiniciar_jornada", use_container_width=True):
    for key in list(st.session_state.keys()):
        if key not in ['banco_caballos_por_carrera', 'lista_usuarios']:
            del st.session_state[key]
    st.toast("🚨 Jornada reiniciada.")
    st.rerun()

menu_principal_opcion = st.session_state.menu_principal_opcion

# =========================================================================
# 1. MÓDULO DE REMATES (3 OPCIONES: ADELANTADOS, CIEGOS, EN VIVO)
# =========================================================================
if menu_principal_opcion == "Remates":
    col_so1, col_so2, col_so3 = st.columns(3, gap="small")
    with col_so1:
        if st.button("⏱️ Adelantados", key="sub_rem_adelantados", use_container_width=True, type="primary" if st.session_state.sub_remate_opcion == "Adelantados" else "secondary"):
            st.session_state.sub_remate_opcion = "Adelantados"
            st.rerun()
    with col_so2:
        if st.button("🙈 Ciegos", key="sub_rem_ciegos", use_container_width=True, type="primary" if st.session_state.sub_remate_opcion == "Ciegos" else "secondary"):
            st.session_state.sub_remate_opcion = "Ciegos"
            st.rerun()
    with col_so3:
        if st.button("⚡ En Vivo", key="sub_rem_envivo", use_container_width=True, type="primary" if st.session_state.sub_remate_opcion == "En Vivo" else "secondary"):
            st.session_state.sub_remate_opcion = "En Vivo"
            st.rerun()

    st.markdown("<hr style='margin: 0.3rem 0; border-color: #21262d;'>", unsafe_allow_html=True)

    modo_actual_remate = st.session_state.sub_remate_opcion

    st.markdown(f"### 🏇 Modo de Remate: **{modo_actual_remate.upper()}**")

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
            st.info(f"ℹ️ No hay carreras habilitadas para la modalidad **{modo_actual_remate}**. Habilítalas en Zona Admin -> Banco de Caballos.")
        else:
            if "carrera_remate_activa_seleccionada" not in st.session_state or st.session_state["carrera_remate_activa_seleccionada"] not in carreras_filtradas_visibles:
                carr_activa = carreras_filtradas_visibles[0]
                st.session_state["carrera_remate_activa_seleccionada"] = carr_activa
            else:
                carr_activa = st.session_state["carrera_remate_activa_seleccionada"]

            st.markdown("🔹 **Seleccionar Carrera:**")
            
            num_carreras = len(carreras_filtradas_visibles)
            cols_carreras = st.columns(num_carreras if num_carreras > 0 else 1, gap="small")
            for idx, c_nombre in enumerate(carreras_filtradas_visibles):
                es_modo_ciego = (modo_actual_remate == "Ciegos")
                abreviatura = obtener_abreviatura_carrera(c_nombre, modo_ciego=es_modo_ciego)
                es_activa = (c_nombre == carr_activa)
                with cols_carreras[idx]:
                    if st.button(abreviatura, key=f"rem_btn_sel_carr_{idx}", use_container_width=True, type="primary" if es_activa else "secondary"):
                        st.session_state["carrera_remate_activa_seleccionada"] = c_nombre
                        st.rerun()

            st.markdown(f"---")

            if carr_activa in st.session_state.imagenes_carreras:
                st.image(st.session_state.imagenes_carreras[carr_activa], caption=f"Imagen oficial - {carr_activa}", use_container_width=True)

            carrera_cerrada = st.session_state.carreras_cerradas_remate.get(carr_activa, False)
            if carrera_cerrada:
                st.error(f"🔴 La carrera **{carr_activa}** se encuentra **CERRADA** para nuevas pujas.")
            else:
                st.success(f"🟢 Panel activo y abierto para: **{carr_activa}** ({modo_actual_remate})")

            # --- MOSTRAR CONDICIÓN, HORA Y DISTANCIA ---
            if carr_activa not in st.session_state.detalles_carreras:
                st.session_state.detalles_carreras[carr_activa] = {"condicion": "Condición general", "distancia": "1200 mts", "hora": "02:00 PM", "monto_fijo_ciego": 500.0, "incentivo": 0.0}
            
            detalles_carr = st.session_state.detalles_carreras[carr_activa]

            st.markdown(f"""
                <div class="carrera-condicion-card">
                    <b>🏁 {carr_activa}</b><br>
                    🏷️ <b>Condición:</b> {detalles_carr.get('condicion', 'N/A')}<br>
                    📏 <b>Distancia:</b> {detalles_carr.get('distancia', 'N/A')} &nbsp;|&nbsp; ⏰ <b>Hora:</b> {detalles_carr.get('hora', 'N/A')}
                </div>
            """, unsafe_allow_html=True)

            dt_limite = st.session_state.fechas_horas_cierre_remate.get(carr_activa)
            estado_conteo = st.session_state.estado_conteo_carrera.get(carr_activa, "INACTIVO")
            
            if dt_limite:
                st.markdown(f"<div class='cierre-info-box'>⏰ Cierre Estricto: <b>{dt_limite.strftime('%d/%m/%Y - %I:%M %p')}</b></div>", unsafe_allow_html=True)

            if dt_limite and not carrera_cerrada:
                diferencia_segundos = (dt_limite - ahora_dt).total_seconds()
                if estado_conteo == "INACTIVO":
                    if 0 < diferencia_segundos <= 10:
                        st.session_state.estado_conteo_carrera[carr_activa] = "CONTEO_10S"
                        st.session_state.tiempo_inicio_conteo[carr_activa] = ahora_dt
                        st.rerun()
                    elif diferencia_segundos <= 0:
                        st.session_state.carreras_cerradas_remate[carr_activa] = True
                        st.session_state.estado_conteo_carrera[carr_activa] = "CERRADO"
                        st.rerun()
                elif estado_conteo == "CONTEO_10S":
                    tiempo_inicio = st.session_state.tiempo_inicio_conteo.get(carr_activa, ahora_dt)
                    transcurridos = (ahora_dt - tiempo_inicio).total_seconds()
                    if transcurridos >= 12:
                        st.session_state.carreras_cerradas_remate[carr_activa] = True
                        st.session_state.estado_conteo_carrera[carr_activa] = "CERRADO"
                        st.rerun()
                    else:
                        restantes_10s = max(0, 10 - int(transcurridos))
                        if restantes_10s > 0:
                            st.markdown(f"<div class='timer-box'>⚠️ CIERRE EN: <b>{restantes_10s}s</b> ({carr_activa})</div>", unsafe_allow_html=True)

            tabla_html = generar_tabla_html_remate(st.session_state.remates[carr_activa])
            cantidad_filas = len(st.session_state.remates[carr_activa])
            altura_dinamica = min(max(140, (cantidad_filas * 32) + 50), 420)
            components.html(tabla_html, height=altura_dinamica, scrolling=True)
            
            # --- SELECCIONAR EJEMPLAR GANADOR DEBAJO DE LA TABLA (COMPACTO Y ELEGANTE) ---
            with st.container(border=True):
                st.markdown(f"<p style='font-size: 11px; font-weight: 700; margin-bottom: 2px; color: #f1e05a;'>🎯 Ganador - {carr_activa}</p>", unsafe_allow_html=True)
                if carr_activa in st.session_state.historial_ganadores:
                    info_ganador_prev = st.session_state.historial_ganadores[carr_activa]
                    st.success(f"✅ Ganador: **{info_ganador_prev.get('Ganador', 'N/A')}** | Premio: **{info_ganador_prev.get('Premio', '0')}**")
                else:
                    caballos_lista_ganador = list(st.session_state.remates[carr_activa].keys())
                    col_g1, col_g2 = st.columns([3, 2], gap="small")
                    with col_g1:
                        caballo_ganador_elegido = st.selectbox("Ejemplar Ganador", caballos_lista_ganador, key=f"rem_sel_ganador_{carr_activa}", label_visibility="collapsed")
                    with col_g2:
                        if st.button("🏆 Liquidar", key=f"rem_btn_liquidar_{carr_activa}", use_container_width=True, type="primary"):
                            pote_carr_total = sum([info['monto'] for info in st.session_state.remates[carr_activa].values()])
                            monto_casa_calc = pote_carr_total * (porcentaje_casa / 100)
                            incentivo_establecido = float(detalles_carr.get('incentivo', 0.0))
                            premio_final_liq = pote_carr_total - monto_casa_calc + incentivo_establecido
                            
                            info_g = st.session_state.remates[carr_activa][caballo_ganador_elegido]
                            if info_g['jugador'] != "Sin Postor":
                                if info_g['jugador'] not in st.session_state.cuentas:
                                    st.session_state.cuentas[info_g['jugador']] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                                st.session_state.cuentas[info_g['jugador']]['Premios'] += premio_final_liq
                            st.session_state.ganancia_casa += monto_casa_calc
                            st.session_state.historial_ganadores[carr_activa] = {"Ganador": info_g['jugador'], "Premio": formatear_bs(premio_final_liq)}
                            st.success(f"✅ ¡Premio liquidado a **{info_g['jugador']}**!")
                            st.rerun()

            # --- HISTORIAL DE PUJAS DEBAJO DE LA TABLA ---
            with st.expander(f"📜 Historial de Pujas - {carr_activa} ({modo_actual_remate})", expanded=False):
                historial_carrera_actual = [
                    h for h in st.session_state.historial_jugadas 
                    if h.get('carrera') == carr_activa and "Remate" in h.get('type', h.get('tipo', ''))
                ]
                if not historial_carrera_actual:
                    st.info(f"ℹ️ No hay registros de pujas o compras para {carr_activa} en esta modalidad.")
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

            total_pote = sum([info['monto'] for info in st.session_state.remates[carr_activa].values()])
            monto_casa = total_pote * (porcentaje_casa / 100)
            pote_neto_base = total_pote - monto_casa
            incentivo_actual = float(detalles_carr.get('incentivo', 0.0))
            premio_total_calculado = pote_neto_base + incentivo_actual

            c_m1, c_m2 = st.columns(2)
            c_m1.metric(f"💰 Pote ({carr_activa})", formatear_bs(total_pote))
            c_m2.metric(f"🏆 Premio Total ({carr_activa})", formatear_bs(premio_total_calculado))

            if incentivo_actual > 0:
                st.markdown(f"""
                    <div class="incentivo-elegante">
                        <div class="incentivo-elegante-titulo">🎁 Incentivo Ya Establecido</div>
                        <div class="incentivo-elegante-monto">{formatear_bs(incentivo_actual)}</div>
                    </div>
                """, unsafe_allow_html=True)

            with st.container(border=True):
                if modo_actual_remate == "Ciegos":
                    st.markdown(f"🙈 **Remate Ciego - Asignación de Ejemplar ({carr_activa})**")
                    monto_fijo_carrera = detalles_carr.get('monto_fijo_ciego', 500.0)

                    caballos_disponibles_ciego = [
                        cab for cab, info in st.session_state.remates[carr_activa].items() 
                        if info['jugador'] == "Sin Postor" or info['monto'] <= 0
                    ]

                    if not caballos_disponibles_ciego:
                        st.warning("⚠️ Todos los ejemplares de esta carrera ya han sido adquiridos.")
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
                                        
                                        st.success(f"🎉 #{num_cb_parte} asignado a **{st.session_state.usuario_activo}** ({formatear_bs(monto_fijo_carrera)})!")
                                        st.rerun()
                else:
                    st.markdown(f"⚡ **Registro Rápido de Puja - {carr_activa}**")
                    lista_caballos_activos = list(st.session_state.remates[carr_activa].keys())
                    
                    if not lista_caballos_activos:
                        st.warning("Sin ejemplares inscritos en esta carrera.")
                    else:
                        k_sel_cab = f"rem_caballo_activo_click_{carr_activa}"
                        if k_sel_cab not in st.session_state or st.session_state[k_sel_cab] not in lista_caballos_activos:
                            st.session_state[k_sel_cab] = lista_caballos_activos[0]
                            
                        st.markdown(f"🔹 **1. Seleccionar Ejemplar (Total inscritos: {len(lista_caballos_activos)}):**")
                        cantidad_ejemplares = len(lista_caballos_activos)
                        cols_ejemplares = min(6, cantidad_ejemplares) if cantidad_ejemplares > 0 else 1
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
                                    st.success("✅ ¡Puja registrada correctamente y conteo reiniciado!")
                                    st.rerun()

# =========================================================================
# 2. MÓDULO DE DUPLETAS, TRIPLETAS Y POLLA HÍPICA
# =========================================================================
elif menu_principal_opcion == "Dupletas":
    col_d1, col_d2, col_d3 = st.columns(3, gap="small")
    with col_d1:
        if st.button("🎟️ Dupleta", key="sub_dup_dupleta", use_container_width=True, type="primary" if st.session_state.sub_dupleta_opcion == "Dupleta" else "secondary"):
            st.session_state.sub_dupleta_opcion = "Dupleta"
            st.rerun()
    with col_d2:
        if st.button("🎟️ Tripleta", key="sub_dup_tripleta", use_container_width=True, type="primary" if st.session_state.sub_dupleta_opcion == "Tripleta" else "secondary"):
            st.session_state.sub_dupleta_opcion = "Tripleta"
            st.rerun()
    with col_d3:
        if st.button("🏇 Polla Hípica", key="sub_dup_polla", use_container_width=True, type="primary" if st.session_state.sub_dupleta_opcion == "Polla Hipica" else "secondary"):
            st.session_state.sub_dupleta_opcion = "Polla Hipica"
            st.rerun()

    st.markdown("<hr style='margin: 0.3rem 0; border-color: #21262d;'>", unsafe_allow_html=True)
    sub_dup_actual = st.session_state.sub_dupleta_opcion

    st.markdown(f"<div class='subasta-header'>🎟️ Módulo de {sub_dup_actual}</div>", unsafe_allow_html=True)
    if st.session_state.dupleta_bloqueada:
        st.error("🔒 **BLOQUEADO:** Emisión cerrada.")

    monto_unico_seccion = st.session_state.config_montos_especiales.get(sub_dup_actual, 500.0)

    if sub_dup_actual == "Dupleta":
        pote_total = sum([t['monto'] for t in st.session_state.dupletas_tickets])
        st.metric("💰 Pote Acumulado Dupletas", formatear_bs(pote_total))
        carreras_permitidas = [c for c in st.session_state.carreras_habilitadas_dupleta if c in lista_carreras_disponibles]
    elif sub_dup_actual == "Tripleta":
        pote_total = sum([t['monto'] for t in st.session_state.tripleta_tickets])
        st.metric("💰 Pote Acumulado Tripletas", formatear_bs(pote_total))
        carreras_permitidas = [c for c in st.session_state.carreras_habilitadas_tripleta if c in lista_carreras_disponibles]
    else:
        pote_total = sum([t['monto'] for t in st.session_state.polla_tickets])
        st.metric("💰 Pote Acumulado Polla Hípica", formatear_bs(pote_total))
        carreras_permitidas = [c for c in st.session_state.carreras_habilitadas_polla if c in lista_carreras_disponibles]

    with st.container(border=True):
        jugador_ticket = st.session_state.usuario_activo
        st.markdown(f"👤 **Jugador Actual:** `{jugador_ticket}` &nbsp;&nbsp;|&nbsp;&nbsp; 💰 **Monto Único:** `{formatear_bs(monto_unico_seccion)}`")

    if not carreras_permitidas:
        st.warning(f"⚠️ No hay carreras habilitadas para **{sub_dup_actual}**. Configúralas en la Zona Admin (Config. Dupletas/Polla).")
    else:
        with st.container(border=True):
            st.markdown(f"🎯 **Armado de Ticket Horizontal (Carreras establecidas en Zona Admin):**")
            
            seleccion_legs = []
            carreras_usadas_en_ticket = set()
            valido_legs = True
            
            num_carrs_permitidas = len(carreras_permitidas)
            cols_horizontales = st.columns(min(num_carrs_permitidas, 4) if num_carrs_permitidas > 0 else 1, gap="small")
            
            for i, carr_leg in enumerate(carreras_permitidas):
                col_target = cols_horizontales[i % len(cols_horizontales)]
                with col_target:
                    st.markdown(f"**{carr_leg}**")
                    if carr_leg in st.session_state.imagenes_carreras:
                        st.image(st.session_state.imagenes_carreras[carr_leg], use_container_width=True)
                    else:
                        st.markdown("<div style='background: #161b22; border: 1px dashed #30363d; padding: 6px; text-align: center; font-size: 9px; border-radius: 4px; color: #8b949e; margin-bottom: 4px;'>Sin Imagen</div>", unsafe_allow_html=True)
                    
                    caballos_in_carr = list(st.session_state.remates.get(carr_leg, {}).keys())
                    cab_leg = st.selectbox(f"Ejemplar {carr_leg}", caballos_in_carr if caballos_in_carr else ["Sin Caballos"], key=f"{sub_dup_actual.lower()}_sel_ejemplar_horizontal_{i}", label_visibility="collapsed")
                    
                    if carr_leg in carreras_usadas_en_ticket:
                        valido_legs = False
                    carreras_usadas_en_ticket.add(carr_leg)
                    seleccion_legs.append({"carrera": carr_leg, "ejemplar": cab_leg})

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
                        st.error("❌ **BLOQUEADO:** Ya existe un ticket con exactamente esta misma combinación.")
                    else:
                        prefijo_id = "DUP" if sub_dup_actual == "Dupleta" else ("TRIP" if sub_dup_actual == "Tripleta" else "POLL")
                        ticket_id = f"{prefijo_id}-{len(lista_tickets_activo) + 1:04d}"
                        
                        nuevo_ticket_dict = {
                            "id": ticket_id, "jugador": jugador_ticket, "monto": monto_unico_seccion,
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
                            "jugador": jugador_ticket,
                            "tipo": sub_dup_actual,
                            "carrera": "Múltiple",
                            "detalle": f"Ticket {ticket_id} ({detalles_str})",
                            "monto": monto_unico_seccion
                        })
                        if jugador_ticket not in st.session_state.cuentas:
                            st.session_state.cuentas[jugador_ticket] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                        st.session_state.cuentas[jugador_ticket]['Pujas'] += monto_unico_seccion
                        
                        st.success(f"✅ ¡Ticket {ticket_id} emitido con éxito!")
                        st.rerun()

    st.markdown("---")
    st.markdown(f"### 📋 Tickets de {sub_dup_actual} Emitidos en la Jornada")
    lista_tickets_activo_ver = (
        st.session_state.dupletas_tickets if sub_dup_actual == "Dupleta" else
        st.session_state.tripleta_tickets if sub_dup_actual == "Tripleta" else
        st.session_state.polla_tickets
    )
    if not lista_tickets_activo_ver:
        st.info("No hay tickets emitidos todavía en esta sección.")
    else:
        for t in reversed(lista_tickets_activo_ver):
            with st.container(border=True):
                col_t1, col_t2, col_t3 = st.columns([2, 2, 2])
                col_t1.markdown(f"🏷️ **Ticket:** `{t['id']}`")
                col_t2.markdown(f"👤 **Jugador:** `{t['jugador']}`")
                col_t3.markdown(f"💰 **Monto:** `{formatear_bs(t['monto'])}`")
                
                st.markdown("🔍 **Selecciones:**")
                detalles_legs = " ➔ ".join([f"**{l['carrera']}**: {l['ejemplar']}" for l in t['legs']])
                st.markdown(f"> {detalles_legs}")
                st.caption(f"Emitido el: {t['fecha']}")

# =========================================================================
# 3. MÓDULO DE CUENTAS
# =========================================================================
elif menu_principal_opcion == "Cuentas":
    st.markdown("<div class='subasta-header'>📊 Mis Cuentas y Estado de Deuda</div>", unsafe_allow_html=True)
    
    jugador_actual = st.session_state.usuario_activo
    st.markdown(f"👤 **Jugador en Sesión:** `{jugador_actual}`")

    if jugador_actual not in st.session_state.cuentas:
        st.session_state.cuentas[jugador_actual] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
    
    vals = st.session_state.cuentas[jugador_actual]
    pujas, premios, abonos = vals['Pujas'], vals['Premios'], vals['Abonos']
    balance_neto = pujas - abonos - premios

    col_cu1, col_cu2, col_cu3, col_cu4 = st.columns(4, gap="small")
    col_cu1.metric("🛒 Compras/Pujas", formatear_bs(pujas))
    col_cu2.metric("🏆 Premios", formatear_bs(premios))
    col_cu3.metric("💳 Pagos", formatear_bs(abonos))
    col_cu4.metric("⚖️ Neto a Pagar", formatear_bs(balance_neto))

    st.markdown("---")
    st.markdown(f"### 📜 Historial Detallado de lo Jugado por `{jugador_actual}`")
    
    historial_usuario = [h for h in st.session_state.historial_jugadas if h['jugador'] == jugador_actual]

    if not historial_usuario:
        st.info(f"ℹ️ No tienes jugadas ni remates registrados en esta jornada.")
    else:
        datos_historial = []
        for h in reversed(historial_usuario):
            datos_historial.append({
                "Fecha / Hora": h['fecha'],
                "Tipo": h['tipo'],
                "Carrera": h['carrera'],
                "Detalle / Ejemplar": h['detalle'],
                "Monto": formatear_bs(h['monto'])
            })
        st.dataframe(pd.DataFrame(datos_historial), use_container_width=True, hide_index=True)

# =========================================================================
# 4. ZONA DE ADMINISTRADOR
# =========================================================================
elif menu_principal_opcion == "🔒 Zona Admin":
    st.markdown("<div class='subasta-header'>🔒 Zona de Administrador</div>", unsafe_allow_html=True)
    
    opciones_admin_tabs = ["✍️ Banco de Caballos", "👥 Registro Usuarios", "⚙️ Config. Dupletas/Polla", "📺 Video En Vivo", "📊 Saldos Usuarios", "🖼️ Imágenes Carrera", "📄 Importar Web/Texto"]
    
    cols_adm_tabs = st.columns(len(opciones_admin_tabs), gap="small")
    for idx, tab_nombre in enumerate(opciones_admin_tabs):
        with cols_adm_tabs[idx]:
            es_tab_activa = (st.session_state.admin_tab_seleccionada == tab_nombre)
            if st.button(tab_nombre, key=f"adm_tab_btn_{idx}", use_container_width=True, type="primary" if es_tab_activa else "secondary"):
                st.session_state.admin_tab_seleccionada = tab_nombre
                st.rerun()

    st.markdown("<hr style='margin: 0.5rem 0; border-color: #30363d;'>", unsafe_allow_html=True)
    tab_actual = st.session_state.admin_tab_seleccionada

    if tab_actual == "✍️ Banco de Caballos":
        st.markdown("### ✍️ Banco de Caballos, Carreras Activas y Configuración Semanal")
        
        with st.container(border=True):
            st.markdown("📅 **Configuración General de la Semana**")
            nueva_cantidad_carreras = st.number_input(
                "¿Cuántas carreras van a correr esta semana?", 
                min_value=1, 
                max_value=25, 
                value=int(st.session_state.total_carreras_semana), 
                step=1, 
                key="input_total_carreras_semana"
            )
            if st.button("💾 Actualizar Cantidad de Carreras", key="btn_actualizar_cant_carreras", use_container_width=True, type="primary"):
                st.session_state.total_carreras_semana = nueva_cantidad_carreras
                for i in range(1, nueva_cantidad_carreras + 1):
                    c_n = f"Carrera {i}"
                    if c_n not in st.session_state.banco_caballos_por_carrera:
                        st.session_state.banco_caballos_por_carrera[c_n] = [f"{j} - Ejemplar {j}" for j in range(1, 11)]
                        st.session_state.remates[c_n] = {f"{j} - Ejemplar {j}": {"jugador": "Sin Postor", "monto": 0.0} for j in range(1, 11)}
                        st.session_state.detalles_carreras[c_n] = {"condicion": "Condición estándar", "distancia": "1200 mts", "hora": "02:00 PM", "monto_fijo_ciego": 500.0, "incentivo": 0.0}
                st.toast(f"✅ ¡Jornada ajustada a {nueva_cantidad_carreras} carreras!")
                st.rerun()

        st.markdown("---")

        # --- PANEL DIDÁCTICO DE CARRERAS ACTIVAS PARA REMATE ---
        with st.container(border=True):
            st.markdown("⚡ **Panel Didáctico: Selección de Carreras Activas para Remate**")
            st.info("💡 Marca las casillas de las carreras que deseas activar o desactivar para los remates de la jornada de forma visual e intuitiva.")
            
            carreras_disponibles_todas = list(st.session_state.remates.keys())
            if not carreras_disponibles_todas:
                st.warning("⚠️ No hay carreras en el banco. Importa contenido o crea la jornada primero.")
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
                
                if st.button("💾 Guardar Carreras Activas Seleccionadas", key="btn_save_activas_didactico", use_container_width=True, type="primary"):
                    st.session_state.carreras_activas_remate = nuevas_activas
                    st.toast("✅ ¡Carreras activas actualizadas con éxito!")
                    st.rerun()

        st.markdown("---")

        # --- SELECCIONADOR DE LAS 2 CARRERAS PARA REMATE CIEGO ---
        with st.container(border=True):
            st.markdown("🙈 **Selección de las 2 Carreras Activas para Remate Ciego (Identificadas como 1V y 6V)**")
            carreras_existentes = list(st.session_state.remates.keys())
            carreras_ciego_actuales = st.session_state.carreras_por_modalidad.get("Ciegos", [])
            
            default_ciego = [c for c in carreras_ciego_actuales if c in carreras_existentes][:2]

            carreras_ciego_seleccionadas = st.multiselect(
                "Elige exactamente 2 carreras para el Ciego:",
                options=carreras_existentes,
                default=default_ciego,
                key="multiselect_carreras_ciego"
            )
            
            if st.button("💾 Guardar Carreras para Remate Ciego", key="btn_save_carr_ciego", use_container_width=True, type="primary"):
                if len(carreras_ciego_seleccionadas) != 2:
                    st.error("⚠️ Debes seleccionar exactamente 2 carreras para el Remate Ciego.")
                else:
                    st.session_state.carreras_por_modalidad["Ciegos"] = carreras_ciego_seleccionadas
                    st.toast("✅ ¡Carreras de Remate Ciego guardadas con éxito!")
                    st.rerun()

        st.markdown("---")
        carr_banco_sel = st.selectbox("Seleccionar Carrera para Configurar y Editar", lista_carreras_disponibles, key="adm_banco_sel_carrera")
        
        if carr_banco_sel not in st.session_state.banco_caballos_por_carrera:
            st.session_state.banco_caballos_por_carrera[carr_banco_sel] = []
        if carr_banco_sel not in st.session_state.detalles_carreras:
            st.session_state.detalles_carreras[carr_banco_sel] = {"condicion": "Condición general", "distancia": "1200 mts", "hora": "02:00 PM", "monto_fijo_ciego": 500.0, "incentivo": 0.0}

        det_actuales = st.session_state.detalles_carreras[carr_banco_sel]
        with st.container(border=True):
            st.markdown(f"🛠️ **Editar Detalles e Incentivo de {carr_banco_sel}**")
            edit_cond = st.text_input("Condición de la carrera", value=det_actuales.get('condicion', ''), key=f"banco_cond_{carr_banco_sel}")
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                edit_dist = st.text_input("Distancia", value=det_actuales.get('distancia', ''), key=f"banco_dist_{carr_banco_sel}")
            with col_b2:
                edit_hora = st.text_input("Hora", value=det_actuales.get('hora', ''), key=f"banco_hora_{carr_banco_sel}")
            with col_b3:
                edit_incentivo = st.number_input("Incentivo (Extra)", min_value=0.0, value=float(det_actuales.get('incentivo', 0.0)), step=50.0, key=f"banco_incentivo_{carr_banco_sel}")
            
            if st.button("💾 Guardar Detalles de Carrera", key=f"btn_save_banco_det_{carr_banco_sel}", use_container_width=True, type="primary"):
                st.session_state.detalles_carreras[carr_banco_sel] = {
                    "condicion": edit_cond, 
                    "distancia": edit_dist, 
                    "hora": edit_hora, 
                    "monto_fijo_ciego": det_actuales.get('monto_fijo_ciego', 500.0),
                    "incentivo": edit_incentivo
                }
                st.toast("✅ ¡Detalles e incentivo guardados con éxito!")
                st.rerun()

        st.markdown("---")
        st.markdown("#### 🐎 Ejemplares Inscritos")
        with st.container(border=True):
            nuevo_nom_banco = st.text_input("Nombre del Ejemplar", placeholder="Ej: Rey David", key=f"adm_banco_input_{carr_banco_sel}")
            if st.button("💾 Agregar al Banco", key=f"adm_banco_btn_add_{carr_banco_sel}", use_container_width=True, type="primary"):
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
                    st.toast("✅ ¡Agregado con éxito y ordenado por posición!")
                    st.rerun()

        for idx_b, ej_item in enumerate(st.session_state.banco_caballos_por_carrera[carr_banco_sel]):
            col_ib1, col_ib2 = st.columns([5, 1])
            with col_ib1: st.text(ej_item)
            with col_ib2:
                if st.button("🗑️", key=f"adm_banco_del_{carr_banco_sel}_{idx_b}", use_container_width=True):
                    st.session_state.banco_caballos_por_carrera[carr_banco_sel].pop(idx_b)
                    if carr_banco_sel in st.session_state.remates and ej_item in st.session_state.remates[carr_banco_sel]:
                        del st.session_state.remates[carr_banco_sel][ej_item]
                    st.rerun()

    elif tab_actual == "👥 Registro Usuarios":
        st.markdown("### 👥 Registro de Nuevos Usuarios")
        with st.container(border=True):
            nuevo_usuario_input = st.text_input("Nombre del Nuevo Usuario", placeholder="Ej: JUAN", key="input_nuevo_usuario_reg")
            if st.button("➕ Registrar Usuario", key="btn_registrar_nuevo_usuario", use_container_width=True, type="primary"):
                usuario_limpio = nuevo_usuario_input.strip().upper()
                if not usuario_limpio:
                    st.warning("⚠️ Escribe un nombre válido.")
                elif usuario_limpio in st.session_state.lista_usuarios:
                    st.error("❌ El usuario ya existe en el sistema.")
                else:
                    st.session_state.lista_usuarios.append(usuario_limpio)
                    if usuario_limpio not in st.session_state.cuentas:
                        st.session_state.cuentas[usuario_limpio] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                    st.toast(f"✅ ¡Usuario **{usuario_limpio}** registrado con éxito!")
                    st.rerun()

        st.markdown("---")
        st.markdown("#### 📋 Lista de Usuarios Registrados Actualmente")
        for u in st.session_state.lista_usuarios:
            col_u1, col_u2 = st.columns([4, 1])
            with col_u1:
                st.markdown(f"👤 **{u}**")
            with col_u2:
                if u != "CASA":
                    if st.button("🗑️", key=f"btn_del_usu_{u}", use_container_width=True):
                        st.session_state.lista_usuarios.remove(u)
                        if u in st.session_state.cuentas:
                            del st.session_state.cuentas[u]
                        if st.session_state.usuario_activo == u:
                            st.session_state.usuario_activo = "CASA"
                        st.rerun()

    elif tab_actual == "⚙️ Config. Dupletas/Polla":
        st.markdown("### ⚙️ Configuración de Carreras Habilitadas y Montos Únicos")
        
        with st.container(border=True):
            st.markdown("💰 **Montos Únicos por Ticket o Polla**")
            monto_dup_cfg = st.number_input("Monto Único para Dupleta (Bs.)", min_value=0.0, value=float(st.session_state.config_montos_especiales.get("Dupleta", 500.0)), step=50.0, key="cfg_monto_dupleta")
            monto_trip_cfg = st.number_input("Monto Único para Tripleta (Bs.)", min_value=0.0, value=float(st.session_state.config_montos_especiales.get("Tripleta", 500.0)), step=50.0, key="cfg_monto_tripleta")
            monto_polla_cfg = st.number_input("Monto Único para Polla Hípica (Bs.)", min_value=0.0, value=float(st.session_state.config_montos_especiales.get("Polla Hipica", 1000.0)), step=50.0, key="cfg_monto_polla")
            
            if st.button("💾 Guardar Montos Únicos", key="btn_save_montos_cfg", use_container_width=True, type="primary"):
                st.session_state.config_montos_especiales["Dupleta"] = monto_dup_cfg
                st.session_state.config_montos_especiales["Tripleta"] = monto_trip_cfg
                st.session_state.config_montos_especiales["Polla Hipica"] = monto_polla_cfg
                st.toast("✅ ¡Montos únicos guardados con éxito!")
                st.rerun()

        st.markdown("---")
        with st.container(border=True):
            st.markdown("🏇 **Carreras Habilitadas por Sección (Dupleta, Tripleta, Polla Hípica)**")
            st.info("💡 Selecciona qué carreras de la jornada estarán disponibles para que los jugadores armen sus tickets y pollas.")
            
            carr_disp_all = list(st.session_state.remates.keys())
            
            def_dup = [c for c in st.session_state.carreras_habilitadas_dupleta if c in carr_disp_all]
            def_trip = [c for c in st.session_state.carreras_habilitadas_tripleta if c in carr_disp_all]
            def_polla = [c for c in st.session_state.carreras_habilitadas_polla if c in carr_disp_all]

            sel_dup_hab = st.multiselect("Carreras Habilitadas para Dupleta", options=carr_disp_all, default=def_dup, key="multiselect_hab_dup")
            sel_trip_hab = st.multiselect("Carreras Habilitadas para Tripleta", options=carr_disp_all, default=def_trip, key="multiselect_hab_trip")
            sel_polla_hab = st.multiselect("Carreras Habilitadas para Polla Hípica", options=carr_disp_all, default=def_polla, key="multiselect_hab_polla")

            if st.button("💾 Guardar Carreras Habilitadas", key="btn_save_carr_hab", use_container_width=True, type="primary"):
                st.session_state.carreras_habilitadas_dupleta = sel_dup_hab
                st.session_state.carreras_habilitadas_tripleta = sel_trip_hab
                st.session_state.carreras_habilitadas_polla = sel_polla_hab
                st.toast("✅ ¡Configuración de carreras habilitadas guardada con éxito!")
                st.rerun()

    elif tab_actual == "📺 Video En Vivo":
        st.markdown("### 📺 Configuración de Transmisión de Video en Vivo")
        with st.container(border=True):
            st.markdown("Pega la URL del video en vivo (YouTube, enlace de transmisión, MP4, etc.):")
            nueva_url_video = st.text_input("URL del Video en Vivo", value=st.session_state.get('url_video_en_vivo', ''), placeholder="Ej: https://www.youtube.com/watch?v=XXXXXXX", key="input_live_video_url")
            
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                if st.button("💾 Guardar Transmisión", key="btn_save_video_url", use_container_width=True, type="primary"):
                    st.session_state.url_video_en_vivo = nueva_url_video.strip()
                    st.toast("✅ ¡URL de transmisión guardada y activa!")
                    st.rerun()
            with col_v2:
                if st.button("🗑️ Desactivar Transmisión", key="btn_clear_video_url", use_container_width=True):
                    st.session_state.url_video_en_vivo = ""
                    st.toast("🗑️ Transmisión desactivada.")
                    st.rerun()

    elif tab_actual == "📊 Saldos Usuarios":
        st.markdown("### 📊 Saldos y Cuentas de Usuarios Registrados")
        usuarios_futuros = [u for u in st.session_state.lista_usuarios if u != "CASA"]
        
        if not usuarios_futuros:
            st.info("ℹ️ No hay usuarios registrados todavía (solo está la cuenta de la Casa). Agrega nuevos usuarios desde la pestaña '👥 Registro Usuarios'.")
        else:
            datos_cuentas_adm = []
            for jugador in usuarios_futuros:
                if jugador not in st.session_state.cuentas:
                    st.session_state.cuentas[jugador] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                vals = st.session_state.cuentas[jugador]
                pujas, premios, abonos = vals['Pujas'], vals['Premios'], vals['Abonos']
                balance_neto = pujas - abonos - premios
                datos_cuentas_adm.append({"Usuario": jugador, "Compras": formatear_bs(pujas), "Premios": formatear_bs(premios), "Abonos/Pagos": formatear_bs(abonos), "Neto a Pagar": formatear_bs(balance_neto)})
            st.dataframe(pd.DataFrame(datos_cuentas_adm), use_container_width=True, hide_index=True)

        st.metric("Ganancia Total Casa", formatear_bs(st.session_state.ganancia_casa))

        st.markdown("---")
        st.markdown("#### 💵 Registrar Abono o Pago a Usuario")
        col_ab1, col_ab2, col_ab3 = st.columns(3, gap="small")
        with col_ab1:
            jugador_abonar = st.selectbox("Usuario", st.session_state.lista_usuarios, key="adm_abono_jugador")
        with col_ab2:
            monto_abono = st.number_input("Monto Abono (Bs.)", min_value=0.0, step=100.0, key="adm_abono_monto")
        with col_ab3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ Aplicar Abono", key="adm_btn_aplicar_abono", use_container_width=True, type="primary"):
                if jugador_abonar not in st.session_state.cuentas:
                    st.session_state.cuentas[jugador_abonar] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                st.session_state.cuentas[jugador_abonar]['Abonos'] += monto_abono
                st.toast(f"✅ Abono de {formatear_bs(monto_abono)} registrado a {jugador_abonar}")
                st.rerun()

    elif tab_actual == "🖼️ Imágenes Carrera":
        st.markdown("### 🖼️ Cargar Imagen Representativa por Carrera (Dupletas y Remates)")
        carr_img_sel = st.selectbox("Seleccionar Carrera", lista_carreras_disponibles, key="adm_img_sel_carr")
        
        imagen_subida = st.file_uploader(f"Subir imagen para {carr_img_sel}", type=["png", "jpg", "jpeg"], key=f"file_img_{carr_img_sel}")
        if imagen_subida is not None:
            if st.button(f"💾 Guardar Imagen para {carr_img_sel}", key=f"btn_save_img_{carr_img_sel}", use_container_width=True, type="primary"):
                st.session_state.imagenes_carreras[carr_img_sel] = imagen_subida
                st.toast(f"✅ Imagen asignada correctamente a {carr_img_sel}")
                st.rerun()

        if carr_img_sel in st.session_state.imagenes_carreras:
            st.markdown("---")
            st.markdown("**Imagen actual asignada:**")
            st.image(st.session_state.imagenes_carreras[carr_img_sel], width=300)
            if st.button("🗑️ Eliminar Imagen", key=f"btn_del_img_{carr_img_sel}", use_container_width=True):
                del st.session_state.imagenes_carreras[carr_img_sel]
                st.toast("🗑️ Removida")
                st.rerun()

    elif tab_actual == "📄 Importar Web/Texto":
        st.markdown("### 🌐 Importar Inscritos, Condición, Hora y Distancia")
        st.markdown("Pega aquí el texto con los datos de las carreras y ejemplares:")
        
        texto_copiado_web = st.text_area(
            "Contenido copiado:",
            value="",
            height=220,
            key="text_area_web_copiado",
            placeholder="Primera Carrera - 1.200 mts - 02:00 PM\n1 - Rey David\n2 - Gran Amigo\n\nSegunda Carrera - 1.400 mts - 02:30 PM\n1 - Rayo Negro"
        )
        if st.button("🚀 Procesar Contenido Pegado", key="btn_procesar_texto_pegado", use_container_width=True, type="primary"):
            if texto_copiado_web.strip():
                if procesar_texto_flexible(texto_copiado_web):
                    st.success("✅ ¡Inscritos organizados por carrera y editables con éxito!")
                    st.rerun()
                else:
                    st.warning("⚠️ Asegúrate de incluir el nombre de cada carrera (ej: 'Primera Carrera' o 'Carrera 1') seguido de los ejemplares numerados (ej: '1 - Nombre').")
            else:
                st.warning("⚠️ El campo de texto está vacío.")

# =========================================================================
# TRANSMISIÓN EN VIVO DE LAS CARRERAS (REPRODUCTOR COMPATIBLE Y ADAPTADO)
# =========================================================================
url_live_video = st.session_state.get('url_video_en_vivo', '').strip()

if url_live_video:
    st.markdown("<br><hr style='border-color: #30363d;'>", unsafe_allow_html=True)
    st.markdown("### 📺 TRANSMISIÓN EN VIVO DE LAS CARRERAS")
    
    # Extraer ID si es un enlace estándar de YouTube
    yt_match = re.search(r'(?:v=|\/embed\/|youtu\.be\/|\/v\/|\/e\/|watch\?v=|&v=)([^#&?]{11})', url_live_video)
    
    if yt_match:
        yt_id = yt_match.group(1)
        # Formato de URL adaptable de YouTube que funciona perfecto tanto en Streamlit Móvil como en PC
        embed_url = f"https://www.youtube.com/embed/{yt_id}?playsinline=1"
        try:
            st.video(embed_url)
        except Exception:
            st.video(url_live_video)
    else:
        try:
            st.video(url_live_video)
        except Exception:
            st.warning("⚠️ No se pudo cargar el video con la URL proporcionada. Verifica el enlace en la Zona Admin.")
