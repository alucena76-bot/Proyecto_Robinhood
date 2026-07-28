import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. Configuración de la página
st.set_page_config(page_title="Control de Riesgo | Portafolio", layout="wide")

st.title("📊 Panel de Control de Riesgo Sectorial")
st.markdown("Monitor interactivo de sobreexposición de capital.")
st.markdown("---")

# 2. Conexión a Google Sheets (con caché para no agotar la cuota de Google)
@st.cache_data(ttl=600)  
def cargar_datos():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Detecta si está en la nube o en tu computadora local
    if "gcp_service_account" in st.secrets:
        # Modo Nube: Lee las credenciales de los secretos de Streamlit
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        # Modo Local: Lee tu archivo JSON
        creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales_google.json", scope)
        
    client = gspread.authorize(creds)
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1NteP0ahr89f9ZsJrA1hqaczQFcSEO9wVz0gC9fJl9d4/edit").worksheet("Dashboard Riesgo")
    
    datos = sheet.get_all_records()
    return pd.DataFrame(datos)

    # Llamar a la función para descargar los datos y guardarlos en la variable
df_sectores = cargar_datos()
    
# 3. Interfaz Visual
col1, col2 = st.columns([2, 1])
with col1:
        st.subheader("Distribución de Capital")
        fig = px.pie(
            df_sectores, 
            values='Porcentaje', 
            names='Sector', 
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Tealgrn
        )
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("⚠️ Alertas de Exposición")
        limite = st.slider("Límite de riesgo permitido (%)", min_value=10, max_value=50, value=20)
        
        st.write("Estado actual:")
        for index, row in df_sectores.iterrows():
            if row['Porcentaje'] > limite:
                st.error(f"**{row['Sector']}**: {row['Porcentaje']}% (¡Sobreexposición!)")
            else:
                st.success(f"**{row['Sector']}**: {row['Porcentaje']}% (Saludable)")
                
st.markdown("---")
st.caption("Desarrollado para la gestión estructurada de riesgo en mercados de capitales.")
