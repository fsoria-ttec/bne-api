import platform
from os import system

def ejecutar_comando(comando, ruta="", ruta2=""):
    import os

    if ruta:
        ruta = os.path.normpath(ruta)
    if ruta2:
        ruta2 = os.path.normpath(ruta2)

    match comando:
        case "limpiar":
            if platform.system() == "Windows":
                system("cls")
            else:
                system("clear")
        case "borrar_arc":
            if platform.system() == "Windows":
                system(f"del {ruta}")
            else:
                system(f"rm {ruta}")
        case "borrar_dir":
            if platform.system() == "Windows":
                system(f"rmdir -rf {ruta}")
            else:
                system(f"rm {ruta}")
        case "copiar":
            if platform.system() == "Windows":
                system(f"copy {ruta} {ruta2}")
            else:
                system(f"cp {ruta} {ruta2}")
