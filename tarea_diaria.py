import os
import json
import shutil
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
import yagmail
from openai import OpenAI
from databueno import generar_datos_salud, generar_grafica, generar_grafico_comparativo
import matplotlib
import glob

matplotlib.use('Agg')

def ejecutar_tarea():
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(asctime)s - %(message)s',
        handlers=[
            logging.FileHandler("logs/tarea_diaria.log"),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)

    logger.info("Descargando datos de salud...")
    generar_datos_salud()
    logger.info("Datos de salud descargados.")

    fecha_hoy = datetime.now().strftime('%Y%m%d')
    ruta_json = os.path.join("datos_salud", f"datos_{fecha_hoy}.json")
    with open(ruta_json, "r", encoding="utf-8") as f:
        datos = json.load(f)

    # OpenAI
    load_dotenv(dotenv_path="envs/.env")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ASISTENTE = os.getenv("ASISTENTE")
    client = OpenAI(api_key=OPENAI_API_KEY)

    mensaje = f"Datos de salud:\n{json.dumps(datos, indent=2, ensure_ascii=False)}"
    thread = client.beta.threads.create()
    client.beta.threads.messages.create(thread_id=thread.id, role="user", content=mensaje)
    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=ASISTENTE)

    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run_status.status == "completed":
            break
        elif run_status.status == "failed":
            raise Exception(" El asistente falló en responder.")
        time.sleep(1)

    messages = client.beta.threads.messages.list(thread_id=thread.id)
    respuesta = messages.data[0].content[0].text.value

    # Guardar análisis local
    with open(f"datos_salud/analisis_{fecha_hoy}.txt", "w", encoding="utf-8") as out:
        out.write(respuesta)

    logger.info("Generando gráfica diaria...")
    generar_grafica(datos)

    origen = "datos_salud/grafico_salud.png"
    destino = "static/grafico_salud.png"
    if os.path.exists(origen):
        os.makedirs("static", exist_ok=True)
        shutil.copy(origen, destino)
        logger.info("Gráfico diario copiado a /static/")
    else:
        logger.warning("El gráfico diario no se encontró.")

    logger.info("Generando gráfico comparativo...")
    generar_grafico_comparativo()
    logger.info("Gráfico comparativo actualizado.")

    carpeta = os.path.join(os.getcwd(), "datos_salud")
    patron = os.path.join(carpeta, "analisis_*.txt")
    archivos = glob.glob(patron)

    ultimo_archivo = max(archivos, key=os.path.getctime)

    with open(ultimo_archivo, "r", encoding="utf-8") as f:
        contenido = f.read()

   
    parte_texto = contenido.split('{')[0].strip()
    respuesta_parse = parte_texto


    # Enviar correo
    logger.info("Enviando email...")
    yag = yagmail.SMTP(user=os.getenv("EMAIL_USER"), password=os.getenv("EMAIL_PASS"))
    yag.send(
        to=os.getenv("EMAIL_DEST"),
        subject="🩺 Tu informe diario de salud",
        contents=[
            f"Análisis IA:\n\n{respuesta_parse}",
            "Adjunto el gráfico diario. Puedes ver el comparativo en la app web."
        ],
        attachments=[destino]
    )
    logger.info("Informe enviado por correo.")

    

if __name__ == "__main__":
    ejecutar_tarea()