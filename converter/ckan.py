import requests as req
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
from datetime import datetime
from constants import dataset_titles
from configs import CONFIG_FILE
from logging_config import setup_logging

load_dotenv()

CONFIG_FILE = Path(__file__).resolve().parent / "bne_config.json"

API_KEY = os.getenv("BNE_API_KEY", "")
CKAN_URL = os.getenv("BNE_CKAN_URL", "http://svjc-des-ckan.ttec.es:84/catalogo")
API_BASE_URL = os.getenv("BNE_API_BASE_URL", "http://svjc-des-bne.ttec.es:3000/api")

def cargar_configuracion():
    """
    Carga la configuración desde un archivo JSON externo.
    Si el archivo no existe, crea uno con la configuración predeterminada.
    
    Returns:
        dict: Configuración cargada del archivo JSON o valores predeterminados
    """
    # Valores predeterminados
    config_predeterminada = {
        "owner_org": "test-api",
        "author": "",
        "contact_email": "info@ejemplo.es",
        "dcat_type": "http://inspire.ec.europa.eu/metadata-codelist/ResourceType/dataset",
        "language": "http://publications.europa.eu/resource/authority/language/DEU",
        "maintainer": "BNE",
        "hvd_category": "",
        "formatos_exportacion": [
            {"name": "JSON", "extension": "json", "mimetype": "application/json"},
            {"name": "CSV", "extension": "csv", "mimetype": "text/csv"}
        ],
        "traduccion_habilitada": True
    }
    
    # Comprobar si existe el archivo de configuración
    if not os.path.exists(CONFIG_FILE):
        # Crear archivo con configuración predeterminada
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_predeterminada, f, indent=2)
        print(f"Archivo de configuración creado: {CONFIG_FILE}")
        return config_predeterminada
    
    # Cargar configuración desde el archivo
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"Configuración cargada desde: {CONFIG_FILE}")
        
        # Completar con valores predeterminados si faltan campos
        for clave, valor in config_predeterminada.items():
            if clave not in config:
                config[clave] = valor
                
        return config
    except Exception as e:
        print(f"Error al cargar configuración: {e}")
        print("Usando configuración predeterminada")
        return config_predeterminada

def actualizar_fecha_ckan(datasets):
    """
    Actualiza SOLO la fecha de última modificación de los datasets en CKAN
    sin alterar ningún otro metadato.
    
    Args:
        datasets (dict): Diccionario con los nombres de los datasets a actualizar
    """
    # Cargar configuración desde el archivo JSON
    config = cargar_configuracion()
    logger = setup_logging()
    
    try:
        session = req.Session()
        session.headers.update({
            'Authorization': API_KEY,
            'Content-Type': 'application/json'
        })
        
        for dataset_name, mrc_file in datasets.items():
            dataset_id = dataset_name[:3]  
            
            logger.info(f"Actualizando fecha de modificación para dataset: {dataset_id}")
            
            # Verificar si el dataset ya existe en CKAN
            check_url = f"{CKAN_URL}/api/3/action/package_show"
            try:
                response = session.get(f"{check_url}?id={dataset_id}", verify=False)
                dataset_exists = response.status_code == 200
                
                if dataset_exists:
                    existing_dataset = response.json().get('result', {})
                    
                    # Si el dataset existe, solo actualizar la fecha de modificación
                    if 'id' in existing_dataset:
                        update_url = f"{CKAN_URL}/api/3/action/package_update"
                        dataset_data = {'id': existing_dataset['id']}
                        
                        try:
                            with tqdm(total=1, desc=f"Actualizando fecha en CKAN", unit="dataset") as pbar:
                                response = session.post(update_url, json=dataset_data, verify=False)
                                response.raise_for_status()
                                pbar.update(1)
                            
                            logger.info(f"Fecha de modificación actualizada para dataset {dataset_id}")
                            
                        except Exception as e:
                            logger.error(f"Error actualizando fecha para dataset {dataset_id}: {e}")
                            continue
                else:
                    logger.warning(f"El dataset {dataset_id} no existe en CKAN, no se puede actualizar la fecha")
                
            except Exception as e:
                logger.error(f"Error al verificar existencia del dataset {dataset_id}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error general al actualizar fechas en CKAN: {e}")
        
    return

