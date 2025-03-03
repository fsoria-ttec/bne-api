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
        args = dict(request.args)
        args["is_from_web"] = True
        dataset = args.pop("dataset")
        qmo_1 = QMO(dataset, args)
        data = qmo_1.json()
        if data["success"]:
            data["data"] = tuple(data["data"])
            data = msgspec.json.encode(data)
            data = json.loads(data)
            data["data"] = data["data"][:10]
        return render_template("consulta/index.html", fields=fields, data=json.dumps(data), hide_elements=hide_elements)
    return render_template("consulta/index.html", fields=fields, hide_elements=hide_elements)

@consulta.route("/")
def t_consulta():
    return process_consulta_request(hide_elements=True)

@web_consulta.route("/")
def t_consulta_web():
    return process_consulta_request(hide_elements=False)
