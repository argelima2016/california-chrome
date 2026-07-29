import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import re
import base64
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from streamlit_autorefresh import st_autorefresh

# Configuración de pantalla completa
st.set_page_config(page_title="WOLF READY TO RUN", layout="wide", page_icon="🐺")

# --- AUTOREFRESH (3 SEGUNDOS) ---
try:
    st_autorefresh(interval=3000, key="datarefresh_en_vivo")
except Exception:
    pass

# --- SCRIPT JS PARA OCULTAR ELEMENTOS NATIVOS DE STREAMLIT ---
components.html("""
    <script>
        function ocultarElementosNativos() {
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
                    el.style.display = 'none';
                    el.style.visibility = 'hidden';
                    el.style.opacity = '0';
                    el.remove();
                });
            });
        }
        setInterval(ocultarElementosNativos, 200);
    </script>
""", height=0, width=0)

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

# --- ESTILOS CSS CON BURBUJAS EN FORMATO CÁPSULA / PASTILLA ---
st.markdown("""
    <style>
    .stApp {
        background-color: #080a0f;
        color: #f0f6fc;
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
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
        max-width: 1400px !important;
        margin: 0 auto !important;
    }
    .stButton button {
        border-radius: 6px !important;
        font-weight: 700 !important;
        padding: 0.2rem 0.4rem !important;
        min-height: 32px !important;
        font-size: 12px !important;
        letter-spacing: 0.2px;
        white-space: nowrap !important;
    }
    
    /* --- NUEVO MODELO: BURBUJAS EN FORMATO CÁPSULA / PASTILLA --- */
    div[data-testid="column"] button[kind="secondary"], 
    div[data-testid="column"] button[kind="primary"] {
        border-radius: 20px !important;
        width: 100% !important;
        height: 42px !important;
        min-height: 42px !important;
        max-height: 42px !important;
        padding: 0 8px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 2px auto !important;
        font-size: 12px !important;
        font-weight: 900 !important;
        letter-spacing: 0.5px !important;
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
    color_balance = "#ff4757"  # Rojo elegante
elif neto_usuario < 0:
    etiqueta_balance = f"Premio: {formatear_bs(abs(neto_usuario))}"
    color_balance = "#2ed573"  # Verde brillante
else:
    etiqueta_balance = "Al día: Bs. 0,00"
    color_balance = "#58a6ff"  # Azul neón

# --- CABECERA SUPERIOR DE DOS FILAS ---
st.markdown(f"""
    <style>
    .premium-header-two-rows {{
        background: #0a0d14;
        border: none;
        box-shadow: none;
        padding: 6px 4px 14px 4px;
        display: flex;
        flex-direction: column;
        gap: 14px;
        margin-bottom: 12px;
        width: 100%;
        box-sizing: border-box;
    }}
    .header-top-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        gap: 10px;
    }}
    .header-clock-box {{
        background: #0d1117;
        border: 1px solid #30363d;
        padding: 6px 12px;
        border-radius: 8px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        flex-shrink: 0;
    }}
    .h-time {{
        color: #f1c40f;
        font-size: 13px;
        font-weight: 900;
        letter-spacing: 0.5px;
    }}
    .h-date {{
        color: #8b949e;
        font-size: 10px;
        font-weight: 600;
    }}
    .header-user-card {{
        background: #0d1117;
        border: 1px solid #30363d;
        padding: 6px 14px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        gap: 12px;
        flex-shrink: 0;
    }}
    .user-details {{
        display: flex;
        flex-direction: column;
        text-align: right;
        line-height: 1.2;
    }}
    .u-name {{
        color: #ffffff;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0.3px;
    }}
    .u-bal {{
        color: {color_balance};
        font-size: 11px;
        font-weight: 800;
    }}
    .u-avatar-badge {{
        background: linear-gradient(135deg, #f1c40f 0%, #e67e22 100%);
        color: #000000;
        width: 38px;
        height: 38px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        font-weight: 900;
        box-shadow: 0px 0px 10px rgba(241, 196, 15, 0.4);
    }}
    .header-bottom-row-logo {{
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        padding-top: 4px;
    }}
    .header-logo-img {{
        max-height: 120px;
        width: auto;
        max-width: 100%;
        object-fit: contain;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        filter: drop-shadow(0px 4px 16px rgba(241, 196, 15, 0.35));
    }}
    </style>

    <div class="premium-header-two-rows">
        <div class="header-top-row">
            <div class="header-clock-box">
                <span class="h-time">⚡ {hora_texto}</span>
                <span class="h-date">📅 {fecha_texto}</span>
            </div>
            <div class="header-user-card">
                <div class="user-details">
                    <span class="u-name">{usuario_en_sesion}</span>
                    <span class="u-bal">{etiqueta_balance}</span>
                </div>
                <div class="u-avatar-badge">🐺</div>
            </div>
        </div>
        <div class="header-bottom-row-logo">
            {logo_display}
        </div>
    </div>
""", unsafe_allow_html=True)

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

# --- CARRUSEL AUTOMÁTICO DE IMÁGENES ---
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
        body {{
            margin: 0;
            padding: 0;
            background-color: #080a0f;
            overflow: hidden;
        }}
        .banner-slider-container {{
            width: 100vw;
            height: 240px;
            margin: 0;
            padding: 0;
            border: none !important;
            outline: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            overflow: hidden;
            position: relative;
            background-color: #080a0f;
        }}
        .banner-slide-img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            border: none !important;
            outline: none !important;
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
    components.html(html_slider, height=245)
else:
    st.markdown("""
        <div style="background: linear-gradient(90deg, #11141d 0%, #1f2937 100%); padding: 15px; text-align: center; margin-bottom: 10px;">
            <h3 style="color: #f1c40f; margin: 0; font-weight: 900; letter-spacing: 1px;">INH - HIPÓDROMO DE LA RINCONADA</h3>
            <p style="color: #8b949e; font-size: 12px; margin: 4px 0 0 0;">¡La pasión del hipismo venezolano en vivo!</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- BARRA LATERAL (IZQUIERDA) ---
st.sidebar.header("Barra Lateral")
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

with st.sidebar.expander("🏁 Cierre y Liquidación de Remates", expanded=False):
    carr_seleccionada_liq = st.selectbox("Gestionar Carrera", lista_carreras_disponibles, key="sb_liq_sel_carrera")
    c_cerrada_actual = st.session_state.carreras_cerradas_remate.get(carr_seleccionada_liq, False)
    
    if c_cerrada_actual:
        st.error(f"🔴 {carr_seleccionada_liq} se encuentra CERRADA")
        if st.button("🔓 Reabrir Remates de la Carrera", key=f"sb_reabrir_{carr_seleccionada_liq}"):
            st.session_state.carreras_cerradas_remate[carr_seleccionada_liq] = False
            st.success(f"Se reabrieron las pujas para {carr_seleccionada_liq}")
            st.rerun()
    else:
        st.success(f"🟢 {carr_seleccionada_liq} se encuentra ABIERTA")
        if st.button("🔒 Cerrar Definitivamente Carrera", key=f"sb_cerrar_{carr_seleccionada_liq}"):
            st.session_state.carreras_cerradas_remate[carr_seleccionada_liq] = True
            st.warning(f"Se cerraron las pujas para {carr_seleccionada_liq}")
            st.rerun()

    st.markdown("---")
    st.subheader("🏆 Cargar Ganador y Liquidar")
    
    lista_ejemplares_liq = st.session_state.banco_caballos_por_carrera.get(carr_seleccionada_liq, [])
    if lista_ejemplares_liq:
        ganador_seleccionado = st.selectbox("Seleccionar Ejemplar Ganador", lista_ejemplares_liq, key="sb_liq_sel_ganador")
        
        if st.button("💰 Liquidar Premio a Ganador", key="sb_btn_liquidar"):
            info_ganador = st.session_state.remates[carr_seleccionada_liq].get(ganador_seleccionado, {"jugador": "Sin Postor", "monto": 0.0})
            comprador = info_ganador["jugador"]
            
            pozo_total = sum(datos["monto"] for datos in st.session_state.remates[carr_seleccionada_liq].values())
            inc = st.session_state.detalles_carreras[carr_seleccionada_liq].get("incentivo", 0.0)
            pozo_total_con_incentivo = pozo_total + inc
            
            retencion = (porcentaje_casa / 100.0) * pozo_total
            premio_neto = pozo_total_con_incentivo - retencion
            
            if comprador != "Sin Postor":
                if comprador not in st.session_state.cuentas:
                    st.session_state.cuentas[comprador] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                
                st.session_state.cuentas[comprador]['Premios'] += premio_neto
                st.session_state.ganancia_casa += retencion
                st.session_state.historial_ganadores[carr_seleccionada_liq] = {
                    "ejemplar": ganador_seleccionado,
                    "ganador": comprador,
                    "premio": premio_neto
                }
                st.success(f"¡Premio de {formatear_bs(premio_neto)} acreditado con éxito a {comprador}!")
                st.rerun()
            else:
                st.error("El ejemplar ganador no tuvo postor. El pozo pasa a la CASA.")

# ==============================================================================
# SECCIÓN PRINCIPAL SEGÚN OPCIÓN SELECCIONADA EN EL MENÚ
# ==============================================================================

# ------------------------------------------------------------------------------
# OPCIÓN 1: REMATES
# ------------------------------------------------------------------------------
if st.session_state.menu_principal_opcion == "Remates":
    col_sub1, col_sub2, col_sub3 = st.columns(3, gap="small")
    with col_sub1:
        if st.button("EN VIVO", key="btn_sub_envivo", use_container_width=True, type="primary" if st.session_state.sub_remate_opcion == "En Vivo" else "secondary"):
            st.session_state.sub_remate_opcion = "En Vivo"
            st.rerun()
    with col_sub2:
        if st.button("ADELANTADOS", key="btn_sub_adelantados", use_container_width=True, type="primary" if st.session_state.sub_remate_opcion == "Adelantados" else "secondary"):
            st.session_state.sub_remate_opcion = "Adelantados"
            st.rerun()
    with col_sub3:
        if st.button("CIEGOS", key="btn_sub_ciegos", use_container_width=True, type="primary" if st.session_state.sub_remate_opcion == "Ciegos" else "secondary"):
            st.session_state.sub_remate_opcion = "Ciegos"
            st.rerun()

    modo_actual = st.session_state.sub_remate_opcion
    carreras_del_modo = st.session_state.carreras_por_modalidad.get(modo_actual, lista_carreras_disponibles)

    if not carreras_del_modo:
        st.info("No hay carreras configuradas para esta modalidad.")
    else:
        carrera_sel = st.selectbox("Seleccionar Carrera", carreras_del_modo, key="select_carrera_remate")
        
        detalles = st.session_state.detalles_carreras.get(carrera_sel, {"condicion": "-", "distancia": "-", "hora": "-", "incentivo": 0.0})
        
        st.markdown(f"""
            <div class="carrera-condicion-card">
                <b>📋 {carrera_sel}</b> | 📐 Distancia: <b>{detalles.get('distancia')}</b> | ⏰ Hora: <b>{detalles.get('hora')}</b><br>
                <i>{detalles.get('condicion')}</i>
            </div>
        """, unsafe_allow_html=True)
        
        if detalles.get("incentivo", 0.0) > 0:
            st.markdown(f"""
                <div class="incentivo-elegante">
                    <div class="incentivo-elegante-titulo">🎁 Incentivo Especial de la Casa</div>
                    <div class="incentivo-elegante-monto">{formatear_bs(detalles['incentivo'])}</div>
                </div>
            """, unsafe_allow_html=True)

        esta_cerrada = st.session_state.carreras_cerradas_remate.get(carrera_sel, False)
        
        if esta_cerrada:
            st.markdown("<div class='timer-box'>🔴 REMATE CERRADO PARA ESTA CARRERA</div>", unsafe_allow_html=True)
        
        dict_remates_carrera = st.session_state.remates.get(carrera_sel, {})
        tabla_html = generar_tabla_html_remate(dict_remates_carrera)
        st.markdown(tabla_html, unsafe_allow_html=True)

        if not esta_cerrada:
            st.markdown("<div class='subasta-header'>⚡ REALIZAR PUJA EN VIVO</div>", unsafe_allow_html=True)
            
            ejemplares_lista = list(dict_remates_carrera.keys())
            if ejemplares_lista:
                col_p1, col_p2 = st.columns([1, 1])
                
                with col_p1:
                    ejemplar_a_pujar = st.selectbox("Ejemplar", ejemplares_lista, key="sel_ejemplar_puja")
                    monto_actual_ej = dict_remates_carrera[ejemplar_a_pujar]["monto"]
                    opciones_monto = obtener_siguientes_montos(monto_actual_ej)
                    monto_seleccionado = st.selectbox("Monto a Pujar (Bs.)", opciones_monto, key="sel_monto_puja")

                with col_p2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🔥 CONFIRMAR PUJA", use_container_width=True, type="primary"):
                        usuario = st.session_state.usuario_activo
                        
                        st.session_state.remates[carrera_sel][ejemplar_a_pujar] = {
                            "jugador": usuario,
                            "monto": float(monto_seleccionado)
                        }
                        
                        if usuario not in st.session_state.cuentas:
                            st.session_state.cuentas[usuario] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                        
                        total_pujas_user = 0.0
                        for c_k, c_v in st.session_state.remates.items():
                            for ej_k, ej_v in c_v.items():
                                if ej_v["jugador"] == usuario:
                                    total_pujas_user += ej_v["monto"]
                        
                        st.session_state.cuentas[usuario]['Pujas'] = total_pujas_user
                        st.success(f"¡Puja registrada! {usuario} ofreció {formatear_bs(monto_seleccionado)} por {ejemplar_a_pujar}")
                        st.rerun()

# ------------------------------------------------------------------------------
# OPCIÓN 2: DUPLETAS / POLLAS HÍPICAS
# ------------------------------------------------------------------------------
elif st.session_state.menu_principal_opcion == "Dupletas":
    col_d1, col_d2, col_d3 = st.columns(3, gap="small")
    with col_d1:
        if st.button("DUPLETA", key="btn_sub_dupleta", use_container_width=True, type="primary" if st.session_state.sub_dupleta_opcion == "Dupleta" else "secondary"):
            st.session_state.sub_dupleta_opcion = "Dupleta"
            st.rerun()
    with col_d2:
        if st.button("TRIPLETA", key="btn_sub_tripleta", use_container_width=True, type="primary" if st.session_state.sub_dupleta_opcion == "Tripleta" else "secondary"):
            st.session_state.sub_dupleta_opcion = "Tripleta"
            st.rerun()
    with col_d3:
        if st.button("POLLA HÍPICA", key="btn_sub_polla", use_container_width=True, type="primary" if st.session_state.sub_dupleta_opcion == "Polla Hipica" else "secondary"):
            st.session_state.sub_dupleta_opcion = "Polla Hipica"
            st.rerun()

    sub_modalidad = st.session_state.sub_dupleta_opcion
    st.subheader(f"🎟️ Jugada Especial: {sub_modalidad}")
    
    monto_fijo = st.session_state.config_montos_especiales.get(sub_modalidad, 500.0)
    st.info(f"Monto por combinación: **{formatear_bs(monto_fijo)}**")

    if st.session_state.dupleta_bloqueada:
        st.error("🔒 Las jugadas especiales se encuentran temporalmente cerradas por la administración.")
    else:
        if sub_modalidad == "Dupleta":
            carreras_disponibles_spec = st.session_state.carreras_habilitadas_dupleta
            num_carreras_req = 2
        elif sub_modalidad == "Tripleta":
            carreras_disponibles_spec = st.session_state.carreras_habilitadas_tripleta
            num_carreras_req = 3
        else:
            carreras_disponibles_spec = st.session_state.carreras_habilitadas_polla
            num_carreras_req = len(carreras_disponibles_spec)

        if len(carreras_disponibles_spec) < num_carreras_req:
            st.warning(f"Se requieren al menos {num_carreras_req} carreras configuradas para esta modalidad.")
        else:
            carreras_seleccionadas_jugada = carreras_disponibles_spec[:num_carreras_req]
            
            selecciones = {}
            col_selec = st.columns(len(carreras_seleccionadas_jugada))
            
            for idx, c_nombre in enumerate(carreras_seleccionadas_jugada):
                with col_selec[idx]:
                    st.markdown(f"**{c_nombre}**")
                    opciones_cab = st.session_state.banco_caballos_por_carrera.get(c_nombre, [])
                    if opciones_cab:
                        selecciones[c_nombre] = st.selectbox(f"Seleccionar Ejemplar", opciones_cab, key=f"spec_{sub_modalidad}_{c_nombre}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(f"🎯 Sellar Ticket de {sub_modalidad}", type="primary", use_container_width=True):
                usuario = st.session_state.usuario_activo
                
                ticket = {
                    "usuario": usuario,
                    "modalidad": sub_modalidad,
                    "monto": monto_fijo,
                    "jugadas": selecciones,
                    "fecha": datetime.now().strftime("%d/%m/%Y %I:%M %p")
                }
                
                if sub_modalidad == "Dupleta":
                    st.session_state.dupletas_tickets.append(ticket)
                elif sub_modalidad == "Tripleta":
                    st.session_state.tripleta_tickets.append(ticket)
                else:
                    st.session_state.polla_tickets.append(ticket)

                if usuario not in st.session_state.cuentas:
                    st.session_state.cuentas[usuario] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                
                st.session_state.cuentas[usuario]['Pujas'] += monto_fijo
                st.success(f"¡Ticket de {sub_modalidad} registrado exitosamente para {usuario}!")
                st.rerun()

# ------------------------------------------------------------------------------
# OPCIÓN 3: CUENTAS
# ------------------------------------------------------------------------------
elif st.session_state.menu_principal_opcion == "Cuentas":
    st.subheader("📊 Estado de Cuentas General")

    df_cuentas = []
    for usr, datos in st.session_state.cuentas.items():
        total_pujas = datos['Pujas']
        total_premios = datos['Premios']
        total_abonos = datos['Abonos']
        saldo = total_pujas - total_abonos - total_premios
        
        df_cuentas.append({
            "Usuario": usr,
            "Total Jugado (Bs.)": formatear_bs(total_pujas),
            "Abonos (Bs.)": formatear_bs(total_abonos),
            "Premios (Bs.)": formatear_bs(total_premios),
            "Balance Neto": formatear_bs(saldo),
            "Estado": "Deuda 🔴" if saldo > 0 else ("A Favor 🟢" if saldo < 0 else "Al Día 🔵")
        })

    st.dataframe(pd.DataFrame(df_cuentas), use_container_width=True)

    st.markdown("---")
    st.subheader("💳 Registrar Abonos / Pagos de Clientes")
    
    col_a1, col_a2, col_a3 = st.columns(3)
    with col_a1:
        usr_abono = st.selectbox("Cliente", list(st.session_state.cuentas.keys()), key="sel_usr_abono")
    with col_a2:
        monto_abono = st.number_input("Monto de Abono (Bs.)", min_value=0.0, step=100.0, key="num_monto_abono")
    with col_a3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✅ Cargar Abono", use_container_width=True):
            if monto_abono > 0:
                st.session_state.cuentas[usr_abono]['Abonos'] += monto_abono
                st.success(f"Se cargó un abono de {formatear_bs(monto_abono)} a {usr_abono}")
                st.rerun()
            else:
                st.error("Ingrese un monto válido mayor a 0.")

    st.markdown("---")
    st.subheader("👤 Crear Nuevo Usuario")
    col_u1, col_u2 = st.columns([2, 1])
    with col_u1:
        nuevo_usuario_nombre = st.text_input("Nombre o Seudónimo del Jugador", key="txt_nuevo_usuario")
    with col_u2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Crear Usuario", use_container_width=True):
            nombre_limpio = nuevo_usuario_nombre.strip().upper()
            if nombre_limpio:
                if nombre_limpio not in st.session_state.lista_usuarios:
                    st.session_state.lista_usuarios.append(nombre_limpio)
                    st.session_state.cuentas[nombre_limpio] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                    st.success(f"Usuario '{nombre_limpio}' registrado con éxito.")
                    st.rerun()
                else:
                    st.warning("El usuario ya existe.")
            else:
                st.error("Ingrese un nombre válido.")
