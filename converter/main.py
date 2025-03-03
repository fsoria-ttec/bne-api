from os import listdir
if "dbs" not in listdir("./"):
    import init
from pymarc import MARCReader
import sys
import codecs
import sqlite3
import requests as req
from models import create_statements
from humanizer import *
import concurrent.futures
from constants import *
from utils import ejecutar_comando
from ckan import actualizar_CKAN
from tqdm import tqdm

import warnings
from urllib3.exceptions import InsecureRequestWarning

# Forzar encoding
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

def get_files(urls):
    '''
    Gracias a ésta función podemos descargar todos los conjuntos en paralelo para su posterior procesado e inserción a la DB
    '''
    warnings.filterwarnings("ignore", category=InsecureRequestWarning)

    failed_downloads = []  # Lista para almacenar los ficheros que han fallado. Es más eficiente intentar usar el método yield, buscar sobre.
    with concurrent.futures.ThreadPoolExecutor() as executor:
        def download(url):
            try:
                print(f"Accediendo a {url.split('/')[-1]}")
                res = req.get(url, verify=False, stream=True)
                res.raise_for_status()  # Reporta los errores 
                z_file_name = re.findall(r"/([^/]+)-mrc_new\.mrc", res.url)[0]
                
                # Calculando tamaño del contenido
                total_size = int(res.headers.get('content-length', 0))
                
                with open(f"mrcs/{z_file_name}.mrc", "wb") as z_file:
                    with tqdm(total=total_size, unit='B', unit_scale=True, desc=f"Descargando {z_file_name}") as pbar:
                        for chunk in res.iter_content(chunk_size=1024):
                            z_file.write(chunk)
                            pbar.update(len(chunk))  # Actualiza la barra de progreso
            except Exception as e:
                print(f"Hubo un fallor al descargar el dataset {url}: {e}")
                failed_downloads.append(url)  

        executor.map(download, urls)

    if failed_downloads:
        print("\nAlgunos ficheros no se han podido descargar:")
        for failed_url in failed_downloads:
            print(f"- {failed_url}")
        retry = input("¿Deseas reintentar la descarga de datos? (s/n): ")
        if retry.lower() == 's':
            print("Intentándolo de nuevo...")
            get_files(failed_downloads)

def insertion(datasets):
    for dataset, mrc_file in datasets.items():
        if dataset not in datasets:
            continue
        dataset = dataset[:3] 
        
        # Condición para evitar que se dupliquen los datos
        cur.execute(f"DROP TABLE IF EXISTS {dataset}")
        con.commit()
        
        with open(f"mrcs/{mrc_file}.mrc", "rb") as file:
            reader = MARCReader(file, force_utf8=True)
            cur.execute(create_statements[f"{dataset}"])  # Query de creación de las tablas de models.py
            con.commit()

            mf = marc_fields(dataset)
            
            def insert(data):
                '''Función responsable por insertar los registros MARC21 en la base de datos'''
                counter = create_statements[f"{dataset}"].count("\n") - 3
                query = f'''insert or ignore into {dataset} values ({'?, '*counter})'''
                query = query.replace(", )", ")")
                
                # Parametros del tqdm para la barra de progreso
                data_list = list(data) # Posiblemente sea más eficiente utilizar yield y no una lista. Buscar sobre.
                batch_size = 1000 # Numéro de registros del contador de progreso
                total_records = len(data_list)

                with tqdm(total=len(data_list), desc=f"Insertando datos en el {dataset}", unit=" registros") as pbar:
                    try:
                        for i in range(0, total_records, batch_size):
                            batch = data_list[i:i + batch_size]
                            cur.executemany(query, filter(lambda d: d, batch))  # Inserción de datos en lotes
                            con.commit()
                            pbar.update(len(batch))
                    except ValueError as e:
                        print(f"Error al insertar los datos: {e}")

            def mapper(record):
                '''
                La función que se encarga de 'humanizar' todos los registros
                '''
                if not record:
                    return
                to_extract = {}
                old_t = None
                fields = record.as_dict()["fields"]
                for f in fields:
                    t, v = tuple(f.items())[0]
                    try:
                        subfields = v.get("subfields")
                    except:
                        pass
                    if type(v) == dict and subfields:
                        v = ""
                        for sf in subfields:
                            t_sf, v_sf = tuple(sf.items())[0]
                            v += f"|{t_sf} {v_sf}"
                        to_extract[t] = f'{to_extract[t]} /**/ {v}' if old_t == t else v
                    else:
                        to_extract[t] = f"{to_extract[t]} |a {v}" if old_t == t else f"|a {v}"
                    old_t = t
                return extract_values(dataset, to_extract)

            data = map(lambda a: mapper(a), reader)
            insert(data)


def crearPromptInicio():
        print("1. Todos")
        print("2. Dataset")
        print("3. Crear ficheros")
        print("4. Actualizar CKAN")
        print("Q. Salir")

if __name__ == "__main__":
    user = ""
    while user.lower() != "q":
        if user == "1":
            ejecutar_comando("limpiar")
            print("Se generarán todos los conjuntos de datos\n ¿Estás seguro de que quieres continuar? (Y/N)")
            user = input(": ")
            if user.lower() == "n":
                continue
            try:
                ejecutar_comando("borrar_arc", db_path)    
            except:
                print("Ignorar este mensaje")
            con = sqlite3.connect("dbs/bne.db")
            cur.execute(create_statements["queries"])
            cur = con.cursor()
            get_files(urls)
            insertion(datasets)
            actualizar_CKAN(datasets)
            print("Datos ingresados")
        elif user == "2":
            ejecutar_comando("limpiar")
            for i, dataset in enumerate(datasets.keys()):
                print(f"{i+1}. {dataset}")
            user = int(input(": ")) - 1
            dataset = list(datasets.keys())[user]
            con = sqlite3.connect(db_path)
            cur.execute(create_statements["queries"])
            cur = con.cursor()
            get_files((urls[user],))
            dataset = {dataset: list(datasets.values())[user]}
            insertion(dataset)
            actualizar_CKAN(dataset)
            print("Datos ingresados")
        elif user == "3":
            ejecutar_comando("limpiar")
            if "bne.db" not in listdir("dbs"):
                print("¡La base de datos no ha sido creada!")
                print("Ejecutar la opción 1 de éste programa")
                user = input(": ")
                continue
            import create_files
        elif user == "4":
            ejecutar_comando("limpiar")
            for i, dataset in enumerate(datasets.keys()):
                print(f"{i+1}. {dataset}")
            user = int(input(": ")) - 1
            dataset = list(datasets.keys())[user]
            con = sqlite3.connect(db_path)
            cur.execute(create_statements["queries"])
            cur = con.cursor()
            dataset = {dataset: list(datasets.values())[user]}
            actualizar_CKAN(dataset)
        crearPromptInicio()
        user = input(": ")
# system("rm -r *.mrc && rm -r *.zip")
