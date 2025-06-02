import os
import json
import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import re

def obtener_access_token(CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN):
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
    return None

def obtener_frecuencia_cardiaca(headers, data_source_id):
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    url = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"

    # promedio de las últimas 24h
    body = {
        "aggregateBy": [{
            "dataTypeName": "com.google.heart_rate.bpm",
            "dataSourceId": data_source_id
        }],
        "bucketByTime": { "durationMillis": 3600000 },
        "startTimeMillis": int(yesterday.timestamp() * 1000),
        "endTimeMillis": int(now.timestamp() * 1000)
    }
    resp = requests.post(url, headers=headers, json=body)
    data = resp.json()
    valores = []
    for bucket in data.get("bucket", []):
        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                for value in point.get("value", []):
                    if "fpVal" in value:
                        valores.append(value["fpVal"])
    if valores:
        return sum(valores) / len(valores)
    #últimos 7 días y tomar el último valor
    seven_days_ago = now - timedelta(days=7)
    body["startTimeMillis"] = int(seven_days_ago.timestamp() * 1000)
    resp = requests.post(url, headers=headers, json=body)
    data = resp.json()
    valores = []
    for bucket in data.get("bucket", []):
        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                for value in point.get("value", []):
                    if "fpVal" in value:
                        valores.append(value["fpVal"])
    if valores:
        return valores[-1]
    return 0.0

def obtener_ultimo_valor(headers, data_source_id, dias=90):
    now = datetime.now(timezone.utc)
    inicio = now - timedelta(days=dias)
    start = int(inicio.timestamp() * 1e9)
    end = int(now.timestamp() * 1e9)
    dataset_id = f"{start}-{end}"
    url = f"https://www.googleapis.com/fitness/v1/users/me/dataSources/{data_source_id}/datasets/{dataset_id}"
    resp = requests.get(url, headers=headers)
    data = resp.json()
    valores = []
    fechas = []
    for point in data.get("point", []):
        val = point["value"][0]
        if "fpVal" in val:
            valores.append(val["fpVal"])
        elif "intVal" in val:
            valores.append(val["intVal"])
        fechas.append(int(point.get("endTimeNanos", "0")))
    if valores and fechas:
        indice = fechas.index(max(fechas))
        return valores[indice]
    else:
        return 0.0

def obtener_metricas_del_dia(headers, data_source_id, dataset_id, nombre):
    url = f"https://www.googleapis.com/fitness/v1/users/me/dataSources/{data_source_id}/datasets/{dataset_id}"
    resp = requests.get(url, headers=headers)
    data = resp.json()
    valores = []
    for point in data.get("point", []):
        val = point["value"][0]
        if "fpVal" in val:
            valores.append(val["fpVal"])
        elif "intVal" in val:
            valores.append(val["intVal"])
    if not valores:
        return 0.0
    if nombre == "Calorías":
        return sum(valores) / len(valores)
    else:
        return sum(valores)

def generar_datos_salud():
    load_dotenv(dotenv_path="envs/.env")

    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

    access_token = obtener_access_token(CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)
    if not access_token:
        raise Exception("No se pudo obtener el access token de Google Fit.")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    now = datetime.now(timezone.utc)
    midnight = datetime.combine(now.date(), datetime.min.time(), tzinfo=timezone.utc)
    start = int(midnight.timestamp() * 1e9)
    end = int(now.timestamp() * 1e9)
    dataset_id = f"{start}-{end}"

    data_sources = {
        "Calorías": "derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended",
        "Distancia": "derived:com.google.distance.delta:com.google.android.gms:merge_distance_delta",
        "Minutos Activos": "derived:com.google.active_minutes:com.google.android.gms:merge_active_minutes",
        "Frecuencia Cardiaca": "derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm",
        "Peso": "derived:com.google.weight:com.google.android.gms:merge_weight",
        "Altura": "derived:com.google.height:com.google.android.gms:merge_height"
    }

    resultados = {}
    for nombre, ds_id in data_sources.items():
        if nombre == "Frecuencia Cardiaca":
            valor = obtener_frecuencia_cardiaca(headers, ds_id)
        elif nombre in ["Peso", "Altura"]:
            valor = obtener_ultimo_valor(headers, ds_id)
        else:
            valor = obtener_metricas_del_dia(headers, ds_id, dataset_id, nombre)
        unidad = {
            "Calorías": "kcal",
            "Minutos Activos": "min",
            "Distancia": "m",
            "Altura": "m",
            "Peso": "kg",
            "Frecuencia Cardiaca": "bpm"
        }.get(nombre, "")
        resultados[nombre] = {
            "valor": round(valor, 2),
            "unidad": unidad
        }

    os.makedirs("datos_salud", exist_ok=True)
    fecha_hoy = datetime.now().strftime('%Y%m%d')
    ruta_json = os.path.join("datos_salud", f"datos_{fecha_hoy}.json")
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=4, ensure_ascii=False)

def generar_grafico_comparativo():
    carpeta = "datos_salud"
    archivos = sorted(os.listdir(carpeta))
    fechas = []
    calorias = []
    distancia = []
    minutos = []
    frecuencia = []
    peso = []
    altura = []
    for archivo in archivos:
        match = re.match(r"^datos_(\d{8})\.json$", archivo)
        if not match:
            continue
        fecha_str = match.group(1)
        fecha = datetime.strptime(fecha_str, "%Y%m%d").strftime("%d/%m")
        with open(os.path.join(carpeta, archivo), "r", encoding="utf-8") as f:
            datos = json.load(f)
        fechas.append(fecha)
        calorias.append(datos.get("Calorías", {}).get("valor", 0))
        distancia.append(datos.get("Distancia", {}).get("valor", 0))
        minutos.append(datos.get("Minutos Activos", {}).get("valor", 0))
        frecuencia.append(datos.get("Frecuencia Cardiaca", {}).get("valor", 0))
        peso.append(datos.get("Peso", {}).get("valor", 0))
        altura.append(datos.get("Altura", {}).get("valor", 0))
    plt.figure(figsize=(12, 7))
    plt.plot(fechas, calorias, label="Calorías", marker="o")
    plt.plot(fechas, distancia, label="Distancia", marker="o")
    plt.plot(fechas, minutos, label="Minutos Activos", marker="o")
    plt.plot(fechas, frecuencia, label="Frecuencia Cardíaca", marker="o")
    plt.plot(fechas, peso, label="Peso", marker="o")
    plt.plot(fechas, altura, label="Altura", marker="o")
    plt.title("Progreso Diario de Salud")
    plt.xlabel("Fecha")
    plt.ylabel("Valor")
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    os.makedirs("static", exist_ok=True)
    plt.savefig("static/grafico_salud.png")
    plt.close()

def generar_grafica(resultados):
    etiquetas = list(resultados.keys())
    valores = [resultados[k]["valor"] for k in etiquetas]
    plt.figure(figsize=(10, 6))
    bars = plt.bar(etiquetas, valores, color="mediumpurple")
    plt.title("Informe Diario de Salud")
    plt.ylabel("Valor")
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.5, f'{yval:.1f}', ha='center')
    plt.tight_layout()
    os.makedirs("static", exist_ok=True)
    plt.savefig("static/grafico_salud_diario.png")
    plt.close()
