from flask import Flask, render_template, request
import os, json
from datetime import datetime
from databueno import generar_grafico_comparativo
import re
from tarea_diaria import ejecutar_tarea


app = Flask(__name__)

@app.template_filter('datetimeformat')
def datetimeformat(value):
    return datetime.strptime(value, '%Y%m%d').strftime('%d/%m/%Y')


@app.route("/")
def mostrar_informe():
    fecha_hoy = datetime.now().strftime('%Y%m%d')
    ruta_json = os.path.join("datos_salud", f"datos_{fecha_hoy}.json")
    ruta_analisis = os.path.join("datos_salud", f"analisis_{fecha_hoy}.txt")

    if not os.path.exists(ruta_json):
        return "❌ No hay datos disponibles para hoy.", 404

    with open(ruta_json, "r", encoding="utf-8") as f:
        datos = json.load(f)

    if os.path.exists(ruta_analisis):
        with open(ruta_analisis, "r", encoding="utf-8") as f:
            contenido = f.read()
            partes = contenido.split("```json")[0]  # cortar antes del JSON
            analisis = partes.strip().replace("\n", "<br>")
    else:
        analisis = "(El análisis aún no ha sido generado)"

    return render_template(
    "index.html",
    fecha=datetime.now().strftime('%d/%m/%Y'),
    calorias=f"{datos['Calorías']['valor']} {datos['Calorías']['unidad']}",
    distancia=f"{datos['Distancia']['valor']} {datos['Distancia']['unidad']}",
    minutos=f"{datos['Minutos Activos']['valor']} {datos['Minutos Activos']['unidad']}",
    frecuencia=f"{datos['Frecuencia Cardiaca']['valor']} {datos['Frecuencia Cardiaca']['unidad']}",
    peso=f"{datos['Peso']['valor']} {datos['Peso']['unidad']}",
    altura=f"{datos['Altura']['valor']} {datos['Altura']['unidad']}",
    analisis=analisis
)


import re

@app.route("/historial")
def informes():

    archivos = os.listdir("datos_salud")
    print("🗂️ Archivos en datos_salud:", archivos)

    archivos_validos = []
    for a in archivos:
        match = re.match(r"^datos_(\d{8})\.json$", a)
        if match:
            archivos_validos.append({
                "nombre": a,
                "fecha": match.group(1) 
            })
    mes_filtro = request.args.get("mes")

    if mes_filtro:
        archivos_validos = [a for a in archivos_validos if a["fecha"].startswith(mes_filtro.replace("-", ""))]

    # obtener lista de meses únicos
    meses = sorted({a["fecha"][:6] for a in archivos_validos})

    print("✅ Archivos válidos:", archivos_validos)
    return render_template("historial.html", archivos=archivos_validos)


@app.route("/informe/<fecha>")
def ver_informe(fecha):
    ruta_json = os.path.join("datos_salud", f"datos_{fecha}.json")
    ruta_analisis = os.path.join("datos_salud", f"analisis_{fecha}.txt")

    if not os.path.exists(ruta_json):
        return "❌ No hay datos para esa fecha.", 404

    with open(ruta_json, "r", encoding="utf-8") as f:
        datos = json.load(f)
    if os.path.exists(ruta_analisis):
        with open(ruta_analisis, "r", encoding="utf-8") as f:
            contenido = f.read()
            partes = contenido.split("```json")[0]  # cortar antes del JSON
            analisis = partes.strip().replace("\n", "<br>")
    else:
        analisis = "(Análisis IA no disponible para esta fecha)"


    return render_template(
        "informe.html",
       fecha=datetime.now().strftime('%d/%m/%Y'),
        calorias=f"{datos['Calorías']['valor']} {datos['Calorías']['unidad']}",
        distancia=f"{datos['Distancia']['valor']} {datos['Distancia']['unidad']}",
        minutos=f"{datos['Minutos Activos']['valor']} {datos['Minutos Activos']['unidad']}",
        frecuencia=f"{datos['Frecuencia Cardiaca']['valor']} {datos['Frecuencia Cardiaca']['unidad']}",
        peso=f"{datos['Peso']['valor']} {datos['Peso']['unidad']}",
        altura=f"{datos['Altura']['valor']} {datos['Altura']['unidad']}",
        analisis=analisis
    )

