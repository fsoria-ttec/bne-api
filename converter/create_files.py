#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo para generar archivos de exportación a partir de la base de datos BNE
"""

import os
import sqlite3
from zipfile import ZipFile
import zipfile
import traceback
import logging
from tqdm import tqdm
from utils import ejecutar_comando
from constants import *

# Importar configuración de logging si existe
try:
    from logging_config import setup_logging
    logger = setup_logging()
except ImportError:
    # Configuración básica si no existe el módulo
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)

# Importar UI si existe
try:
    from console_ui import ConsoleUI
    ui = ConsoleUI()
    ui_available = True
except ImportError:
    ui_available = False

# Definir la carpeta de exportación centralizada
EXPORT_DIR = "./exports"

# Conexión a la base de datos
try:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
except Exception as e:
    logger.error(f"Error conectando a la base de datos: {str(e)}")
    if ui_available:
        ui.show_error(f"Error conectando a la base de datos: {str(e)}")
    else:
        print(f"Error: {str(e)}")

def human_fields(dataset) -> str:
    """Obtiene los campos humanos de un dataset"""
    try:
        result = ""
        fields = tuple(filter(lambda f: not f.startswith("t_"), (row[1] for row in cur.execute(f"pragma table_info({dataset});"))))
        for field in fields:
            result += f"{field}, "
        return result[:-2]
    except Exception as e:
        logger.error(f"Error obteniendo campos de {dataset}: {str(e)}")
        return ""

def marc_fields(dataset) -> str:
    """Obtiene los campos MARC de un dataset"""
    try:
        result = ""
        fields = tuple(filter(lambda f: f.startswith("t_"), (row[1] for row in cur.execute(f"pragma table_info({dataset});"))))
        for field in fields:
            result += f"{field}, "
        return result[:-2]
    except Exception as e:
        logger.error(f"Error obteniendo campos MARC de {dataset}: {str(e)}")
        return ""

def ensure_export_directory():
    """Asegura que el directorio de exportación centralizado existe"""
    os.makedirs(EXPORT_DIR, exist_ok=True)
    logger.debug(f"Directorio de exportación {EXPORT_DIR} creado o verificado")

def export_csv(dataset:str) -> None:
    """Exporta el dataset en formato CSV (UTF-8 y CP1252)"""
    try:
        ensure_export_directory()
        logger.info(f"Exportando {dataset} en CSV-UTF8")
        if ui_available:
            ui.show_info(f"Exportando {dataset} en CSV-UTF8")
        
        # Usar nombre de archivo con prefijo del dataset para evitar conflictos
        file_name = f"{EXPORT_DIR}/{dataset}_{file_names[dataset].lower()}-UTF8.csv"
        query = f"SELECT {human_fields(dataset)} FROM {dataset};"
        command = f'''sqlite3 {db_path} -header -csv -separator ";" " {query} " > {file_name}'''
        os.system(command)
        
        logger.info(f"Exportando {dataset} en CSV-CP1252")
        if ui_available:
            ui.show_info(f"Exportando {dataset} en CSV-CP1252")
        ejecutar_comando("copiar", file_name, f"{EXPORT_DIR}/{dataset}_{file_names[dataset].lower()}-CP1252.csv")
        
        logger.info(f"Exportando {dataset} en ODS")
        if ui_available:
            ui.show_info(f"Exportando {dataset} en ODS")
        ejecutar_comando("copiar", file_name, f"{EXPORT_DIR}/{dataset}_{file_names[dataset].lower()}-ODS.ods")
        
        # Comprimir archivos
        with ZipFile(f"{EXPORT_DIR}/{dataset}_{file_names[dataset].lower()}-UTF8.zip", 'w', zipfile.ZIP_DEFLATED) as myzip:
            myzip.write(file_name, os.path.basename(file_name))
        
        with ZipFile(f"{EXPORT_DIR}/{dataset}_{file_names[dataset].lower()}-CP1252.zip", 'w', zipfile.ZIP_DEFLATED) as myzip:
            myzip.write(f"{EXPORT_DIR}/{dataset}_{file_names[dataset].lower()}-CP1252.csv", 
                       os.path.basename(f"{EXPORT_DIR}/{dataset}_{file_names[dataset].lower()}-CP1252.csv"))
        
        with ZipFile(f"{EXPORT_DIR}/{dataset}_{file_names[dataset].lower()}-ODS.zip", 'w', zipfile.ZIP_DEFLATED) as myzip:
            myzip.write(f"{EXPORT_DIR}/{dataset}_{file_names[dataset].lower()}-ODS.ods", 
                       os.path.basename(f"{EXPORT_DIR}/{dataset}_{file_names[dataset].lower()}-ODS.ods"))
        
        logger.debug(f"Archivos CSV para {dataset} comprimidos correctamente")
        
    except Exception as e:
        logger.error(f"Error exportando {dataset} a CSV: {str(e)}")
        logger.error(traceback.format_exc())
        if ui_available:
            ui.show_error(f"Error exportando a CSV: {str(e)}")
        else:
            print(f"Error: {str(e)}")

def export_txt(dataset:str) -> None:
    """Exporta el dataset en formato TXT"""
    try:
        ensure_export_directory()
        logger.info(f"Exportando {dataset} en TXT-UTF8")
        if ui_available:
            ui.show_info(f"Exportando {dataset} en TXT-UTF8")
        
        file_name = f"{EXPORT_DIR}/{dataset}_{file_names[dataset].lower()}-TXT.txt"
        query = f"SELECT {human_fields(dataset)} FROM {dataset};"
        command = f'''sqlite3 {db_path} -header -csv -separator "|" " {query} " > {file_name}'''
        os.system(command)
        
        # Comprimir archivo
        with ZipFile(f"{EXPORT_DIR}/{dataset}_{file_names[dataset].lower()}-TXT.zip", 'w', zipfile.ZIP_DEFLATED) as myzip:
            myzip.write(file_name, os.path.basename(file_name))
        
        logger.debug(f"Archivo TXT para {dataset} comprimido correctamente")
        
    except Exception as e:
        logger.error(f"Error exportando {dataset} a TXT: {str(e)}")
        logger.error(traceback.format_exc())
        if ui_available:
            ui.show_error(f"Error exportando a TXT: {str(e)}")
        else:
            print(f"Error: {str(e)}")

def export_json(dataset:str) -> None:
    """Exporta el dataset en formato JSON"""
    try:
        ensure_export_directory()
        logger.info(f"Exportando {dataset} en JSON")
        if ui_available:
            ui.show_info(f"Exportando {dataset} en JSON")
        
        file_name = f"{EXPORT_DIR}/{dataset}_{file_names[dataset].lower()}-JSON.json"
        query = f"SELECT {human_fields(dataset)} FROM {dataset};"
        command = f'''sqlite3 {db_path} -json " {query} " > {file_name}'''
        os.system(command)
        
        # Comprimir archivo
        with ZipFile(f"{EXPORT_DIR}/{dataset}_{file_names[dataset].lower()}-JSON.zip", 'w', zipfile.ZIP_DEFLATED) as myzip:
            myzip.write(file_name, os.path.basename(file_name))
        
        logger.debug(f"Archivo JSON para {dataset} comprimido correctamente")
        
    except Exception as e:
        logger.error(f"Error exportando {dataset} a JSON: {str(e)}")
        logger.error(traceback.format_exc())
        if ui_available:
            ui.show_error(f"Error exportando a JSON: {str(e)}")
        else:
            print(f"Error: {str(e)}")

def export_xml_2(dataset:str):
    """Exporta el dataset en formato XML optimizado"""
    try:
        ensure_export_directory()
        logger.info(f"Exportando {dataset} en XML")
        if ui_available:
            ui.show_info(f"Exportando {dataset} en XML")
        
        def xml_factory(cursor, row):
            result = "<item>"
            for idx, col in enumerate(cursor.description):
                if row[idx]:
                    # Escapar caracteres especiales XML
                    value = str(row[idx])
                    value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    result += f"<{col[0]}>{value}</{col[0]}>"
            result += "</item>"
            return result
        
        headers = human_fields(dataset)
        con = sqlite3.connect(db_path)
        con.row_factory = xml_factory
        cur = con.cursor()
        
        file_name = f"{EXPORT_DIR}/{dataset}_{file_names[dataset].lower()}-XML.xml"
        query = f"SELECT {headers} FROM {dataset};"
        
        # Obtener conteo total para la barra de progreso
        count_cur = con.cursor()
        count_cur.execute(f"SELECT COUNT(*) FROM {dataset}")
        total_records = count_cur.fetchone()[0]
        
        # Exportar en lotes para mejor rendimiento
        batch_size = 5000
        offset = 0
        
        with open(file_name, "w", encoding="utf-8") as file:
            file.write('''<?xml version="1.0" encoding="UTF-8"?>\n<list>''')
            
            with tqdm(total=total_records, desc=f"Exportando {dataset} a XML", unit="registros") as pbar:
                while offset < total_records:
                    query_paginated = f"{query} LIMIT {batch_size} OFFSET {offset}"
                    data = cur.execute(query_paginated)
                    records = list(data)
                    
                    file.writelines(records)
                    
                    # Actualizar contador y offset
                    offset += len(records)
                    pbar.update(len(records))
                    
                    # Si no hay más registros, salir
                    if len(records) < batch_size:
                        break
            
            file.write("</list>")
        
        # Comprimir archivo
        with ZipFile(f"{EXPORT_DIR}/{dataset}_{file_names[dataset].lower()}-XML.zip", 'w', zipfile.ZIP_DEFLATED) as myzip:
            myzip.write(file_name, os.path.basename(file_name))
        
        logger.debug(f"Archivo XML para {dataset} comprimido correctamente")
        
    except Exception as e:
        logger.error(f"Error exportando {dataset} a XML: {str(e)}")
        logger.error(traceback.format_exc())
        if ui_available:
            ui.show_error(f"Error exportando a XML: {str(e)}")
        else:
            print(f"Error: {str(e)}")

def cleanup_files():
    """Borra todos los archivos que no son .zip en el directorio de exportación"""
    try:
        logger.info(f"Limpiando archivos temporales en {EXPORT_DIR}")
        
        for file in os.listdir(EXPORT_DIR):
            if not file.endswith('.zip'):
                file_path = os.path.join(EXPORT_DIR, file)
                if os.path.isfile(file_path):  # Asegurarse de que es un archivo
                    ejecutar_comando("borrar_arc", file_path)
                    logger.debug(f"Archivo temporal eliminado: {file_path}")
        
    except Exception as e:
        logger.error(f"Error limpiando archivos temporales: {str(e)}")
        if ui_available:
            ui.show_error(f"Error limpiando archivos temporales: {str(e)}")
        else:
            print(f"Error: {str(e)}")

def process_all_datasets():
    """Procesa todos los datasets disponibles"""
    ensure_export_directory()
    
    for dataset_key in datasets.keys():
        dataset = dataset_key[:3]
        try:
            export_csv(dataset)
            export_txt(dataset)
            export_json(dataset)
            export_xml_2(dataset)
            logger.info(f"Procesamiento completo de {dataset}")
            if ui_available:
                ui.show_success(f"Procesamiento completo de {dataset}")
        except Exception as e:
            logger.error(f"Error procesando {dataset}: {str(e)}")
            if ui_available:
                ui.show_error(f"Error procesando {dataset}: {str(e)}")
            else:
                print(f"Error procesando {dataset}: {str(e)}")
    
    # Limpieza final
    cleanup_files()

def process_single_dataset(dataset):
    """Procesa un dataset específico"""
    try:
        ensure_export_directory()
        
        dataset = dataset[:3]
        export_csv(dataset)
        export_txt(dataset)
        export_json(dataset)
        export_xml_2(dataset)
        
        # Limpieza selectiva
        cleanup_files()
        
        logger.info(f"Procesamiento completo de {dataset}")
        if ui_available:
            ui.show_success(f"Procesamiento completo de {dataset}")
    except Exception as e:
        logger.error(f"Error procesando {dataset}: {str(e)}")
        if ui_available:
            ui.show_error(f"Error procesando {dataset}: {str(e)}")
        else:
            print(f"Error procesando {dataset}: {str(e)}")

if __name__ == "__main__":
    try:
        if ui_available:
            ui.print_header()
            ui.print_section("Generación de Archivos")
            
        print('''
        1. Crear todos los ficheros
        2. Crear por dataset
        ''')
        user = input(": ")
        
        if user == "1":
            process_all_datasets()
            if ui_available:
                ui.show_success("Todos los datasets procesados correctamente")
            else:
                print("Todos los datasets procesados correctamente")
                
        elif user == "2": 
            dataset = input("DATASET: ")
            process_single_dataset(dataset)
            if ui_available:
                ui.show_success(f"Dataset {dataset} procesado correctamente")
            else:
                print(f"Dataset {dataset} procesado correctamente")
                
        if ui_available:
            ui.wait_for_keypress()
                
    except Exception as e:
        logger.error(f"Error en la ejecución principal: {str(e)}")
        logger.error(traceback.format_exc())
        if ui_available:
            ui.show_error(f"Error en la ejecución: {str(e)}")
            ui.wait_for_keypress()
        else:
            print(f"Error: {str(e)}")
