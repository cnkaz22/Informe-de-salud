import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone

# Cargar variables de entorno desde envs/.env
load_dotenv(dotenv_path="envs/.env")

# Obtener credenciales del entorno
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

def obtener_access_token():
    """Solicita un nuevo access token usando el refresh token"""
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }
    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print("❌ Error al obtener el token:", response.text)
        return None

def listar_data_sources(token):
    """Lista todos los dataSources disponibles en la cuenta del usuario"""
    url = "https://www.googleapis.com/fitness/v1/users/me/dataSources"
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"❌ Error {resp.status_code}: {resp.text}")
        return

    data = resp.json()
    if not data.get("dataSource"):
        print("⚠️ No se encontraron dataSources.")
        return

    print("✅ Lista de dataSources disponibles:\n")
    for ds in data["dataSource"]:
        print(f"📌 ID: {ds['dataStreamId']}")
        print(f"   🔹 Nombre: {ds.get('dataStreamName', 'Sin nombre')}")
        print(f"   🔹 Tipo: {ds['dataType']['name']}")
        print(f"   🔹 Aplicación: {ds.get('application', {}).get('name', 'Desconocida')}")
        print("-" * 60)

if __name__ == "__main__":
    token = obtener_access_token()
    if token:
        listar_data_sources(token)
