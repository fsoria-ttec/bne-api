#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo de interfaz de consola para BNE Converter
"""

import os
import sys
import logging
from colorama import init, Fore, Style, Back

# Inicializar colorama para soporte cross-platform de colores
init()

class ConsoleUI:
    """Clase para manejar la interfaz de usuario por consola"""
    
    def __init__(self):
        self.title = "BNE Converter"
        self.version = "2.0"
        self.logger = logging.getLogger(__name__)
    
    def clear_screen(self):
        """Limpia la pantalla de la consola"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        """Imprime un encabezado atractivo para la aplicación"""
        self.clear_screen()
        print(f"{Fore.BLUE}{Style.BRIGHT}" + "═" * 54)
        print(f"{Fore.BLACK}{Back.BLUE}{Style.BRIGHT} {self.title} v{self.version} ".center(54))
        print(f"{Fore.BLUE}{Back.RESET}{Style.BRIGHT}" + "═" * 54)
        print(f"{Style.RESET_ALL}")
    
    def print_footer(self):
        """Imprime un pie de página para los menús"""
        print(f"\n{Fore.BLUE}{Style.BRIGHT}" + "═" * 54)
        print(f"{Style.RESET_ALL}")
    
    def print_section(self, title):
        """Imprime un título de sección"""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}┌────── {title} ───────┐" )
        print(f"{Style.RESET_ALL}")
    
    def show_main_menu(self):
        """Muestra el menú principal y obtiene la selección del usuario"""
        self.print_header()
        
        print(f"{Fore.GREEN}{Style.BRIGHT}Seleccione una opción:{Style.RESET_ALL}\n")
        
        options = [
            "Procesar todos los datasets",
            "Procesar dataset específico",
            "Generar archivos para todos los datasets",
            "Generar archivos para dataset específico",
            "Actualizar CKAN",
            "Salir"
        ]
        
        for i, option in enumerate(options, 1):
            print(f"{Fore.YELLOW}{i}.{Style.RESET_ALL} {option}")
        
        self.print_footer()
        
        # Obtener y validar entrada
        while True:
            try:
                choice = input(f"{Fore.GREEN}Opción: {Style.RESET_ALL}")
                if choice.lower() in ('q', 'quit', 'exit'):
                    return len(options)  # Opción de salir
                
                choice = int(choice)
                if 1 <= choice <= len(options):
                    return choice
                print(f"{Fore.RED}Opción inválida. Intente nuevamente.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Por favor, ingrese un número válido.{Style.RESET_ALL}")
    
    def show_dataset_selection(self, datasets):
        """Muestra una lista de datasets para selección"""
        self.print_section("Selección de Dataset")
        
        print(f"{Fore.GREEN}Seleccione un dataset:{Style.RESET_ALL}\n")
        
        # Organizar en columnas para mejor visualización
        items_per_row = 3
        for i in range(0, len(datasets), items_per_row):
            row_items = list(datasets.items())[i:i+items_per_row]
            row_str = ""
            for idx, (key, value) in enumerate(row_items, i+1):
                item = f"{Fore.YELLOW}{idx}.{Style.RESET_ALL} {key:<3} - {value:<20}"
                row_str += item + " " * (5 - len(item) % 5)
            print(row_str)
        
        print(f"\n{Fore.YELLOW}0.{Style.RESET_ALL} Volver al menú principal")
        
        # Obtener y validar entrada
        while True:
            try:
                choice = input(f"{Fore.GREEN}Dataset: {Style.RESET_ALL}")
                choice = int(choice)
                if choice == 0:
                    return None
                if 1 <= choice <= len(datasets):
                    return list(datasets.keys())[choice-1]
                print(f"{Fore.RED}Opción inválida. Intente nuevamente.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Por favor, ingrese un número válido.{Style.RESET_ALL}")
    
    def show_confirmation(self, message):
        """Muestra un mensaje de confirmación y retorna True/False"""
        print(f"\n{Fore.YELLOW}{message} (s/n){Style.RESET_ALL}")
        
        while True:
            choice = input(f"{Fore.GREEN}Respuesta: {Style.RESET_ALL}").lower()
            if choice in ('s', 'si', 'sí', 'y', 'yes'):
                return True
            if choice in ('n', 'no'):
                return False
            print(f"{Fore.RED}Respuesta inválida. Use 's' para sí o 'n' para no.{Style.RESET_ALL}")
    
    def show_progress(self, message, current, total):
        """Muestra una barra de progreso simple"""
        percentage = int(100 * current / total) if total > 0 else 0
        bar_length = 40
        filled_length = int(bar_length * current / total) if total > 0 else 0
        
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        print(f"\r{Fore.CYAN}{message}: {Style.RESET_ALL}|{bar}| {percentage}% ({current}/{total})", end='')
        
        if current == total:
            print()  # Nueva línea al completar
    
    def show_success(self, message):
        """Muestra un mensaje de éxito"""
        print(f"\n{Fore.GREEN}{Style.BRIGHT}✓ {message}{Style.RESET_ALL}")
        self.logger.info(message)
    
    def show_error(self, message):
        """Muestra un mensaje de error"""
        print(f"\n{Fore.RED}{Style.BRIGHT}✗ {message}{Style.RESET_ALL}")
        self.logger.error(message)
    
    def show_warning(self, message):
        """Muestra un mensaje de advertencia"""
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}⚠ {message}{Style.RESET_ALL}")
        self.logger.warning(message)
    
    def show_info(self, message):
        """Muestra un mensaje informativo"""
        print(f"\n{Fore.CYAN}ℹ {message}{Style.RESET_ALL}")
        self.logger.info(message)
    
    def wait_for_keypress(self, message="Presione ENTER para continuar..."):
        """Espera a que el usuario presione una tecla"""
        print(f"\n{Fore.YELLOW}{message}{Style.RESET_ALL}")
        input()
