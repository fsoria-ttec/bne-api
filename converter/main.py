#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BNE Converter - Herramienta para procesar y convertir registros MARC21 de la BNE
"""

import os
import sys
import sqlite3
import re
import json
import traceback
import concurrent.futures

# Verificar directorio de base de datos
if "dbs" not in os.listdir("./"):
    import init

# Importaciones locales
from pymarc import MARCReader
import codecs
import requests as req
from models import create_statements
from humanizer import *
from constants import *
from utils import ejecutar_comando
from ckan import actualizar_fecha_ckan, actualizar_CKAN
from configs import CONFIG
from tqdm import tqdm

# Importar los nuevos módulos
from logging_config import setup_logging
from console_ui import ConsoleUI

# Configurar colorama
try:
    from colorama import init as colorama_init
    colorama_init()
except ImportError:
    print("Se recomienda instalar colorama para una mejor experiencia de usuario.")
    print("Puede instalarlo con: pip install colorama")

# Desactivar advertencias de inseguridad SSL
import warnings
from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

# Forzar encoding
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

# Inicializar logger y UI
logger = setup_logging()
ui = ConsoleUI()

def get_files(urls):
    """
    Descarga archivos MARC21 solo si han sido modificados desde la última descarga
    """
    logger.info(f"Iniciando descarga de {len(urls)} archivos")

    # Obtener la ruta configurada para archivos MARC
    mrcs_path = CONFIG.get("mrcs_path", "./mrcs")   

    # Crear directorio para archivos descargados si no existe
    if not os.path.exists(mrcs_path):
        os.makedirs(mrcs_path)
        logger.debug(f"Directorio '{mrcs_path}' creado")
    
    # Cargar timestamps existentes o crear diccionario vacío
    last_modified_file = os.path.join(mrcs_path, "last_modified.json")
    try:
        with open(last_modified_file, 'r') as f:
            last_modified_data = json.load(f)
    except Exception:
        last_modified_data = {}
    
    failed_downloads = []
    skipped_files = []
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        def download(url):
            try:
                z_file_name = re.findall(r"/([^/]+)-mrc_new\.mrc", url)[0]
                file_path = f"{mrcs_path}/{z_file_name}-mrc_new.mrc"
                
                # Iniciar solicitud GET con streaming para verificar
                res = req.get(url, verify=False, stream=True, timeout=30)
                current_modified = res.headers.get('Last-Modified')
                
                # Verificar si el archivo ya existe y no ha cambiado
                if (z_file_name in last_modified_data and 
                    current_modified and
                    current_modified == last_modified_data[z_file_name] and
                    os.path.exists(file_path)):
                    logger.info(f"Omitiendo {z_file_name} - no ha cambiado")
                    ui.show_info(f"Omitiendo {z_file_name} - no ha cambiado")
                    skipped_files.append(z_file_name)
                    return
                
                # Si el archivo ha cambiado o no existe, descargarlo
                logger.info(f"Descargando {z_file_name}")
                ui.show_info(f"Descargando {z_file_name}...")
                
                # Usar la misma conexión para descargar el archivo
                total_size = int(res.headers.get('content-length', 0))
                
                with open(file_path, "wb") as z_file:
                    with tqdm(total=total_size, unit='B', unit_scale=True, 
                             desc=f"Descargando {z_file_name}") as pbar:
                        for chunk in res.iter_content(chunk_size=8192):
                            if chunk:
                                z_file.write(chunk)
                                pbar.update(len(chunk))
                
                # Guardar el timestamp para futuras verificaciones
                if current_modified:
                    last_modified_data[z_file_name] = current_modified
                    with open(last_modified_file, 'w') as f:
                        json.dump(last_modified_data, f, indent=2)
                
                logger.info(f"Descarga completada: {z_file_name}")
                ui.show_success(f"Descarga completada: {z_file_name}")
                
            except Exception as e:
                logger.error(f"Error al descargar {url}: {str(e)}")
                ui.show_error(f"Error al descargar {url}: {str(e)}")
                failed_downloads.append(url)
        
        # Ejecutar descargas en paralelo
        futures = [executor.submit(download, url) for url in urls]
        concurrent.futures.wait(futures)
    
    # Mostrar resumen
    logger.info(f"Resumen: Total={len(urls)}, Omitidos={len(skipped_files)}, Fallidos={len(failed_downloads)}")
    
    if failed_downloads and ui.show_confirmation("¿Desea reintentar las descargas fallidas?"):
        get_files(failed_downloads)
    
    return len(failed_downloads) == 0

def insertion(datasets):
    """
    Procesa los archivos MARC y los inserta en la base de datos
    """
    logger.info(f"Iniciando inserción de datos para {len(datasets)} datasets")
    
    # Crear conexión a la base de datos
    try:
        con = sqlite3.connect(db_path)
        # Optimizar SQLite para rendimiento
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        con.execute("PRAGMA cache_size=10000")
        con.execute("PRAGMA temp_store=MEMORY")
        
        cur = con.cursor()
        cur.execute(create_statements["queries"])
        logger.debug("Tabla de consultas creada")
        
    except Exception as e:
        error_msg = f"Error al conectar con la base de datos: {str(e)}"
        logger.error(error_msg)
        ui.show_error(error_msg)
        return False
    
    # Procesar cada dataset
    success = True
    for dataset_key, mrc_file in datasets.items():
        dataset = dataset_key[:3]
        
        ui.show_info(f"Procesando dataset: {dataset}")
        logger.info(f"Iniciando procesamiento del dataset {dataset}")
        
        try:
            # Eliminar tabla existente si existe
            cur.execute(f"DROP TABLE IF EXISTS {dataset}")
            # Crear tabla para el dataset
            cur.execute(create_statements[f"{dataset}"])
            con.commit()
            logger.debug(f"Tabla {dataset} creada")
            
            # Procesar archivo MRC
            marc_file_path = f"{CONFIG.get('mrcs_path', './mrcs')}/{mrc_file}-mrc_new.mrc"
            
            if not os.path.exists(marc_file_path):
                error_msg = f"Archivo no encontrado: {marc_file_path}"
                logger.error(error_msg)
                ui.show_error(error_msg)
                success = False
                continue
            
            # Leer y procesar archivo
            with open(marc_file_path, "rb") as file:
                reader = MARCReader(file, force_utf8=True)
                logger.debug(f"Iniciando lectura de {marc_file_path}")
                
                # Preparar consulta de inserción
                fields_count = create_statements[f"{dataset}"].count("\n") - 3
                placeholders = "?, " * fields_count
                query = f"INSERT OR IGNORE INTO {dataset} VALUES ({placeholders[:-2]})"
                
                # Procesar registros en lotes
                batch_size = CONFIG.get('batch_size', 1000)
                record_count = 0
                batch = []
                
                # Iniciar transacción
                cur.execute("BEGIN TRANSACTION")
                
                with tqdm(unit=" registros") as pbar:
                    for record in reader:
                        if record:
                            # Convertir registro a diccionario y extraer valores
                            record_dict = {}
                            
                            # Procesar campos del registro
                            for field in record.get_fields():
                                tag = field.tag
                                
                                if hasattr(field, 'subfields') and field.subfields:
                                    value = ""
                                    for i in range(0, len(field.subfields), 2):
                                        if i+1 < len(field.subfields):
                                            code = field.subfields[i]
                                            content = field.subfields[i+1]
                                            value += f"|{code} {content}"
                                    
                                    if tag in record_dict:
                                        record_dict[tag] = f"{record_dict[tag]} /**/ {value}"
                                    else:
                                        record_dict[tag] = value
                                else:
                                    if hasattr(field, 'data'):
                                        data = field.data
                                        if tag in record_dict:
                                            record_dict[tag] = f"{record_dict[tag]} |a {data}"
                                        else:
                                            record_dict[tag] = f"|a {data}"
                            
                            # Extraer valores para la base de datos
                            data_row = extract_values(dataset, record_dict)
                            
                            if data_row:
                                batch.append(data_row)
                                record_count += 1
                                
                                # Si el lote está completo, ejecutar inserción
                                if len(batch) >= batch_size:
                                    cur.executemany(query, batch)
                                    batch = []
                                    pbar.update(batch_size)
                                    
                                    # Confirmar transacción cada cierto número de lotes
                                    if record_count % (batch_size * 10) == 0:
                                        con.commit()
                                        cur.execute("BEGIN TRANSACTION")
                
                # Insertar el último lote
                if batch:
                    cur.executemany(query, batch)
                    pbar.update(len(batch))
                
                # Confirmar transacción final
                con.commit()
                
                logger.info(f"Dataset {dataset}: {record_count} registros procesados")
                ui.show_success(f"Dataset {dataset}: {record_count} registros procesados")
                
        except Exception as e:
            con.rollback()
            error_msg = f"Error procesando dataset {dataset}: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            ui.show_error(error_msg)
            success = False
            
    return success

def main():
    """Función principal del programa"""
    user_choice = ""
    
    while user_choice.lower() != "q":
        choice = ui.show_main_menu()
        
        if choice == 1:  # Procesar todos los datasets
            if ui.show_confirmation("Se generarán todos los conjuntos de datos.\n¿Está seguro de que quiere continuar?"):

                # Borrar DB existente si es necesario
                try:
                    ejecutar_comando("borrar_arc", db_path)    
                except:
                    pass
                
                # Conectar a la BD
                con = sqlite3.connect(db_path)
                cur = con.cursor()
                
                # Descargar archivos
                if get_files(urls):
                    # Procesar e insertar datos
                    if insertion(datasets):
                        # Siempre actualizar fecha de modificación
                        try:
                            actualizar_fecha_ckan(datasets)
                            ui.show_info("Fecha de modificación en CKAN actualizada")
                        except Exception as e:
                            logger.error(f"Error actualizando fecha en CKAN: {str(e)}")
                            ui.show_error(f"Error actualizando fecha en CKAN: {str(e)}")
    
                        # Preguntar si actualizar todos los metadatos               
                        if ui.show_confirmation("¿Desea actualizar el catálogo CKAN?"):
                            try:
                                actualizar_CKAN(datasets)
                                ui.show_success("Catálogo CKAN actualizado correctamente")
                            except Exception as e:
                                logger.error(f"Error actualizando CKAN: {str(e)}")
                                ui.show_error(f"Error actualizando CKAN: {str(e)}")
                
                ui.show_info("Operación completada")
                ui.wait_for_keypress()
        
        elif choice == 2:  # Procesar dataset específico
            # Mostrar lista de datasets
            ui.print_section("Selección de Dataset")
            for i, dataset in enumerate(datasets.keys()):
                print(f"{i+1}. {dataset}")
            
            # Solicitar selección
            try:
                user = int(input(": ")) - 1
                if 0 <= user < len(datasets):
                    dataset = list(datasets.keys())[user]
                    
                    # Conectar a la BD
                    con = sqlite3.connect(db_path)
                    
                    # Descargar archivo específico
                    if get_files((urls[user],)):
                        # Procesar dataset específico
                        dataset_dict = {dataset: list(datasets.values())[user]}
                        if insertion(dataset_dict):    # Siempre actualizar fecha de modificación
                            try:
                                actualizar_fecha_ckan(dataset_dict)
                                ui.show_info("Fecha de modificación en CKAN actualizada")
                            except Exception as e:
                                logger.error(f"Error actualizando fecha en CKAN: {str(e)}")
                                ui.show_error(f"Error actualizando fecha en CKAN: {str(e)}")

                            # Actualizar CKAN
                            if ui.show_confirmation("¿Desea actualizar el catálogo CKAN?"):
                                try:
                                    actualizar_CKAN(dataset_dict)
                                    ui.show_success("Catálogo CKAN actualizado correctamente")
                                except Exception as e:
                                    logger.error(f"Error actualizando CKAN: {str(e)}")
                                    ui.show_error(f"Error actualizando CKAN: {str(e)}")
                else:
                    ui.show_error("Selección inválida")
            except ValueError:
                ui.show_error("Por favor, ingrese un número válido")
            
            ui.wait_for_keypress()
        
        elif choice == 3:  # Generar archivos para todos
            if "bne.db" not in os.listdir("dbs"):
                ui.show_error("¡La base de datos no ha sido creada!")
                ui.show_info("Ejecute la opción 1 o 2 primero para crear la base de datos")
                ui.wait_for_keypress()
                continue
    
            try:
                import create_files
                # Asegurarse de que el directorio de exportación exista
                export_dir = CONFIG.get("exports_path", "./exports")
                os.makedirs(export_dir, exist_ok=True)
        
                ui.show_info(f"Los archivos se exportarán a: {export_dir}")
                create_files.process_all_datasets()
                ui.show_success("Todos los archivos generados correctamente")
            except Exception as e:
                logger.error(f"Error generando archivos: {str(e)}")
                ui.show_error(f"Error generando archivos: {str(e)}")
    
            ui.wait_for_keypress()

        elif choice == 4:  # Generar archivos para dataset específico
            if "bne.db" not in os.listdir("dbs"):
                ui.show_error("¡La base de datos no ha sido creada!")
                ui.show_info("Ejecute la opción 1 o 2 primero para crear la base de datos")
                ui.wait_for_keypress()
                continue
    
            # Mostrar lista de datasets
            ui.print_section("Selección de Dataset")
            for i, dataset in enumerate(datasets.keys()):
                print(f"{i+1}. {dataset}")
    
            # Solicitar selección
            try:
                user = int(input(": ")) - 1
                if 0 <= user < len(datasets):
                    dataset = list(datasets.keys())[user][:3]
            
                    try:
                        import create_files
                        # Asegurarse de que el directorio de exportación exista
                        export_dir = CONFIG.get("exports_path", "./exports")
                        os.makedirs(export_dir, exist_ok=True)
                
                        ui.show_info(f"Los archivos se exportarán a: {export_dir}")
                        create_files.process_single_dataset(dataset)
                        ui.show_success(f"Archivos generados para {dataset}")
                    except Exception as e:
                        logger.error(f"Error generando archivos para {dataset}: {str(e)}")
                        ui.show_error(f"Error generando archivos: {str(e)}")
                else:
                    ui.show_error("Selección inválida")
            except ValueError:
                ui.show_error("Por favor, ingrese un número válido")
    
            ui.wait_for_keypress()        
        
        elif choice == 5:  # Actualizar CKAN
            # Mostrar lista de datasets
            ui.print_section("Selección de Dataset para CKAN")
            for i, dataset in enumerate(datasets.keys()):
                print(f"{i+1}. {dataset}")
            
            # Solicitar selección
            try:
                user = int(input(": ")) - 1
                if 0 <= user < len(datasets):
                    dataset = list(datasets.keys())[user]
                    
                    # Conectar a la BD
                    con = sqlite3.connect(db_path)
                    
                    # Actualizar CKAN para dataset específico
                    dataset_dict = {dataset: list(datasets.values())[user]}
                    try:
                        actualizar_CKAN(dataset_dict)
                        ui.show_success(f"Catálogo CKAN actualizado para {dataset}")
                    except Exception as e:
                        logger.error(f"Error actualizando CKAN para {dataset}: {str(e)}")
                        ui.show_error(f"Error actualizando CKAN: {str(e)}")
                else:
                    ui.show_error("Selección inválida")
            except ValueError:
                ui.show_error("Por favor, ingrese un número válido")
            
            ui.wait_for_keypress()
        
        elif choice == 0:  # Salir
            user_choice = "q"
            ui.show_info("Cerrando BNE Converter.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nPrograma interrumpido por el usuario")
        logger.info("Programa interrumpido por el usuario")
    except Exception as e:
        print(f"\nError inesperado: {str(e)}")
        logger.critical(f"Error inesperado: {str(e)}")
        logger.critical(traceback.format_exc())
