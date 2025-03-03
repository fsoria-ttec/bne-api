from flask import Flask, g
import os
from views.api.routes import api
from views.home.routes import home
from views.errors.routes import errors
from views.web.routes import consulta, web_consulta
from flask_cors import CORS
from datetime import timedelta
import json

def create_app():
    app = Flask(__name__)
    app.config.from_file("config.json", load=json.load)
    app.config['PERMANENT_SESSION_LIFETIME'] =  timedelta(minutes=10)
    app.register_blueprint(api, url_prefix="/api")
    app.register_blueprint(errors)
    app.register_blueprint(home)
    app.register_blueprint(consulta, url_prefix="/consulta")
    app.register_blueprint(web_consulta, url_prefix="/web")
    return app


app = create_app()
CORS(app)

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

#if "kuga" in app.root_path or "pi" in app.root_path:
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3000, debug=True)