def actualizar_CKAN(datasets):
    """
    Actualiza los conjuntos de datos en el catálogo CKAN.
    
    Args:
        datasets (dict): Diccionario con los nombres de los conjuntos de datos a actualizar
    """
    # Cargar configuración desde el archivo JSON
    config = cargar_configuracion()
    logger = setup_logging()
    
    try:
        # Importar ckanapi
        import ckanapi
        
        # Crear cliente CKAN
        ckan = ckanapi.RemoteCKAN(
            CKAN_URL,
            apikey=API_KEY
        )
        
        for dataset_name, mrc_file in datasets.items():
            dataset_id = dataset_name[:3]  
            
            logger.info(f"Procesando dataset: {dataset_id}")
            
            # Verificar si el dataset ya existe en CKAN
            try:
                existing_dataset = ckan.action.package_show(id=dataset_id)
                dataset_exists = True
            except ckanapi.NotFound:
                dataset_exists = False
                existing_dataset = {}
            except Exception as e:
                logger.error(f"Error al verificar existencia del dataset {dataset_id}: {str(e)}")
                dataset_exists = False
                existing_dataset = {}
            
            # Definir los recursos como URLs para diferentes formatos
            current_date = datetime.now().strftime("%Y-%m-%d")
            resources = []
            
            # Mantener recursos existentes que no son de estos formatos específicos
            if dataset_exists:
                for resource in existing_dataset.get('resources', []):
                    # Si el recurso no es uno de los que vamos a crear, lo mantenemos
                    extensions = [fmt["extension"] for fmt in config["formatos_exportacion"]]
                    if not any(ext in resource.get('name', '').lower() for ext in extensions):
                        resources.append(resource)
            
            # Añadir recursos para diferentes formatos
            formats = config["formatos_exportacion"]
            
            for fmt in formats:
                url = f"{API_BASE_URL}/{dataset_id}.{fmt['extension']}"
                
                # Comprobar si el recurso ya existe (por URL)
                existing_resource = None
                if dataset_exists:
                    for resource in existing_dataset.get('resources', []):
                        if resource.get('url') == url:
                            existing_resource = resource
                            break
                
                # Si existe, mantener el ID para actualizarlo en lugar de crear uno nuevo
                resource_data = {
                    'name': f"Datos en formato {fmt['name']}",
                    'description': f"Descarga del dataset en formato {fmt['name']}",
                    'url': url,
                    'format': fmt['name'],
                    'mimetype': fmt['mimetype'],
                    'last_modified': current_date,
                    'resource_type': 'api'
                }
                
                if existing_resource:
                    resource_data['id'] = existing_resource.get('id')
                
                resources.append(resource_data)
            
            # Preparar los datos del JSON para la creación/actualización
            dataset_data = {
                'name': dataset_id,
                'title': f"Conjunto de datos",
                'resources': resources        
            }
            
            # Añadir título traducido si está habilitado
            if config.get("traduccion_habilitada", True):
                dataset_data["title_translated"] = {
                    "en": dataset_titles.get(dataset_id, f"Dataset {dataset_id}"),
                    "es": dataset_titles.get(dataset_id, f"Conjunto de datos {dataset_id}")
                }
                dataset_data["notes_translated"] = {
                    "en": f"Data updated from MARC21 files ({mrc_file})",
                    "es": f"Datos actualizados desde registros MARC21 ({mrc_file})"
                }
            
            # Añadir descripción
            dataset_data['notes'] = f"Datos actualizados desde registros MARC21 ({mrc_file})"
            
            # Lista de campos permitidos para CKAN
            campos_permitidos = [
                "owner_org", "author", "contact_email", "dcat_type",
                "language", "maintainer", "hvd_category", "identifier"
            ]
            
            # Solo añadir campos explícitamente permitidos
            for key in campos_permitidos:
                if key in config:
                    dataset_data[key] = config[key]
                    
            # Identificador específico
            dataset_data["identifier"] = mrc_file
            
            # Mantener ID si existe
            if dataset_exists and 'id' in existing_dataset:
                dataset_data['id'] = existing_dataset['id']
            
            # Crear o actualizar el dataset
            try:
                with tqdm(total=1, desc=f"Actualizando dataset en CKAN", unit="dataset") as pbar:
                    if dataset_exists:
                        result = ckan.action.package_update(**dataset_data)
                        action = "actualizado"
                    else:
                        result = ckan.action.package_create(**dataset_data)
                        action = "creado"
                    pbar.update(1)
                
                logger.info(f"Dataset {dataset_id} {action} exitosamente en CKAN")
            except Exception as e:
                logger.error(f"Error al procesar dataset {dataset_id} en CKAN: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"Error general al actualizar CKAN: {str(e)}")
        
    return