@app.route("/comparativo")
def ver_comparativo():
    generar_grafico_comparativo()  # genera el grafico 'grafico_salud.png'

    archivos = sorted(
        [f for f in os.listdir("datos_salud") if re.match(r"^datos_(\d{8})\.json$", f)],
        reverse=True
    )

    fechas = []
    valores = []
    for archivo in archivos:
        fecha_raw = re.findall(r"\d{8}", archivo)[0]
        with open(os.path.join("datos_salud", archivo), "r", encoding="utf-8") as f:
            datos = json.load(f)
            fechas.append(datetime.strptime(fecha_raw, "%Y%m%d").strftime("%d/%m"))
            valores.append({
                "fecha": fecha_raw,
                "calorias": datos["Calorías"]["valor"],
                "distancia": datos["Distancia"]["valor"],
                "minutos": datos["Minutos Activos"]["valor"]
            })

    # Leer metas de usuario
    ruta_metas = os.path.join("datos_salud", "metas_usuario.json")
    if os.path.exists(ruta_metas):
        with open(ruta_metas, "r", encoding="utf-8") as f:
            metas = json.load(f)
    else:
        metas = {"Calorías": 300, "Distancia": 2000, "Minutos Activos": 30}

    # Ranking de cumplimiento
    ranking = []
    for v in valores:
        cumplidas = 0
        if v["calorias"] >= metas["Calorías"]: cumplidas += 1
        if v["distancia"] >= metas["Distancia"]: cumplidas += 1
        if v["minutos"] >= metas["Minutos Activos"]: cumplidas += 1
        ranking.append({
            "fecha": datetime.strptime(v["fecha"], "%Y%m%d").strftime("%d/%m"),
            "puntos": cumplidas
        })

    ranking.sort(key=lambda x: x["puntos"], reverse=True)

    return render_template("comparativo.html", fechas=fechas, valores=valores, ranking=ranking)


@app.template_filter('format_mes')
def format_mes(value):
    meses = {
        "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
        "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
        "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"
    }
    anio, mes = value.split("-")
    return f"{meses[mes]} {anio}"

@app.route("/consejos")
def consejos():
    import os
    import json
    import re
    from datetime import datetime

    fecha_hoy = datetime.now().strftime('%Y%m%d')
    ruta_analisis = os.path.join("datos_salud", f"analisis_{fecha_hoy}.txt")

    if not os.path.exists(ruta_analisis):
        return "❌ No hay análisis generado aún.", 404

    with open(ruta_analisis, "r", encoding="utf-8") as f:
        contenido = f.read()

    # 🔍 Buscar el primer bloque JSON válido, incluso si no está entre ```json ... ```
    match = re.search(r"(\{[\s\S]+\})", contenido)
    if not match:
        return "❌ No se encontró JSON válido en el análisis.", 400

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return "❌ Error al decodificar el JSON de consejos.", 400

    # 🧩 Unir todos los consejos en una lista de tarjetas
    tarjetas = []
    for categoria in [
        "actividad_fisica", "nutricion", "descanso_y_recuperacion",
        "salud_mental", "hidratacion", "elogios"
    ]:
        tarjetas.extend(data.get(categoria, []))

    return render_template("consejos.html", tarjetas=tarjetas)

   

@app.route("/metas", methods=["GET", "POST"])
def metas():
    ruta_metas = os.path.join("datos_salud", "metas_usuario.json")
    
    # Si el usuario envía nuevas metas desde el formulario
    if request.method == "POST":
        metas_usuario = {
            "Calorías": float(request.form["Calorías"]),
            "Distancia": float(request.form["Distancia"]),
            "Minutos Activos": float(request.form["Minutos Activos"])
        }
        with open(ruta_metas, "w", encoding="utf-8") as f:
            json.dump(metas_usuario, f, indent=2)

    # Cargar metas guardadas
    if os.path.exists(ruta_metas):
        with open(ruta_metas, "r", encoding="utf-8") as f:
            metas_guardadas = json.load(f)
    else:
        metas_guardadas = {"Calorías": 300, "Distancia": 2000, "Minutos Activos": 30}

    # Cargar datos de hoy
    fecha_hoy = datetime.now().strftime('%Y%m%d')
    ruta_datos = os.path.join("datos_salud", f"datos_{fecha_hoy}.json")
    if not os.path.exists(ruta_datos):
        return "❌ No hay datos de salud de hoy.", 404

    with open(ruta_datos, "r", encoding="utf-8") as f:
        datos = json.load(f)

    evaluacion = []
    for categoria in ["Calorías", "Distancia", "Minutos Activos"]:
        valor_real = datos[categoria]["valor"]
        meta = metas_guardadas.get(categoria, 0)
        unidad = datos[categoria]["unidad"]
        cumplida = valor_real >= meta
        evaluacion.append({
            "nombre": categoria,
            "valor_real": valor_real,
            "meta": meta,
            "unidad": unidad,
            "cumplida": cumplida
        })

    return render_template("metas.html", metas=evaluacion, metas_form=metas_guardadas)





if __name__ == "__main__":
    ejecutar_tarea()
    app.run(host="0.0.0.0", port=8080, debug=False)
