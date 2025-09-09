import os
import sys

# === Variables globales ===
ruta_markdown = None       # Ruta completa del archivo seleccionado
nombre_markdown = None     # Nombre del archivo seleccionado


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
    Guarda la ruta y el nombre del archivo en memoria global.
    """
    global ruta_markdown, nombre_markdown

    while True:
        ruta = input("Introduce la ruta absoluta del archivo Markdown (.md): ").strip()
        ruta = os.path.abspath(ruta)  # Normalizar

        if os.path.isfile(ruta) and ruta.lower().endswith(".md"):
            ruta_markdown = ruta
            nombre_markdown = os.path.basename(ruta)
            print(f"✅ Archivo seleccionado: {ruta_markdown}")
            print(f"📄 Nombre del archivo: {nombre_markdown}")
            
            # Esperar confirmación del usuario antes de limpiar y volver al menú
            input("\n🔄 Pulsa ENTER para volver al menú...")
            borrar_pantalla()
            break
        else:
            print("❌ La ruta no es válida o el archivo no es .md. Inténtalo de nuevo.")


def opcion2():
    print("Ejecutando opción 2...")
    if ruta_markdown and nombre_markdown:
        print(f"Trabajando con el archivo: {nombre_markdown}")
        print(f"Ubicación completa: {ruta_markdown}")
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
