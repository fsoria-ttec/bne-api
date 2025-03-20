from flask import Blueprint,  request, render_template, Response, g, send_file
from db import QMO
import time
import os
import datetime as dt
import cProfile
import pstats
import msgspec
from fields import fields
from views.api.utils import write_error
from re import sub

api = Blueprint("api", __name__)

@api.route("/")
def r_home():
    '''
    Ésta ruta se encarga de convertir el md a formato HTML haciendo uso de la librería markdown
    El README contiene los siguientes puntos:
    1. Explicación de uso
    2. Tutorial
    3. Ejemplos de consulta
    '''
    import markdown as md
    with open("README.md", encoding="utf-8") as file:
        md = md.markdown(file.read(), extensions=["fenced_code", "codehilite"])
        file.close()
    return render_template("docs.html", md=md)

@api.route("/<model>")
def r_query(model):
    '''
    Ésta es la ruta más compleja del blueprint api
    Hace uso de las siguientes librerías:
    msgspsec: msgspec, permite convertir colecciones de datos tanto ordenadas como asociativas en JSON.
    Hace uso de _structs_ para ofrecer los menores tiempos de respuesta registrado entre otras alternativas como: json, orjson, ujson
    Pensar en los structs como si fueran objetos en Python, por cada modelo existente en la DB (per, ent, geo...), crea un modelo que permite hacer la conversión velozmente

    El resto del código es un conjunto de pasos secuenciales lógicos:
    1. Recibir los argumentos del cliente
    2. Consultar la db con esos argumentos
    3. Entrejar un fichero csv, json, txt, xml o ods si el cliente lo ha solicitado o sino
    4. Entregar un JSON limitado siempre a 1000 resultados
    '''
    model = sub("\.csv|\.json|\.txt|\.xml|\.ods", "", model)
    args = {}
    for k,arg in request.args.items():
        args[k] = sub("\.csv|\.json|\.txt|\.xml|\.ods", "", arg)
    file_extension = request.url.rsplit(".", 1)[-1]
    # with cProfile.Profile() as pr: # http://localhost:3000/api/per?t_375=masculino&limit=1000000 # código comentado  que sirve para evaluar el rendimiento de la respuesta
    qmo_1 = QMO(model, args)
    if model not in qmo_1.datasets + ["queries"]:
        return render_template("errors/404.html", message=f"{model} no es un conjunto de datos existente")
    
    data = qmo_1.json() # Éste método está explicado en db.py
   # Modificar solo la parte de manejo de archivos en r_query
    if file_extension in ("csv", "json", "txt", "xml", "ods"):
        if not data["success"]:
            return {"success": False, "message": f"No se ha podido generar el {file_extension}", "error": data["message"]}
        
        export_functions = {
            "csv": qmo_1.export_csv,
            "json": qmo_1.export_json,
            "txt": qmo_1.export_txt,
            "xml": qmo_1.export_xml,
            "ods": qmo_1.export_ods
        }
        
        mime_types = {
            "csv": "application/zip",
            "json": "application/zip",
            "txt": "application/zip",
            "xml": "application/zip",
            "ods": "application/zip"
        }
        
        try:
            file_name = export_functions[file_extension]()
            zip_path = f"{file_name}.zip"
            
            # Verificar que el archivo existe y tiene contenido
            if not os.path.exists(zip_path) or os.path.getsize(zip_path) == 0:
                write_error(450, f"Archivo zip vacío o inexistente: {zip_path}", f"Empty zip for {file_extension}")
                return {"success": False, "message": f"Error al generar el archivo {file_extension}"}
            
            # Entregar el archivo
            response = send_file(
                zip_path, 
                mimetype=mime_types[file_extension],
                as_attachment=True,
                download_name=f"{model}_{dt.datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
            )
            
            # Establecer cabeceras para evitar almacenamiento en caché
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            
            return response
        except Exception as e:
            write_error(460, f"{e}", f"Couldn't deliver {file_extension}")
            return {"success": False, "message": f"No se ha podido generar el {file_extension}: {str(e)}"}
    
    # Para respuestas JSON normales
    print(f"{request.url}".center(100,"-"))
    if data["success"]:
        data["time"] = time.perf_counter()
        # Convertir el iterable map a lista para que sea serializable
        data["data"] = list(data["data"])
        data["time"] = time.perf_counter() - data["time"]
        if model == "queries":
            data["length"] = len(data["data"]) 
        now = dt.datetime.now()
        try:
            if model != "queries":
                g._database = None
                qmo_1.enter(data["query"], None, now, model, data["time"],request.args.get("is_from_web"), False,True)
        except Exception as e:
            write_error(2,f"{e}", "Couldn't save query")
        data.pop("query")
    
    try:    
        data = msgspec.json.encode(data) # convertir cada diccionario en el iterable a un struct para luego generar el JSON
    except Exception as e:
        write_error(3, f"{e}", "Error ocurred while encoding data using msgspec")
        # Fallback a JSON estándar en caso de error
        import json
        data = json.dumps({"success": False, "message": "Error interno al procesar la respuesta"})
    
    res = Response(response=data, mimetype="application/json", status=200) # application/gzip
    # stats = pstats.Stats(pr) # código comentado  que sirve para evaluar el rendimiento de la respuesta
    # stats.sort_stats(pstats.SortKey.TIME) # código comentado  que sirve para evaluar el rendimiento de la respuesta
    # stats.print_stats(8) # código comentado  que sirve para evaluar el rendimiento de la respuesta
    return res

@api.route("/fields/<model>")
def r_fields(model):
    '''
    Ésta ruta tiene como objetivo indicar los campos o esquema del modelo solicitado.
    '''
    res = {}
    test_QMO = QMO(model)
    view = request.args.get("view")
    if view:
        if view == "human":
            res["fields"] = test_QMO.human_fields
        elif view == "marc":
            res["fields"] = test_QMO.marc_fields
        return res
    res["fields"] = test_QMO.available_fields
    return res

@api.route("/schema")
def t_schema():
    dataset = request.args.get("dataset")
    if dataset:
        if fields.get(dataset):
            return render_template("schema.html", fields=fields[dataset])
    return render_template("schema.html")
        
@api.route("/stats")
def t_stats():
    '''
    Gráficas de uso generadas con js utilizado la librería chart.js
    '''
    return render_template("stats.html")
