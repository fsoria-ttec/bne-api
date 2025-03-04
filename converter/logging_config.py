#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo de configuración de logging para BNE Converter
"""

import os
import logging
from datetime import datetime

def setup_logging(level=logging.INFO):
    """
    Configura el sistema de logging con diferentes niveles y formatos
    
    Args:
        level: Nivel de logging (default: logging.INFO)
        
    Returns:
        Logger configurado
    """
    # Crear directorio para logs si no existe
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Nombre de archivo basado en fecha
    log_date = datetime.now().strftime("%Y-%m-%d")
    log_file = f"{log_dir}/bne_converter_{log_date}.log"
    
    # Configurar el logger raíz
    logger = logging.getLogger()
    logger.setLevel(level)  # Nivel base para capturar todo
    
    # Limpiar handlers existentes para evitar duplicación
    if logger.handlers:
        logger.handlers.clear()
    
    # Formato detallado para archivo
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    
    # Formato simple para consola (solo mostrará errores y advertencias)
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    # Handler para archivo (guarda todos los mensajes)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # Guardar todo en el archivo
    file_handler.setFormatter(file_formatter)
    
    # Handler para consola (solo mensajes importantes)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Solo mensajes de advertencia o error
    console_handler.setFormatter(console_formatter)
    
    # Añadir handlers al logger raíz
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Mensaje inicial
    logger.info(f"Iniciando sesión de BNE Converter - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return logger
