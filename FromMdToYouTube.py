import os
import sys
import asyncio

# === Variables globales ===
ruta_markdown = None        # Ruta completa del archivo seleccionado
nombre_markdown = None      # Nombre del archivo seleccionado
ruta_audio_largo = None     # Ruta completa del mp3 generado
nombre_audio_largo = None   # Nombre del mp3 generado


# === Funciones auxiliares ===
def borrar_pantalla():
    """Limpia la pantalla en Linux."""
    os.system("clear")

def salir_de_app():
    """Finaliza la aplicación."""
    print("👋 Saliendo de la aplicación...")
    sys.exit(0)

def md_a_texto(md: str) -> str:
    """
    Conversión ligera de Markdown a texto plano para TTS.
    (Sin dependencias; suficiente para casos comunes.)
    """
    import re
    # Quitar bloques de código
    md = re.sub(r"```.*?```", "", md, flags=re.DOTALL)
    # Quitar inline code
    md = re.sub(r"`([^`]+)`", r"\1", md)
    # Encabezados (#, ##, ...)
    md = re.sub(r"^\s{0,3}#{1,6}\s*", "", md, flags=re.MULTILINE)
    # Enlaces [texto](url) -> texto
    md = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", md)
    # Imágenes ![alt](url) -> alt
    md = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", md)
    # Listas y citas
    md = re.sub(r"^\s*([*\-+]\s+|\d+\.\s+|>\s+)", "", md, flags=re.MULTILINE)
    # Énfasis **, __, *, _
    md = re.sub(r"(\*\*|__|\*|_)", "", md)
    # Tablas | --- | -> espacios
    md = re.sub(r"\|", " ", md)
    # Colapsar espacios múltiples
    md = re.sub(r"[ \t]+", " ", md)
    # Normalizar saltos de línea
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()

async def _tts_edge_guardar(texto: str, salida_mp3: str,
                            voz: str = "es-ES-ElviraNeural",
                            rate: str = "+40%"):
    """
    Usa edge-tts para sintetizar 'texto' en 'salida_mp3' con voz y rate dados.
    """
    import edge_tts

    # edge-tts admite textos largos, pero es buena práctica trocear si fuera necesario
    # para evitar limites; aquí troceamos a ~3000 caracteres por seguridad.
    trozo_max = 3000
    fragmentos = []
    inicio = 0
    while inicio < len(texto):
        fin = min(inicio + trozo_max, len(texto))
        fragmentos.append(texto[inicio:fin])
        inicio = fin

    # Guardamos acumulando en un fichero temporal y luego en MP3 final directo
    # Nota: edge-tts permite save() por cada Communicate; concatenar múltiples
    # MP3 no es trivial, así que mandamos el texto completo cuando sea posible.
    # Para garantizar robustez, si hay múltiples fragmentos, los unimos con saltos.
    if len(fragmentos) > 1:
        texto = "\n\n".join(fragmentos)

    communicate = edge_tts.Communicate(texto, voice=voz, rate=rate)
    await communicate.save(salida_mp3)


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

            input("\n🔄 Pulsa ENTER para volver al menú...")
            borrar_pantalla()
            break
        else:
            print("❌ La ruta no es válida o el archivo no es .md. Inténtalo de nuevo.")


def opcion2():
    """
    Transformar en MP3 (es-ES, voz femenina, velocidad x1.40).
    - Requiere haber seleccionado antes un Markdown.
    - Salida: 'L-<nombre_sin_ext>.mp3' en misma carpeta.
    - Guarda en globales: ruta_audio_largo, nombre_audio_largo
    """
    global ruta_markdown, nombre_markdown, ruta_audio_largo, nombre_audio_largo

    print("🎙️ Transformar Markdown en MP3 (es-ES, voz femenina, x1.40)")

    if not (ruta_markdown and nombre_markdown):
        print("⚠️ No se ha seleccionado ningún archivo Markdown todavía (opción 1).")
        input("\nPulsa ENTER para volver al menú...")
        borrar_pantalla()
        return

    # Leer contenido del markdown
    try:
        with open(ruta_markdown, "r", encoding="utf-8") as f:
            contenido_md = f.read()
    except Exception as e:
        print(f"❌ Error leyendo el archivo: {e}")
        input("\nPulsa ENTER para volver al menú...")
        borrar_pantalla()
        return

    texto = md_a_texto(contenido_md)
    if not texto:
        print("⚠️ El Markdown está vacío tras limpiar formato. Nada que locutar.")
        input("\nPulsa ENTER para volver al menú...")
        borrar_pantalla()
        return

    # Preparar ruta de salida
    base_sin_ext, _ = os.path.splitext(nombre_markdown)
    nombre_audio_largo = f"L-{base_sin_ext}.mp3"
    directorio = os.path.dirname(ruta_markdown)
    ruta_audio_largo = os.path.join(directorio, nombre_audio_largo)

    # Sintetizar con edge-tts
    try:
        # Import aquí para poder mostrar aviso de instalación si falta
        import edge_tts  # noqa: F401
    except ImportError:
        print("❌ Falta la dependencia 'edge-tts'.")
        print("   Instálala en tu entorno con: pip install edge-tts")
        input("\nPulsa ENTER para volver al menú...")
        borrar_pantalla()
        return

    try:
        asyncio.run(_tts_edge_guardar(
            texto=texto,
            salida_mp3=ruta_audio_largo,
            voz="es-ES-ElviraNeural",  # voz femenina (neural)
            rate="+40%"                # ~ x1.40 de velocidad
        ))
        print(f"✅ Audio generado: {ruta_audio_largo}")
        print(f"📄 Nombre del audio: {nombre_audio_largo}")
    except Exception as e:
        print(f"❌ Error generando el audio: {e}")

    input("\n🔄 Pulsa ENTER para volver al menú...")
    borrar_pantalla()


def opcion3():
    print("Ejecutando opción 3...")
    input("\nPulsa ENTER para volver al menú...")
    borrar_pantalla()

def opcion4():
    print("Ejecutando opción 4...")
    input("\nPulsa ENTER para volver al menú...")
    borrar_pantalla()

def opcion56():
    print("Ejecutando opción 5 o 6...")
    input("\nPulsa ENTER para volver al menú...")
    borrar_pantalla()

def opcion7():
    print("Ejecutando opción 7...")
    input("\nPulsa ENTER para volver al menú...")
    borrar_pantalla()


# === Menú principal ===
def mostrar_menu():
    print("""
Seleccione una opción:
    1 ==> Seleccionar archivo Markdown
    2 ==> Transformar en MP3 (es-ES, voz femenina, x1.40)
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
