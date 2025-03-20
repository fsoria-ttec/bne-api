from flask import Blueprint, request, render_template
from db import QMO
import json
import msgspec

consulta = Blueprint("consulta", __name__)
web_consulta = Blueprint("web_consulta", __name__)

def process_consulta_request(hide_elements=True):
    qmo_1 = QMO("geo", {})
    fields = json.dumps(qmo_1.all_fields)
    if request.args:
        # Obtener parámetros de paginación pero mantenerlos separados
        page = int(request.args.get('page', 1))
        page_size = 10  # Registros por página
        
        # Crear una copia de args para la consulta, excluyendo parámetros de paginación
        query_args = dict(request.args)
        if 'page' in query_args:
            query_args.pop('page')
            
        query_args["is_from_web"] = True
        dataset = query_args.pop("dataset")
        qmo_1 = QMO(dataset, query_args)
        data = qmo_1.json()
        
        if data["success"]:
            data["data"] = tuple(data["data"])
            # Guardar el número total de registros
            total_records = len(data["data"])
            data["total_records"] = total_records
            
            # Calcular páginas
            total_pages = (total_records + page_size - 1) // page_size
            data["current_page"] = page
            data["total_pages"] = total_pages
            data["page_size"] = page_size
            
            # Aplicar paginación a los datos
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            
            data = msgspec.json.encode(data)
            data = json.loads(data)
            data["data"] = data["data"][start_index:end_index]
            
        return render_template("consulta/index.html", fields=fields, data=json.dumps(data), hide_elements=hide_elements)
    return render_template("consulta/index.html", fields=fields, hide_elements=hide_elements)

@consulta.route("/")
def t_consulta():
    return process_consulta_request(hide_elements=True)

@web_consulta.route("/")
def t_consulta_web():
    return process_consulta_request(hide_elements=False)
