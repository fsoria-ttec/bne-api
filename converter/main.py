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
import time
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
from ckan import actualizar_CKAN
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
    
    # Crear directorio para archivos descargados si no existe
    if not os.path.exists("mrcs"):
        os.makedirs("mrcs")
        logger.debug("Directorio 'mrcs' creado")
    
    # Archivo para almacenar información de archivos
    file_info_path = "mrcs/file_info.json"
    
    # Cargar información existente o crear diccionario vacío
    if os.path.exists(file_info_path):
        try:
            with open(file_info_path, 'r') as f:
                file_info = json.load(f)
                logger.debug(f"Archivo de información cargado: {file_info_path}")
        except Exception as e:
            logger.warning(f"Error al cargar archivo de información: {str(e)}")
            file_info = {}
    else:
        file_info = {}
        logger.debug("No se encontró archivo de información previo")
    
    failed_downloads = []
    skipped_files = []
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        def download(url):
            try:
                logger.debug(f"Verificando {url}")
                z_file_name = re.findall(r"/([^/]+)-mrc_new\.mrc", url)[0]
                file_path = f"mrcs/{z_file_name}-mrc_new.mrc"
                
                # Verificar si el archivo ha cambiado usando una solicitud HEAD
                file_changed = True
                skip_reason = None
                
                if os.path.exists(file_path):
                    try:
                        # Solicitud HEAD para obtener metadatos (ligera)
                        head_response = req.head(url, verify=False, timeout=30)
                        head_response.raise_for_status()
                        
                        # Verificación por tamaño
                        remote_size = int(head_response.headers.get('Content-Length', '0'))
                        local_size = os.path.getsize(file_path)
                        
                        if remote_size > 0 and local_size == remote_size:
                            # Verificación por Last-Modified
                            current_modified = head_response.headers.get('Last-Modified')
                            stored_modified = file_info.get(z_file_name, {}).get('modified')
                            
                            if current_modified and stored_modified and current_modified == stored_modified:
                                file_changed = False
                                skip_reason = "Last-Modified"
                            else:
                                # Verificar por tiempo mínimo entre actualizaciones
                                last_check = file_info.get(z_file_name, {}).get('last_check', 0)
                                min_hours = 24  # Tiempo mínimo entre verificaciones
                                
                                if last_check and (time.time() - last_check < min_hours * 3600):
                                    file_changed = False
                                    skip_reason = "tiempo mínimo entre verificaciones"
                    
                    except Exception as e:
                        logger.warning(f"Error verificando cambios en {z_file_name}: {str(e)}")
                        # Si falla la verificación, asumimos que ha cambiado por seguridad
                
                # Si no ha cambiado, omitir descarga
                if not file_changed:
                    logger.info(f"Omitiendo {z_file_name} - no ha cambiado (verificado por {skip_reason})")
                    ui.show_info(f"Omitiendo {z_file_name} - no ha cambiado")
                    skipped_files.append(z_file_name)
                    return
                
                # Si ha cambiado o no existe, descargarlo
                logger.info(f"Descargando {z_file_name}")
                ui.show_info(f"Descargando {z_file_name}...")
                
                # Una sola solicitud GET para descargar el archivo
                response = req.get(url, verify=False, stream=True, timeout=60)
                response.raise_for_status()
                
                # Guardar el archivo
                total_size = int(response.headers.get('content-length', 0))
                
                with open(file_path, "wb") as z_file:
                    with tqdm(total=total_size, unit='B', unit_scale=True, 
                             desc=f"Descargando {z_file_name}") as pbar:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                z_file.write(chunk)
                                pbar.update(len(chunk))
                
                # Actualizar información del archivo
                file_info[z_file_name] = {
                    'modified': response.headers.get('Last-Modified'),
                    'size': total_size,
                    'last_check': time.time()
                }
                
                # Guardar información actualizada
                with open(file_info_path, 'w') as f:
                    json.dump(file_info, f, indent=2)
                
                logger.info(f"Descarga completada: {z_file_name}")
                ui.show_success(f"Descarga completada: {z_file_name}")
                
            except Exception as e:
                error_msg = f"Error al descargar {url}: {str(e)}"
                logger.error(error_msg)
                ui.show_error(error_msg)
                failed_downloads.append(url)
        
        # Crear tareas de descarga
        futures = []
        for url in urls:
            futures.append(executor.submit(download, url))
        
        # Esperar a que todas terminen
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()  # Obtener resultado (o excepción)
            except Exception as e:
                logger.error(f"Error en tarea de descarga: {str(e)}")
    
    # Mostrar resumen
    logger.info(f"Resumen de descarga: Total={len(urls)}, Omitidos={len(skipped_files)}, Fallidos={len(failed_downloads)}")
    
    if failed_downloads:
        logger.warning(f"{len(failed_downloads)} archivos no se pudieron descargar")
        ui.show_warning(f"{len(failed_downloads)} archivos no se pudieron descargar")
        
        if ui.show_confirmation("¿Desea reintentar las descargas fallidas?"):
            logger.info("Reintentando descargas fallidas")
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
        
        ui.print_section(f"Procesando dataset: {dataset}")
        logger.info(f"Iniciando procesamiento del dataset {dataset}")
        
        try:
            # Eliminar tabla existente si existe
            cur.execute(f"DROP TABLE IF EXISTS {dataset}")
            # Crear tabla para el dataset
            cur.execute(create_statements[f"{dataset}"])
            con.commit()
            logger.debug(f"Tabla {dataset} creada")
            
            # Procesar archivo MRC
            marc_file_path = f"mrcs/{mrc_file}-mrc_new.mrc"
            
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
                batch_size = 1000
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
                        # Actualizar CKAN
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
                    cur = con.cursor()
                    
                    # Descargar archivo específico
                    if get_files((urls[user],)):
                        # Procesar dataset específico
                        dataset_dict = {dataset: list(datasets.values())[user]}
                        if insertion(dataset_dict):
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
                export_dir = "./exports"
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
                        export_dir = "./exports"
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
        
        elif choice == 6:  # Salir
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
