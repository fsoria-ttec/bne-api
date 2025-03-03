import sqlite3
from flask import g, current_app
from uuid import uuid4
import datetime as dt
from functools import reduce
import msgspec
from typing import Optional
import re
from multiprocessing import Process
import os
import platform
import shutil
import subprocess
import zipfile
from secrets import token_hex

structs = {}

class QMO:
    def __init__(self,dataset:str,  args:dict=None):
        self.dataset = dataset
        self.args = args

    @staticmethod
    def get_db(file:str=None):
        db = getattr(g, '_database', None)
        if db is None:
            db = g._database = sqlite3.connect(current_app.config.get("DB_FILE") if not file else file)
        return db

    @property
    def con(self, file:str=None):
        return self.get_db(file)
    
    @property
    def cur(self):
        return self.con.cursor()
    
    @property
    def available_fields(self) -> list:
        '''
        Todos los campos disponibles del dataset (marc21 + humans)
        '''
        dataset_name = self.dataset.replace("'", "''")  # Escapar las comillas simples
        return [row[1] for row in self.cur.execute(f"pragma table_info('{dataset_name}');")]
                
    @property
    def marc_fields(self) -> str:
        '''
        Todos los campos marc21 del dataset 
        '''
        return [field[1] for field in self.cur.execute(f"pragma table_info({self.dataset});") if field[1].startswith("t_")]

    @property
    def human_fields(self) -> str:
        '''
        Todos los campos humans del dataset
        '''
        return [field[1] for field in self.cur.execute(f"pragma table_info({self.dataset});") if not field[1].startswith("t_")]

    def create_struct(self, fields: list):
        '''
        struct generado por el dataset con el que se esté trabajando en definitiva es la conversión dict -> JSON (Object de JS)
        '''
        import re
        
        class_name = re.sub(r'[^a-zA-Z0-9_]', '', self.dataset.capitalize())
        
        # Si el nombre no comienza con una letra o está vacío, agregar un prefijo
        if not class_name or not class_name[0].isalpha():
            class_name = 'Dataset' + class_name
        
        to_execute = f'''class {class_name}(msgspec.Struct, omit_defaults=True):\n    '''
        
        if not fields:
            to_execute += "id: Optional[str] = None\n    "
        else:
            for field in fields:
                field_name = re.sub(r'[^a-zA-Z0-9_]', '_', field)
                to_execute += f"{field_name}: Optional[str] = None\n    "
        
        to_execute = to_execute.rstrip()
        if to_execute.endswith(':'):
            to_execute += "\n    pass"
        
        local_namespace = {}
        exec(to_execute, globals(), local_namespace)
        
        created_class = local_namespace[class_name]
        
        structs[self.dataset] = created_class

    @property
    def datasets(self):
        '''
        Todos los datasets disponibles en la aplicación
        '''
        return list(
            map(
                lambda name:name[0],
                filter(
                    lambda name: len(name[0]) == 3, self.cur.execute("select name from sqlite_master where type='table';")
                    )
                )
            )
    
    @property
    def all_fields(self):
        '''
        Método utilizado por la ruta /api/schema para generar los esquemas de cada conjunto
        '''
        '''
        all fields of all tables
        {
            dataset1_human: [],
            dataset1_marc: [],
            dataset1_all: []
            dataset2...
        }
        '''
        result = {}
        for dataset in self.datasets:
            self.dataset = dataset
            result[dataset] = self.available_fields
        return result

    @property
    def purgue(self) -> dict:
        '''
        Método que limpia y maneja el mal uso de la aplicación por parte del cliente
        '''
        result = {}
        error = {"success": False}
        args = self.args.copy()
        dataset_2 = [{dataset:args.pop(dataset)} for dataset in self.datasets if dataset in args.keys()] # Ésto es utilizado cuando el usuario hace una joining query entre por ejemplo, per y mon
        fields = args.pop("fields", None) # Los campos que quiere ver el cliente, ejemplo fields=id,nombre_de_persona
        limit = args.pop("limit", "1000") # El usuario no puede especificar límite, pero si es que se quiere aumentar por parte del desarrollador, se puede hacer desde aquí
        order_by = args.pop("order_by", None) # SQL ORDER BY (asc default, desc optional)
        view = args.pop("view", False) # Campos a mostrar, por defecto todos, y sino view=marc o view=human
        result["is_from_web"] = args.pop("is_from_web", False) # Si la consulta fue generada desde las rutas de web (cajitas - wikidata style) o en formato RESTful API
        filters = args.items() # Todos los filtros del usuario, ejemplo nombre_de_persona=Vito Genovese
        rowid = args.pop("rowid", None)
        count = args.pop("count", False) # Método de contaje de registros en la API. Se fija al final de la query &count=1 para obtener los valores.
        
        if rowid:
            try:
                k, s = map(int, rowid.split("-"))
                result["rowid"] = {"k": k, "s": s}
            except ValueError:
                error["message"] = "rowid debe ser un rango de dos valores separados por '-' (ej. 1-10)"
                return error
            
        if count:
            try:
                int(count)
            except ValueError:
                error['message'] = "Count necesita ser un número entero. Por defecto es False = 0 y True = 1"
                return error
            result['count'] = count


        if limit:
            try:
                int(limit)
            except ValueError:
                error["message"] = f"limit debe ser un número entero"
                return error
        result["limit"] = limit

        if order_by:
            order_key = order_by.split(",")[0]
            if order_key not in self.available_fields: # Es necesario verificar si el usuario está filtrando por un campo existente
                result["message"] = f"No se puede ordenar por {order_key} en {self.dataset}"
                return error
            try:
                order_direction:str = order_by.split(",")[1].strip()
                if order_direction not in ("asc", "desc"):
                    error["message"] = f"Orden ascendente: asc - Orden descendente: desc"
                    return error
            except Exception:
                pass
        result["order_by"] = order_by

        for field in fields.split(",") if fields else ():
            fields = fields.replace(field, field.strip())
            field:str = field.strip()
            if field not in self.available_fields:
                error["message"] = f"El campo no existe en la base de datos: {field} - campos disponibles: {self.available_fields}"
                return error        
       
        not_available_filter = next(filter(lambda kv: kv[0] not in self.available_fields, filters), None) # Se verifica que los filtros indicados sean campos existentes en la DB
        if not_available_filter:
            error["message"] = f"El filtro {not_available_filter[0]}, no es un campo disponible - campos disponibles: {self.available_fields}"
            return error
        result["filters"] = dict(filters)
        
        if view:
            if view == "marc":
                fields = reduce(lambda x,y:f"{x},{y}", self.marc_fields)

            elif view == "human":
                fields = reduce(lambda x,y:f"{x},{y}", self.human_fields)
        result["fields"] = fields if fields else None # campos a consultar en la DB todos, marc21, humans o custom

        try:
            result["dataset_2"] = dataset_2[0] # Se verifica si hay un segundo dataset a consultar para realizar una consulta cruzada
        except:
            pass

        result["success"] = True
        return result
    
    def where(self, args: dict, dataset:str = None) -> str:
        '''Creación de la clausula WHERE de la consulta SQL'''
        args = dict(args)
        dataset = dataset if dataset else self.dataset # Comprobación por si se están consultado dos datasets
        if not args:
            return ""
        result = f"WHERE "
        and_or = " AND " 
        for k,value in args.items():
            v = value.strip()
            # v:str = v.replace("!","")
            v:str = v.replace("|","") 
            v = re.sub("[^\w !-]", " ", v) # Los caracters especiales generan error en el módulo FTS5
            if v.endswith("OR"):
                v = v.replace("OR", "")
                and_or = " OR  "
            if v.find("null") >= 0:
                v_where = f'''{dataset}.{k} IS NULL{and_or}'''
                if v.find("!") >= 0:
                    v_where = v_where.replace("IS NULL", "IS NOT NULL")
            elif v.startswith('"') and v.endswith('"'):
                v_where = f'''{dataset}.{k} MATCH '{v}'{and_or}'''
            elif k == "siglo" or k == "decada":
                v_where = f'''{dataset}.{k} MATCH '{v}'{and_or}'''
            elif v.find("<") >= 0: # Evitar que el operador de comparación < caiga dentro del filtro ya que no es válido en la sintaxis
                v = v.replace("<", "")
                v_where = f'''{k} >= '{v}' {and_or}'''
            elif v.find(">") >= 0:
                v = v.replace(">", "")
                v_where = f'''{k} <= '{v}' {and_or}'''
            elif re.search("\d{4}\-\d{4}", v): # trabajo con dígitos y más especificamente con años de las fechas como fecha_de_nacimiento
                s, e = v.split("-")
                v_where = f'''{k} BETWEEN '{s}' AND '{e}' {and_or}'''
            else:
                v_where = f'''{dataset}.{k} MATCH '{v}*'{and_or}'''


            result += v_where
        return result[:-5] # Debe ser quitado el último operador AND o OR

    def joining(self) -> str:
        '''
        Método a utlizar cuando se consultan más de un conjunto a la vez
        La forma de hacer ésto no es mediante un INNER JOIN común, sino, realizado dos consultas simples, donde se extraen las FOREIGN KEYS del dataset 2 para utilizarlos como filtro en el dataset 1
        '''
        '''WHERE id XX OR XX OR XX...'''
        dataset_2 = self.purgue["dataset_2"]
        d_2 = list(dataset_2.keys())[0].strip()
        filters = {}
        for kv in dataset_2[d_2].split(","): # Filtros del dataset 2 
            k,v = kv.split(":")
            filters[k] = v
        query_2 = f"SELECT id FROM {d_2} "
        d_2_where = self.where(filters, d_2)
        query_2 += d_2_where
        d_2_ids = map(lambda r_id: f"{r_id[0]} OR ", self.cur.execute(query_2))
        ids = ""
        for i,r_id in enumerate(d_2_ids):
            if i == 10000:
                break
            ids += r_id
        ids = ids[:-4]
        return f"WHERE {d_2}_id MATCH '{ids}'"
   
       
    def query(self, count=False, limit=True) -> str:
        '''Unificación de los métodos purge, joining, where'''
        fields = self.purgue.get("fields")
        order_by = self.purgue.get("order_by")
        filters = self.purgue.get("filters")
        dataset_2 = self.purgue.get("dataset_2")
        rowid = self.purgue.get("rowid")
        count = self.purgue.get("count")

        if count and not dataset_2:
            query = f"SELECT count(*) FROM {self.dataset} "
        else:
            if fields:
                query = f"SELECT {fields} FROM {self.dataset} "
            else:
                query = f"SELECT * FROM {self.dataset} "

        if dataset_2:
            where_ids = self.joining()
            query += where_ids
            d_1_where = self.where(filters.items())
            if d_1_where:
                d_1_where = d_1_where.replace("WHERE", "")
                query += f" AND ({d_1_where})"
        else:
            query += self.where(filters.items())

        if order_by:
            if order_by.find(",") >= 0:
                order_by = order_by.replace(",", " ")
            query += f" ORDER BY {order_by} "

        if rowid:
            # Método para definir un rango de líneas en la query cuando LIMIT no sea definido
            k = rowid["k"] # Cantidad de líneas solicitadas
            s = rowid["s"] # Punto de partida de la solicitud
            query = query.rstrip(";")
            query += f" LIMIT {k} OFFSET {s};"
        else:
            # Cuando no si define ROWID la query es limitada a 1000 registros
            if limit:
                return query + " LIMIT 1000;"
        
        return query
    
                 
    def get_estimated(self) -> None:
        '''Método para consultar cuántos resultados la consulta entregará con un timeout de 1.5 segundos (en desuso)'''
        def auxiliar():
            try:
                with open("length.txt", "w") as file:
                    file.write(f"")
                length = tuple(self.cur.execute(self.query(count=True)))[0][0]
                with open("length.txt", "w") as file:
                    file.write(f"{length}")
            except Exception:
                pass
        try:
            p = Process(target=auxiliar)
            p.start()
            p.join(1.5)
            if p.is_alive():
                p.terminate()
        except:
            pass
    
    def json(self) -> dict:
        '''Método que genera el JSON en base a lo que query haya entregado'''
        res_json = self.purgue
        if not res_json["success"]: # False sólo cuando el usuario haga mal uso de la aplicación. True puede suceder por más que la consulta no entregue resultados
            return {"success":False,"message":res_json["message"]}
        
        if res_json["fields"]: # Se crea un modelo en base a cada campo extraido del dataset (si fields=id, sólo se generará id)
            self.create_struct(res_json["fields"].split(","))
        else:
            self.create_struct(self.available_fields)

        query = self.query()   
        print(query)
                    
        '''
        saving query:
        '''
        if self.dataset != "queries": # Comprobar que se guarde la consulta a un conjunto y no a queries en sí
            self.enter(query, error=True, date=dt.datetime.now(), dataset=self.dataset, is_from_web=True if res_json.get("is_from_web") else False) # Se guarda la consulta en la db queries

        try:
            if self.dataset == "queries":
                con = sqlite3.connect("instance/users.db")
                res = con.execute(query)
            else:
                res = self.cur.execute(query)

        except sqlite3.OperationalError as e:
            res = {}
            res["success"] = False
            res["message"] = "SQLite3 Operational Error"
            res["error"] = f"{e}"
            if res["error"] == 'fts5: syntax error near ""':
                res["message"] += ": La búsqueda no ha entregado resultados en el dataset 1"
            return res
        
        result = {}
        result["success"] = True
        result["data"] = map(lambda row:structs[self.dataset](*row),res) # generar un _generator_ para luego utilizar el método msgspec en route en pos de aumentar el rendimiento de la aplicación
        result["query"] = query
        return result
    
    def export_csv(self) -> None:
        '''Exporta los resultados a un archivo CSV de manera compatible con Windows y Linux'''
        file_name = self.dataset + "_" + token_hex(2)
        csv_file = f"{file_name}.csv"
        zip_file = f"{file_name}.zip"
        
        # Eliminar archivos anteriores si existen
        self._remove_previous_files(self.dataset)
        
        # Generar la consulta SQL sin comillas
        query = self.query(limit=False)
        query = query.replace('"', "")
        
        # Usar sqlite3 de manera multiplataforma
        db_path = os.path.join("instance", "bne.db")
        
        # Ejecutar sqlite3 como proceso independiente
        if platform.system() == "Windows":
            cmd = ["sqlite3", db_path, "-header", "-csv", "-separator", ";", query]
        else:
            cmd = ["sqlite3", db_path, "-header", "-csv", "-separator", ";", query]
        
        with open(csv_file, 'w') as f:
            try:
                subprocess.run(cmd, stdout=f, check=True)
            except subprocess.CalledProcessError:
                # Alternativa: usar Python directamente en lugar de sqlite3 CLI
                self._export_csv_python(csv_file, query)
        
        # Comprimir usando zipfile en lugar del comando zip
        with zipfile.ZipFile(zip_file, 'w') as zipf:
            zipf.write(csv_file, arcname=os.path.basename(csv_file))
        
        # Eliminar el archivo CSV original
        if os.path.exists(csv_file):
            os.remove(csv_file)
        
        return file_name
    
    def _export_csv_python(self, csv_file, query):
        '''Método alternativo para exportar a CSV usando Python si sqlite3 CLI falla'''
        import csv
        
        connection = sqlite3.connect(os.path.join("instance", "bne.db"))
        cursor = connection.cursor()
        
        with open(csv_file, 'w', newline='') as f:
            csv_writer = csv.writer(f, delimiter=';')
            
            # Obtener los nombres de las columnas
            if 'SELECT *' in query:
                # Si es SELECT *, necesitamos obtener los nombres de las columnas
                table_name = self.dataset
                cursor.execute(f"PRAGMA table_info({table_name})")
                headers = [info[1] for info in cursor.fetchall()]
            else:
                # Extraer los nombres de columnas de la consulta SELECT
                field_part = query.split("FROM")[0].replace("SELECT", "").strip()
                headers = [field.strip() for field in field_part.split(",")]
            
            csv_writer.writerow(headers)
            
            # Ejecutar la consulta y escribir los resultados
            cursor.execute(query)
            csv_writer.writerows(cursor.fetchall())
        
        connection.close()
    
    def export_json(self) -> None:
        '''Exporta los resultados a un archivo JSON de manera compatible con Windows y Linux'''
        file_name = self.dataset + "_" + token_hex(2)
        json_file = f"{file_name}.json"
        zip_file = f"{file_name}.zip"
        
        # Eliminar archivos anteriores si existen
        self._remove_previous_files(self.dataset)
        
        # Generar la consulta SQL
        query = self.query(count=False, limit=False)
        
        # Usar sqlite3 de manera multiplataforma
        db_path = os.path.join("instance", "bne.db")
        
        # Ejecutar sqlite3 como proceso independiente
        if platform.system() == "Windows":
            cmd = ["sqlite3", db_path, "-json", query]
        else:
            cmd = ["sqlite3", db_path, "-json", query]
        
        with open(json_file, 'w') as f:
            try:
                subprocess.run(cmd, stdout=f, check=True)
            except subprocess.CalledProcessError:
                # Alternativa: usar Python directamente
                self._export_json_python(json_file, query)
        
        # Comprimir usando zipfile
        with zipfile.ZipFile(zip_file, 'w') as zipf:
            zipf.write(json_file, arcname=os.path.basename(json_file))
        
        # Eliminar el archivo JSON original
        if os.path.exists(json_file):
            os.remove(json_file)
        
        return file_name
    
    def _export_json_python(self, json_file, query):
        '''Método alternativo para exportar a JSON usando Python si sqlite3 CLI falla'''
        import json
        
        connection = sqlite3.connect(os.path.join("instance", "bne.db"))
        connection.row_factory = sqlite3.Row  # Para obtener resultados como diccionarios
        cursor = connection.cursor()
        
        cursor.execute(query)
        results = [dict(row) for row in cursor.fetchall()]
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        connection.close()
    
    def _remove_previous_files(self, prefix):
        '''Elimina archivos anteriores con el mismo prefijo de manera compatible'''
        for file in os.listdir('.'):
            if file.startswith(prefix) and (file.endswith('.zip') or file.endswith('.csv') or file.endswith('.json')):
                try:
                    os.remove(file)
                except (PermissionError, OSError):
                    pass  # Ignorar errores si el archivo está en uso o no se puede eliminar    
    def enter(self, query:str, length:int=None, date:str=None, dataset:str=None, time:float=None,is_from_web:bool=False ,error:bool=None, update:bool=False):
        # g._database = None
        # con = self.get_db("instance/users.db")
        '''método para guardar la query en queries'''
        try:
            self.cur.execute("ATTACH 'instance/users.db' as queries;")
            query = query[:2000]
        except Exception as e:
            pass
        if update:
            last_id = tuple(self.cur.execute("SELECT id FROM queries.queries ORDER BY date DESC LIMIT 1;"))[0][0]
            query_str = f'''
                        UPDATE queries.queries SET length = ?, date=?, dataset=?, time=?, is_from_web=?, error=0 WHERE id = '{last_id}';
                        '''
            self.cur.execute(query_str, (length, date, dataset, time, True if is_from_web else False))
            self.con.commit()
            
        else:
            if is_from_web:
                error = False
            query_str = f'''
                    INSERT INTO queries.queries VALUES(
                    '{uuid4().hex}',
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                    )
                    '''
            self.cur.execute(query_str, (query, length, date, dataset, time,is_from_web ,error))
            self.con.commit()
        
if __name__ == "__main__":
    def get_db(file:str=None):
        return sqlite3.connect(current_app.config.get("DB_FILE") if not file else file)
