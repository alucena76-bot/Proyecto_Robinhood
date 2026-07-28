import gspread
from oauth2client.service_account import ServiceAccountCredentials
import robin_stocks.robinhood as r
import yfinance as yf
import pandas as pd
from datetime import datetime

# =====================================================================
# 1. CONFIGURACIÓN DE CREDENCIALES
# =====================================================================
# REMPLAZA AQUÍ: Pon tu correo y contraseña reales de Robinhood entre las comillas
USUARIO_ROBINHOOD = "alucena76@gmail.com"
PASSWORD_ROBINHOOD = "Mi980817guel$"

# Nombre exacto del archivo de Google Docs/Sheets que creamos
NOMBRE_HOJA = "https://docs.google.com/spreadsheets/d/1NteP0ahr89f9ZsJrA1hqaczQFcSEO9wVz0gC9fJl9d4/edit?gid=0#gid=0"

print("Iniciando sesión en Robinhood...")
# Autenticarse en Robinhood (Te pedirá el SMS en la terminal la primera vez)
r.login(username=USUARIO_ROBINHOOD, password=PASSWORD_ROBINHOOD, expiresIn=86400)

print("Conectando con Google Sheets...")
# Conectarse a Google Sheets usando el archivo JSON
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales_google.json", scope)
client = gspread.authorize(creds)

try:
    sheet = client.open_by_url(NOMBRE_HOJA).sheet1
except Exception as e:
    print(f"Error al abrir la hoja. Asegúrate de haber compartido la hoja con el correo de la cuenta de servicio. Error: {e}")
    exit()

# =====================================================================
# 2. OBTENER ACTIVOS DEL PORTAFOLIO
# =====================================================================
print("Extrayendo activos de tu portafolio...")
my_stocks = r.build_holdings()
tickers = list(my_stocks.keys()) 

if not tickers:
    print("No se encontraron activos abiertos en tu cuenta de Robinhood.")
    exit()

print(f"Activos detectados: {tickers}")
filas_actualizacion = []

# =====================================================================
# 3. EXTRACCIÓN DE SECTOR, PESO Y CÁLCULO TÉCNICO
# =====================================================================
for ticker in tickers:
    print(f"Analizando {ticker}...")
    
    # 1. Extraer el porcentaje de peso en el portafolio directo de Robinhood
    peso_portafolio = float(my_stocks[ticker].get('percentage', 0))
    
    # 2. Extraer Sector e Industria de Yahoo Finance
    try:
        info_accion = yf.Ticker(ticker).info
        sector = info_accion.get('sector', 'Desconocido')
        industria = info_accion.get('industry', 'Desconocida')
    except Exception:
        sector = "Error"
        industria = "Error"

# =====================================================================
# 3. EXTRACCIÓN DE SECTOR, PESO Y CÁLCULO TÉCNICO
# =====================================================================
# Diccionario para forzar la clasificación de ETFs o activos "Desconocidos"
CORRECCIONES_ETFS = {
    "QQQ": {"sector": "Technology", "industry": "Technology - ETF"},
    "SOXX": {"sector": "Technology", "industry": "Semiconductors - ETF"},
    "VOO": {"sector": "Financial Services", "industry": "S&P 500 - ETF"}
    # Puedes agregar cualquier otro ticker rebelde aquí siguiendo el mismo formato
}

for ticker in tickers:
    print(f"Analizando {ticker}...")
    
    # 1. Extraer el porcentaje de peso en el portafolio
    peso_portafolio = float(my_stocks[ticker].get('percentage', 0))
    
    # 2. Extraer Sector e Industria (Revisando primero nuestro diccionario)
    if ticker in CORRECCIONES_ETFS:
        sector = CORRECCIONES_ETFS[ticker]["sector"]
        industria = CORRECCIONES_ETFS[ticker]["industry"]
    else:
        try:
            info_accion = yf.Ticker(ticker).info
            # Buscamos 'sector', si no existe buscamos 'category' (común en algunos ETFs)
            sector = info_accion.get('sector', info_accion.get('category', 'Desconocido'))
            industria = info_accion.get('industry', info_accion.get('quoteType', 'Desconocida'))
        except Exception:
            sector = "Error"
            industria = "Error"

    # 3. Descargar datos para cálculo de pivotes
    data = yf.download(ticker, period="5d", interval="1d", progress=False, group_by="ticker")
    
    if not data.empty:
        if isinstance(data.columns, pd.MultiIndex):
            df_ticker = data[ticker]
        else:
            df_ticker = data
            
        high = float(df_ticker['High'].max())
        low = float(df_ticker['Low'].min())
        close = float(df_ticker['Close'].iloc[-1])
        
        precio_actual_raw = r.get_latest_price(ticker)[0]
        precio_actual = float(precio_actual_raw) if precio_actual_raw else close
        
        # Fórmulas de Puntos Pivote
        pivot = (high + low + close) / 3
        r1 = (2 * pivot) - low
        s1 = (2 * pivot) - high
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        
        filas_actualizacion.append([
            ticker, 
            sector,
            industria,
            round(peso_portafolio, 2),
            round(precio_actual, 2),
            round(s2, 2), 
            round(s1, 2), 
            round(pivot, 2), 
            round(r1, 2), 
            round(r2, 2),
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ])

# =====================================================================
# 4. ACTUALIZAR GOOGLE SHEETS
# =====================================================================
print("Escribiendo datos en Google Sheets...")

sheet.clear()

# Definir e insertar las nuevas etiquetas (Labels) incluyendo Sector, Industria y Peso
etiquetas = [
    "Ticker", "Sector", "Industria", "Peso (%)", "Precio Actual", 
    "Soporte 2 (S2)", "Soporte 1 (S1)", "Pivote Central", 
    "Resistencia 1 (R1)", "Resistencia 2 (R2)", "Última Actualización"
]
sheet.append_row(etiquetas)

for fila in filas_actualizacion:
    sheet.append_row(fila)

print("¡Proceso completado! Tu matriz de riesgo sectorial ha sido actualizada.")