import streamlit as st
import rasterio
import numpy as np
import matplotlib.pyplot as plt
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
from pyproj import Transformer
import io

# Configurar la pàgina web de Streamlit
st.set_page_config(page_title="Perfil Topogràfic Interactiu", layout="wide")

st.title("🗺️ Generador de Perfils Topogràfics sobre Mapa")
st.markdown("Fes servir l'eina de línia del mapa per a traçar un recorregut (clic d'inici i doble clic de final) i generar el perfil.")

# --- RUTA DEL FITXER AL NÚVOL (HUGGING FACE) ---
# S'utilitza el prefix /vsicurl/ per a que rasterio puga llegir el TIF d'internet sense descarregar-lo sencer
nom_fitxer = "/vsicurl/https://huggingface.co/datasets/rafainsa/mapa-espanya/resolve/main/espanya_200m.tif"

# 1. TRADUCTOR DE COORDENADES (De Graus del mapa web a Metres UTM del teu .tif)
traductor = Transformer.from_crs("EPSG:4326", "EPSG:25830", always_xy=True)

# 2. CREACIÓ DEL MAPA INTERACTIU (Centrat a Espanya)
col1, col2 = st.columns([2, 1])

with col1:
    m = folium.Map(location=[40.4167, -3.7037], zoom_start=6)
    Draw(
        export=False,
        draw_options={
            'polyline': True,
            'rectangle': False,
            'polygon': False,
            'circle': False,
            'marker': False,
            'circlemarker': False
        }
    ).add_to(m)
    
    dades_mapa = st_folium(m, width=700, height=450)

with col2:
    st.subheader("📋 Instruccions")
    st.write("1. Clica sobre la icona de la **línia trencada** a la vora del mapa.")
    st.write("2. Fes un **clic on vols començar** el perfil.")
    st.write("3. Fes **doble clic on vols acabar** el perfil.")
    st.write("4. Utilitza el botó de baix per a descarregar la imatge en PNG.")

# 3. CAPTURAR EL TRAÇAT I GENERAR EL PERFIL LLEGINT DEL NÚVOL
if dades_mapa and dades_mapa.get("last_active_drawing") and dades_mapa["last_active_drawing"]["geometry"]["type"] == "LineString":
    punts_graus = dades_mapa["last_active_drawing"]["geometry"]["coordinates"]
    
    if len(punts_graus) >= 2:
        p_inici_graus = punts_graus[0]
        p_final_graus = punts_graus[-1]
        
        x1, y1 = traductor.transform(p_inici_graus[0], p_inici_graus[1])
        x2, y2 = traductor.transform(p_final_graus[0], p_final_graus[1])
        
        with st.spinner("Calculant relleu des del servidor de mapes..."):
            try:
                with rasterio.open(nom_fitxer) as mdt:
                    num_mostres = 500
                    x = np.linspace(x1, x2, num_mostres)
                    y = np.linspace(y1, y2, num_mostres)
                    
                    coords = list(zip(x, y))
                    altures = [val[0] for val in mdt.sample(coords)]
                    
                    dist_m = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                    eix_x_km = np.linspace(0, dist_m / 1000, num_mostres)

                    # --- DIBUIX DEL GRÀFIC ---
                    st.subheader("📊 Perfil Topogràfic Resultant")
                    fig, ax = plt.subplots(figsize=(11, 4.5))
                    
                    ax.plot(eix_x_km, altures, color='#8B4513', lw=2.5, label='Terreny')
                    ax.fill_between(eix_x_km, altures, color='#CD853F', alpha=0.3)
                    
                    ax.set_xlabel("Distància recorreguda (km)", fontsize=10)
                    ax.set_ylabel("Altitud (metres)", fontsize=10)
                    ax.grid(True, linestyle='--', alpha=0.5)
                    ax.axhline(0, color='royalblue', lw=1.2, alpha=0.7, label='Nivell del mar')
                    ax.legend()
                    
                    st.pyplot(fig)
                    st.success(f"Perfil generat! Distància total: {dist_m/1000:.2f} km")
                    
                    # --- BOTÓ DE DESCÀRREGA ---
                    buffer = io.BytesIO()
                    fig.savefig(buffer, format='png', dpi=300)
                    buffer.seek(0)
                    
                    st.download_button(
                        label="📥 Descarregar gràfic en PNG",
                        data=buffer,
                        file_name="perfil_topografic.png",
                        mime="image/png"
                    )
                    
            except Exception as e:
                st.error(f"Error en llegir el fitxer topogràfic des del núvol: {e}")