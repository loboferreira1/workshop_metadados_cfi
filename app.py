import streamlit as st
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import pandas as pd
import base64
from pathlib import Path

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="O que sua foto revela?",
    page_icon="📸",
    layout="centered",          # Melhor para celular e projeção
    initial_sidebar_state="collapsed"
)

# ============================================================
# IDENTIDADE VISUAL (artes da pasta /art)
# ============================================================

def img_b64(caminho: str) -> str:
    """Lê uma imagem do disco e devolve em base64 (para CSS inline)."""
    return base64.b64encode(Path(caminho).read_bytes()).decode()

st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{img_b64('art/fundo.png')}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    div.block-container,
    div[data-testid="stAppViewBlockContainer"] {{
        position: relative;
        z-index: 1;
        background-color: rgba(255, 255, 255, 0.88);
        border-radius: 20px;
        padding: 2rem 2.5rem;
        margin-top: 1rem;
    }}
    .arte-campanha {{
        position: fixed;
        top: 50%;
        right: 3%;
        transform: translateY(-50%);
        width: min(230px, 22vw);
        z-index: 0;
        pointer-events: none;
        opacity: 0.92;
    }}
    </style>
    <div class="arte-campanha">
        <img src="data:image/png;base64,{img_b64('art/arte.png')}" style="width:100%;">
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# FUNÇÕES DE EXTRAÇÃO DE METADADOS
# ============================================================

def get_exif_data(image: Image.Image) -> dict:
    """Extrai todos os metadados EXIF da imagem."""
    exif_data = {}
    try:
        info = image._getexif()
        if info:
            for tag_id, value in info.items():
                tag_name = TAGS.get(tag_id, tag_id)
                exif_data[tag_name] = value
    except Exception:
        pass
    return exif_data


def get_decimal_coordinates(dms, ref):
    """Converte coordenadas DMS (graus, minutos, segundos) para decimal."""
    try:
        degrees = float(dms[0])
        minutes = float(dms[1]) / 60.0
        seconds = float(dms[2]) / 3600.0
        decimal = degrees + minutes + seconds
        if ref in ["S", "W"]:
            decimal = -decimal
        return decimal
    except Exception:
        return None


def extract_gps(exif_data: dict):
    """
    Tenta extrair latitude e longitude do EXIF.
    Retorna (lat, lon) ou (None, None).
    """
    if "GPSInfo" not in exif_data:
        return None, None

    gps_info = {}
    for key, value in exif_data["GPSInfo"].items():
        name = GPSTAGS.get(key, key)
        gps_info[name] = value

    try:
        lat = get_decimal_coordinates(
            gps_info.get("GPSLatitude"),
            gps_info.get("GPSLatitudeRef")
        )
        lon = get_decimal_coordinates(
            gps_info.get("GPSLongitude"),
            gps_info.get("GPSLongitudeRef")
        )
        return lat, lon
    except Exception:
        return None, None


def show_verdict(exif_data: dict, lat, lon):
    """Veredito automático com base nos metadados encontrados."""
    if not exif_data:
        st.warning(
            "🧹 **Esta foto NÃO tem metadados.** "
            "Pode ser print, imagem baixada do WhatsApp "
            "ou uma foto editada/salva de novo."
        )
    elif lat is not None and lon is not None:
        st.error(
            "🚨 **PERIGO!** Esta foto é original e revela "
            "sua **localização exata**!"
        )
    else:
        st.success("✅ Foto com metadados básicos, mas **sem GPS**.")


def show_metadata(exif_data: dict, lat, lon):
    """Mostra os metadados principais em cartões."""
    with st.container(border=True):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**📱 Aparelho**")
            st.write(f"Fabricante: `{exif_data.get('Make', '—')}`")
            st.write(f"Modelo: `{exif_data.get('Model', '—')}`")

        with col2:
            st.markdown("**📅 Data e Hora**")
            st.write(f"`{exif_data.get('DateTimeOriginal', exif_data.get('DateTime', '—'))}`")

    with st.container(border=True):
        st.markdown("**📍 Localização (GPS)**")
        if lat is not None and lon is not None:
            st.success(f"Latitude: `{lat:.6f}`  |  Longitude: `{lon:.6f}`")

            # Mapa
            df = pd.DataFrame({"lat": [lat], "lon": [lon]})
            st.map(df, zoom=14, width="stretch", height=300)
        else:
            st.info("Esta foto **não contém** coordenadas GPS.")


# ============================================================
# INTERFACE PRINCIPAL
# ============================================================

# Cabeçalho com logos institucionais
col_cgi, col_titulo, col_dpt = st.columns([1, 4, 1], vertical_alignment="center")
with col_cgi:
    st.image("art/cgi.png", width=90)
with col_titulo:
    st.markdown(
        "<h1 style='text-align:center; margin:0 0 .2rem 0;'>📸 O que sua foto revela?</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center; margin:0;'>Demonstração de Segurança Operacional</p>",
        unsafe_allow_html=True,
    )
with col_dpt:
    st.image("art/dpt.png", width=90)

st.info(
    "🔒 **Privacidade:** Tudo acontece só na sua sessão. "
    "Quando você fecha esta página, os dados desaparecem. "
    "Nada é salvo em nenhum lugar."
)

st.divider()

# ------------------------------------------------------------
# UPLOAD ÚNICO — testa uma foto por vez
# ------------------------------------------------------------
# Contador usado para "reiniciar" o uploader: cada reset cria uma
# nova key, então o campo volta vazio (padrão recomendado pelo Streamlit).
if "reset_count" not in st.session_state:
    st.session_state["reset_count"] = 0

foto = st.file_uploader(
    "Arraste uma foto ou clique para escolher",
    type=["jpg", "jpeg", "png", "webp"],
    key=f"foto_{st.session_state['reset_count']}",
    help="Teste: foto original da câmera, print, foto baixada do WhatsApp… compare os resultados!",
)

if foto:
    image = Image.open(foto)

    # Imagem com nome e tamanho do arquivo
    st.image(
        image,
        caption=f"📄 `{foto.name}` • {foto.size / 1024:.0f} KB",
        width="stretch",
    )

    # Botão para limpar e testar outra
    if st.button("🔄 Limpar e testar outra foto", width="stretch"):
        st.session_state["reset_count"] += 1
        st.rerun()

    exif = get_exif_data(image)
    lat, lon = extract_gps(exif)

    st.markdown("### 🔍 O que esta foto revela:")
    show_verdict(exif, lat, lon)
    show_metadata(exif, lat, lon)

    with st.expander("Ver todos os metadados brutos"):
        if exif:
            st.json({k: str(v) for k, v in exif.items()})
        else:
            st.info("Nenhum metadado EXIF encontrado neste arquivo.")

