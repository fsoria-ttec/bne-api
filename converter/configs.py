#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuración global para BNE Converter
"""

import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Directorios y archivos
BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "dbs"
MRC_DIR = BASE_DIR / "mrcs"
LOG_DIR = BASE_DIR / "logs"
CONFIG_FILE = BASE_DIR / "bne_config.json"

# Crear directorios si no existen
for directory in [DB_DIR, MRC_DIR, LOG_DIR]:
    directory.mkdir(exist_ok=True)

# Base de datos
DB_PATH = os.path.join(DB_DIR, "bne.db")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

# CKAN
CKAN_URL = os.getenv("BNE_CKAN_URL", "http://svjc-des-ckan.ttec.es:84/catalogo")
API_BASE_URL = os.getenv("BNE_API_BASE_URL", "http://svjc-des-bne.ttec.es:3000/api")
API_KEY = os.getenv("BNE_API_KEY", "")

# Opciones de exportación
EXPORT_FORMATS = {
    "CSV": {"enabled": True, "extension": "csv", "mime": "text/csv", "encoding": ["UTF8", "CP1252"]},
    "JSON": {"enabled": True, "extension": "json", "mime": "application/json"},
    "XML": {"enabled": True, "extension": "xml", "mime": "application/xml"},
    "TXT": {"enabled": True, "extension": "txt", "mime": "text/plain"},
    "ODS": {"enabled": True, "extension": "ods", "mime": "application/vnd.oasis.opendocument.spreadsheet"}
}

# Opciones de rendimiento
BATCH_SIZE = 1000
CONCURRENT_DOWNLOADS = 5
SQLITE_PRAGMAS = {
    "journal_mode": "WAL",
    "synchronous": "NORMAL",
    "cache_size": 10000,
    "temp_store": "MEMORY"
}

# Cargar configuración personalizada si existe
def load_config():
    """Carga la configuración desde el archivo JSON si existe"""
    config = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"Configuración cargada desde: {CONFIG_FILE}")
            
            # Actualizar variables globales con los valores de la configuración
            global BATCH_SIZE, CONCURRENT_DOWNLOADS, EXPORT_FORMATS
            
            if "batch_size" in config:
                BATCH_SIZE = config["batch_size"]
            
            if "concurrent_downloads" in config:
                CONCURRENT_DOWNLOADS = config["concurrent_downloads"]
                
            if "export_formats" in config:
                for format_name, format_config in config["export_formats"].items():
                    if format_name in EXPORT_FORMATS:
                        EXPORT_FORMATS[format_name].update(format_config)
                        
        except Exception as e:
            print(f"Error al cargar configuración: {e}")
    
    return config

# Guardar configuración personalizada
def save_config(config):
    """Guarda la configuración en un archivo JSON"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        print(f"Configuración guardada en: {CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"Error al guardar configuración: {e}")
        return False

# Cargar configuración al iniciar el módulo
CONFIG = load_config()
