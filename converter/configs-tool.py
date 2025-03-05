#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Herramienta para configurar BNE Converter
"""

import os
import json
import pathlib
from configs import CONFIG, EXPORT_FORMATS, BATCH_SIZE, CONCURRENT_DOWNLOADS, save_config

try:
    from colorama import init, Fore, Style
    init()  # Inicializar colorama
    colorama_available = True
except ImportError:
    colorama_available = False
    print("Se recomienda instalar colorama para una mejor experiencia.")
    print("pip install colorama")

def color_text(text, color_code=""):
    """Colorea el texto si colorama está disponible"""
    if colorama_available:
        return f"{color_code}{text}{Style.RESET_ALL}"
    return text

def clear_screen():
    """Limpia la pantalla de la terminal"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    """Imprime un encabezado formateado"""
    clear_screen()
    width = 54
    
    if colorama_available:
        print(f"{Fore.BLUE}{Style.BRIGHT}" + "═" * width)
        print(f"{Fore.WHITE}{Style.BRIGHT}" + f" {title} ".center(width))
        print(f"{Fore.BLUE}{Style.BRIGHT}" + "═" * width)
        print(Style.RESET_ALL)
    else:
        print("=" * width)
        print(f" {title} ".center(width))
        print("=" * width)
        print()

def print_current_config():
    """Muestra la configuración actual"""
    print_header("Configuración actual")
    
    # Rendimiento
    print(color_text("1. Rendimiento:", Fore.GREEN + Style.BRIGHT))
    print(f"   • Tamaño de lote: {BATCH_SIZE}")
    print(f"   • Descargas concurrentes: {CONCURRENT_DOWNLOADS}")
    print()
    
    # Formatos de exportación
    print(color_text("2. Formatos de exportación:", Fore.GREEN + Style.BRIGHT))
    for format_name, format_config in EXPORT_FORMATS.items():
        status = "✓ Activado" if format_config["enabled"] else "✗ Desactivado"
        status_color = Fore.GREEN if format_config["enabled"] else Fore.RED
        
        encodings = ""
        if "encoding" in format_config and isinstance(format_config["encoding"], list):
            encodings = f" ({', '.join(format_config['encoding'])})"
        
        print(f"   • {format_name}: {color_text(status, status_color)}{encodings}")
    print()
    
    # Rutas de almacenamiento
    print(color_text("3. Rutas de almacenamiento:", Fore.GREEN + Style.BRIGHT))
    exports_path = CONFIG.get("exports_path", "./exports")
    mrcs_path = CONFIG.get("mrcs_path", "./mrcs")
    print(f"   • Ruta de exportación: {exports_path}")
    print(f"   • Ruta de archivos MARC: {mrcs_path}")
    print()
    
    # CKAN
    print(color_text("4. CKAN:", Fore.GREEN + Style.BRIGHT))
    api_key = "Configurada" if CONFIG.get("api_key", "").strip() else "No configurada"
    api_key_color = Fore.GREEN if api_key == "Configurada" else Fore.YELLOW
    print(f"   • API Key: {color_text(api_key, api_key_color)}")
    print()
    
    print(color_text("0. Salir", Fore.YELLOW))
    print()

def configure_performance():
    """Configura las opciones de rendimiento"""
    print_header("Configuración de rendimiento")
    
    print(color_text("Configuración actual:", Fore.GREEN))
    print(f"1. Tamaño de lote: {BATCH_SIZE}")
    print(f"2. Descargas concurrentes: {CONCURRENT_DOWNLOADS}")
    print()
    print("0. Volver")
    print()
    
    option = input(color_text("Seleccione una opción: ", Fore.CYAN))
    
    if option == "1":
        try:
            new_value = int(input(color_text("Nuevo tamaño de lote (1000-10000): ", Fore.GREEN)))
            if 100 <= new_value <= 10000:
                CONFIG["batch_size"] = new_value
                save_config(CONFIG)
                print(color_text("\n✓ Tamaño de lote actualizado correctamente", Fore.GREEN))
            else:
                print(color_text("\n✗ Valor fuera de rango", Fore.RED))
        except ValueError:
            print(color_text("\n✗ Por favor ingrese un número válido", Fore.RED))
    
    elif option == "2":
        try:
            new_value = int(input(color_text("Número de descargas concurrentes (1-20): ", Fore.GREEN)))
            if 1 <= new_value <= 20:
                CONFIG["concurrent_downloads"] = new_value
                save_config(CONFIG)
                print(color_text("\n✓ Descargas concurrentes actualizadas correctamente", Fore.GREEN))
            else:
                print(color_text("\n✗ Valor fuera de rango", Fore.RED))
        except ValueError:
            print(color_text("\n✗ Por favor ingrese un número válido", Fore.RED))
    
    input("\nPresione ENTER para continuar...")

def configure_export_formats():
    """Configura los formatos de exportación"""
    while True:  # Bucle para permanecer en esta pantalla hasta que el usuario elija volver
        print_header("Configuración de formatos de exportación")
        
        print(color_text("Formatos disponibles:", Fore.GREEN))
        formats = list(EXPORT_FORMATS.keys())
        
        for i, format_name in enumerate(formats, 1):
            format_config = EXPORT_FORMATS[format_name]
            status = "✓ Activado" if format_config["enabled"] else "✗ Desactivado"
            status_color = Fore.GREEN if format_config["enabled"] else Fore.RED
            
            print(f"{i}. {format_name}: {color_text(status, status_color)}")
        
        print()
        print("0. Volver")
        print()
        
        try:
            option = int(input(color_text("Seleccione un formato para cambiar su estado: ", Fore.CYAN)))
            
            if option == 0:
                return  # Salir de la función para volver al menú principal
                
            if 1 <= option <= len(formats):
                format_name = formats[option-1]
                
                if "export_formats" not in CONFIG:
                    CONFIG["export_formats"] = {}
                
                if format_name not in CONFIG["export_formats"]:
                    CONFIG["export_formats"][format_name] = {}
                
                # Cambiar estado
                current_state = EXPORT_FORMATS[format_name]["enabled"]
                new_state = not current_state
                
                # Actualizar tanto en CONFIG como en EXPORT_FORMATS
                CONFIG["export_formats"][format_name]["enabled"] = new_state
                EXPORT_FORMATS[format_name]["enabled"] = new_state
                
                # Guardar cambios
                save_config(CONFIG)
                
                # Mensaje de éxito (desaparece cuando se refresca la pantalla)
                state_message = "activado" if new_state else "desactivado"
                print(color_text(f"\n✓ Formato {format_name} {state_message} correctamente", Fore.GREEN))
                
                # Pequeña pausa para que el usuario vea el mensaje
                import time
                time.sleep(1)
                
                # No salimos de la función - el bucle continuará y mostrará el menú actualizado
                
            else:
                print(color_text("\n✗ Opción inválida", Fore.RED))
                input("\nPresione ENTER para continuar...")
                
        except ValueError:
            print(color_text("\n✗ Por favor ingrese un número válido", Fore.RED))
            input("\nPresione ENTER para continuar...")
def configure_paths():
    """Configura las rutas de almacenamiento"""
    print_header("Configuración de Rutas de Almacenamiento")
    
    print(color_text("Rutas actuales:", Fore.GREEN))
    exports_path = CONFIG.get("exports_path", "./exports")
    mrcs_path = CONFIG.get("mrcs_path", "./mrcs")
    print(f"1. Ruta de exportación: {exports_path}")
    print(f"2. Ruta de archivos MARC: {mrcs_path}")
    print()
    print("0. Volver")
    print()
    
    option = input(color_text("Seleccione una opción: ", Fore.CYAN))
    
    if option == "1":
        current = exports_path
        new_path = input(color_text(f"Nueva ruta de exportación [{current}]: ", Fore.GREEN))
        
        if new_path.strip():
            # Convertir a ruta absoluta si es necesario
            if not os.path.isabs(new_path):
                print(color_text("Convirtiendo a ruta absoluta...", Fore.YELLOW))
                new_path = os.path.abspath(new_path)
            
            try:
                # Crear directorio si no existe
                os.makedirs(new_path, exist_ok=True)
                
                # Verificar permisos
                test_file = os.path.join(new_path, "test_write_permission.tmp")
                try:
                    with open(test_file, 'w') as f:
                        f.write("test")
                    os.remove(test_file)
                    
                    CONFIG["exports_path"] = new_path
                    save_config(CONFIG)
                    print(color_text(f"\n✓ Ruta de exportación actualizada a: {new_path}", Fore.GREEN))
                except (IOError, PermissionError):
                    print(color_text("\n✗ No hay permisos de escritura en esta ruta", Fore.RED))
            except Exception as e:
                print(color_text(f"\n✗ Error al configurar la ruta: {str(e)}", Fore.RED))
        else:
            print(color_text("\nSe mantuvo la ruta actual", Fore.YELLOW))
    
    elif option == "2":
        current = mrcs_path
        new_path = input(color_text(f"Nueva ruta para archivos MARC [{current}]: ", Fore.GREEN))
        
        if new_path.strip():
            # Convertir a ruta absoluta si es necesario
            if not os.path.isabs(new_path):
                print(color_text("Convirtiendo a ruta absoluta...", Fore.YELLOW))
                new_path = os.path.abspath(new_path)
            
            try:
                # Crear directorio si no existe
                os.makedirs(new_path, exist_ok=True)
                
                # Verificar permisos
                test_file = os.path.join(new_path, "test_write_permission.tmp")
                try:
                    with open(test_file, 'w') as f:
                        f.write("test")
                    os.remove(test_file)
                    
                    CONFIG["mrcs_path"] = new_path
                    save_config(CONFIG)
                    print(color_text(f"\n✓ Ruta de archivos MARC actualizada a: {new_path}", Fore.GREEN))
                except (IOError, PermissionError):
                    print(color_text("\n✗ No hay permisos de escritura en esta ruta", Fore.RED))
            except Exception as e:
                print(color_text(f"\n✗ Error al configurar la ruta: {str(e)}", Fore.RED))
        else:
            print(color_text("\nSe mantuvo la ruta actual", Fore.YELLOW))
    
    input("\nPresione ENTER para continuar...")

def configure_ckan():
    """Configura las opciones de CKAN"""
    print_header("Configuración de CKAN")
    
    print(color_text("Configuración actual:", Fore.GREEN))
    api_key = CONFIG.get("api_key", "")
    if api_key:
        masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else "****"
        print(f"API Key: {masked_key}")
    else:
        print("API Key: No configurada")
    
    print("\n1. Configurar API Key")
    print()
    print("0. Volver")
    print()
    
    option = input(color_text("Seleccione una opción: ", Fore.CYAN))
    
    if option == "1":
        new_api_key = input(color_text("Nueva API Key (deje en blanco para mantener la actual): ", Fore.GREEN))
        
        if new_api_key.strip():
            CONFIG["api_key"] = new_api_key
            save_config(CONFIG)
            print(color_text("\n✓ API Key configurada correctamente", Fore.GREEN))
        else:
            print(color_text("\nSe mantuvo la API Key actual", Fore.YELLOW))
    
    input("\nPresione ENTER para continuar...")

def main_menu():
    """Menú principal de la herramienta de configuración"""
    while True:
        print_current_config()
        
        option = input(color_text("Seleccione una opción: ", Fore.CYAN))
        
        if option == "1":
            configure_performance()
        elif option == "2":
            configure_export_formats()
        elif option == "3":
            configure_paths()
        elif option == "4":
            configure_ckan()
        elif option == "0":
            break
        else:
            print(color_text("\n✗ Opción inválida", Fore.RED))
            input("\nPresione ENTER para continuar...")

if __name__ == "__main__":
    try:
        main_menu()
        print(color_text("\n¡Configuración guardada correctamente!", Fore.GREEN))
    except KeyboardInterrupt:
        print(color_text("\n\nOperación cancelada por el usuario", Fore.YELLOW))
    except Exception as e:
        print(color_text(f"\n\nError inesperado: {str(e)}", Fore.RED))
