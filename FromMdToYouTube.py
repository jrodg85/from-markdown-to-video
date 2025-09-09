import os
import sys

# === Variable global donde se guardará el archivo seleccionado ===
ruta_markdown = None


# === Funciones auxiliares ===
def borrar_pantalla():
    """Limpia la pantalla en Linux."""
    os.system("clear")

def salir_de_app():
    """Finaliza la aplicación."""
    print("👋 Saliendo de la aplicación...")
    sys.exit(0)


# === Funciones de las opciones ===
def seleccionar_archivo_markdown():
    """
    Solicita al usuario una ruta a un archivo .md y valida que exista.
    Guarda la ruta en memoria global (ruta_markdown).
    """
    global ruta_markdown

    while True:
        ruta = input("Introduce la ruta absoluta del archivo Markdown (.md): ").strip()
        ruta = os.path.abspath(ruta)  # Normalizar

        if os.path.isfile(ruta) and ruta.endswith(".md"):
            ruta_markdown = ruta
            print(f"✅ Archivo seleccionado: {ruta_markdown}")
            break
        else:
            print("❌ La ruta no es válida o el archivo no es .md. Inténtalo de nuevo.")


def opcion2():
    print("Ejecutando opción 2...")
    if ruta_markdown:
        print(f"Trabajando con el archivo cargado: {ruta_markdown}")
    else:
        print("⚠️ No se ha seleccionado ningún archivo Markdown todavía.")


def opcion3():
    print("Ejecutando opción 3...")


def opcion4():
    print("Ejecutando opción 4...")


def opcion56():
    print("Ejecutando opción 5 o 6...")


def opcion7():
    print("Ejecutando opción 7...")


# === Menú principal ===
def mostrar_menu():
    print("""
Seleccione una opción:
    1 ==> Seleccionar archivo Markdown
    2 ==> Opción 2
    3 ==> Opción 3
    4 ==> Opción 4
    5 ==> Opción 5
    6 ==> Opción 6
    7 ==> Opción 7
    8 ==> Salir del programa
""")


def seleccion_menu():
    while True:
        mostrar_menu()
        opcion = input("Opción: ").strip()

        if opcion == "1":
            seleccionar_archivo_markdown()
        elif opcion == "2":
            opcion2()
        elif opcion == "3":
            opcion3()
        elif opcion == "4":
            opcion4()
        elif opcion in ("5", "6"):
            opcion56()
        elif opcion == "7":
            opcion7()
        elif opcion == "8":
            salir_de_app()
        else:
            borrar_pantalla()
            print(f"❌ Selección incorrecta: '{opcion}'. Inténtalo de nuevo.")


# === Arranque del programa ===
if __name__ == "__main__":
    seleccion_menu()
