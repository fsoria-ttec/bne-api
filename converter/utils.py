import os
import shutil
import platform

def ejecutar_comando(comando, ruta="", ruta2=""):
    """
    Ejecuta comandos utilizando funciones nativas de Python en lugar de comandos del sistema.
    
    Args:
        comando: Tipo de acción a realizar ('limpiar', 'borrar_arc', 'borrar_dir', 'copiar')
        ruta: Ruta del archivo/directorio principal
        ruta2: Ruta secundaria para operaciones como copiar
    
    Returns:
        bool: True si la operación fue exitosa, False en caso contrario
    """
    try:
        # Normalizar rutas para evitar problemas
        if ruta:
            ruta = os.path.normpath(ruta)
        if ruta2:
            ruta2 = os.path.normpath(ruta2)
        
        if comando == "limpiar":
            # No hay equivalente directo para cls/clear, pero podemos imprimir líneas en blanco
            # o devolver un código especial para que el llamador lo maneje
            print("\n" * 100)  # Imprimir múltiples líneas en blanco
            return True
            
        elif comando == "borrar_arc":
            if os.path.exists(ruta):
                os.remove(ruta)
                return True
            else:
                print(f"Advertencia: El archivo {ruta} no existe")
                return False
                
        elif comando == "borrar_dir":
            if os.path.exists(ruta):
                shutil.rmtree(ruta)
                return True
            else:
                print(f"Advertencia: El directorio {ruta} no existe")
                return False
                
        elif comando == "copiar":
            # Asegurarse de que el directorio destino existe
            dir_destino = os.path.dirname(ruta2)
            if dir_destino and not os.path.exists(dir_destino):
                os.makedirs(dir_destino, exist_ok=True)
            
            # Copiar el archivo
            if os.path.exists(ruta):
                shutil.copy2(ruta, ruta2)
                return True
            else:
                print(f"Advertencia: El archivo origen {ruta} no existe")
                return False
        else:
            print(f"Comando no reconocido: {comando}")
            return False
            
    except Exception as e:
        print(f"Error ejecutando {comando} ({ruta} → {ruta2}): {str(e)}")
        return False
