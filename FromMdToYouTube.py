import os
import sys
import asyncio

# === Variables globales ===
ruta_markdown = None        # Ruta completa del archivo seleccionado
nombre_markdown = None      # Nombre del archivo seleccionado
ruta_audio = None     # Ruta completa del mp3 generado
nombre_audio = None   # Nombre del mp3 generado
ruta_imagen  = None   # Ruta completa de la imagen generada
nombre_imagen = None  # Nombre de la imagen generada


# === Funciones auxiliares ===

def borrar_pantalla():
    """Limpia la pantalla en Linux."""
    os.system("clear")

def salir_de_app():
    """Finaliza la aplicación."""
    print("👋 Saliendo de la aplicación...")
    sys.exit(0)

def ir_al_menu(mensaje: str = "\nPulsa ENTER para volver al menú..."):
    """Pausa la ejecución hasta ENTER, limpia pantalla y retorna al menú."""
    input(mensaje)
    borrar_pantalla()
    return

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
                            rate: str = "+30%"):
    """
    Usa edge-tts para sintetizar 'texto' en 'salida_mp3' con voz y rate dados.
    """
    import edge_tts

    # edge-tts admite textos largos, pero es buena práctica trocear si fuera necesario
    # para evitar limites; aquí troceamos a ~10000 caracteres por seguridad.
    trozo_max = 10000
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
    global ruta_markdown, nombre_markdown
    while True:
        ruta = input("Introduce la ruta absoluta del archivo Markdown (.md): ").strip()
        ruta = os.path.abspath(ruta)  # Normalizar
        if os.path.isfile(ruta) and ruta.lower().endswith(".md"):
            ruta_markdown = ruta
            nombre_markdown = os.path.basename(ruta)
            print(f"✅ Archivo seleccionado: {ruta_markdown}")
            print(f"📄 Nombre del archivo: {nombre_markdown}")
            ir_al_menu("\n🔄 Pulsa ENTER para volver al menú...")
            return  # <- importante, corta la función después
        else:
            print("❌ La ruta no es válida o el archivo no es .md. Inténtalo de nuevo.")



# Constantes al inicio

VOZ_TTS = "es-ES-ElviraNeural"
RATE_TTS = "+00%"


def transformar_md_a_mp3():
    """
    Transformar en MP3 (es-ES, voz femenina, velocidad x1.40).
    - Requiere haber seleccionado antes un Markdown.
    - Salida: 'L-<nombre_sin_ext>.mp3' en misma carpeta.
    - Guarda en globales: ruta_audio, nombre_audio
    """
    global ruta_markdown, nombre_markdown, ruta_audio, nombre_audio

    print("🎙️ Transformar Markdown en MP3 (es-ES, voz femenina, x1.00)")

    if not (ruta_markdown and nombre_markdown):
        print("⚠️ No se ha seleccionado ningún archivo Markdown todavía (opción 1).")
        return ir_al_menu()

    try:
        with open(ruta_markdown, "r", encoding="utf-8") as f:
            contenido_md = f.read()
    except Exception as e:
        print(f"❌ Error leyendo el archivo: {e}")
        return ir_al_menu()

    texto = md_a_texto(contenido_md)
    if not texto:
        print("⚠️ El Markdown está vacío tras limpiar formato. Nada que locutar.")
        return ir_al_menu()

    # Preparar ruta de salida
    base_sin_ext, _ = os.path.splitext(nombre_markdown)
    nombre_audio = f"{base_sin_ext}.mp3"
    directorio = os.path.dirname(ruta_markdown)
    ruta_audio = os.path.join(directorio, nombre_audio)

    # Sintetizar con edge-tts
    try:
        # Import aquí para poder mostrar aviso de instalación si falta
        import edge_tts  # noqa: F401
    except ImportError:
        print("❌ Falta la dependencia 'edge-tts'.")
        print("   Instálala en tu entorno con: pip install edge-tts")
        return ir_al_menu()

    try:
        asyncio.run(_tts_edge_guardar(
            texto=texto,
            salida_mp3=ruta_audio,
            voz=VOZ_TTS,
            rate=RATE_TTS
        ))
        print(f"✅ Audio generado: {ruta_audio}")
        print(f"📄 Nombre del audio: {nombre_audio}")
    except Exception as e:
        print(f"❌ Error generando el audio: {e}")
        return ir_al_menu()

    return ir_al_menu()


# === Nueva función: opción 2 ===
def mostrar_markdown_actual():
    """
    Muestra por consola el nombre y la ruta absoluta del archivo Markdown
    actualmente seleccionado. Si no hay ninguno, avisa al usuario.
    """
    global ruta_markdown, nombre_markdown

    # Si no hay ruta, no hay selección
    if not ruta_markdown:
        print("ℹ️  No hay ningún archivo Markdown seleccionado todavía.")
        ir_al_menu()
        return

    # Nombre derivado si no está cacheado
    if not nombre_markdown:
        try:
            import os
            nombre = os.path.basename(ruta_markdown)
        except Exception:
            nombre = "(desconocido)"
    else:
        nombre = nombre_markdown

    print("\n📄 Archivo Markdown seleccionado")
    print(f"   • Nombre: {nombre}")
    print(f"   • Ruta  : {ruta_markdown}")
    return ir_al_menu()


# === Menú principal ===
def mostrar_menu():
    print("""
Seleccione una opción:
    1 ==> Seleccionar archivo MarkDown.
    2 ==> Mostrar archivo MarkDown seleccionado (nombre y ruta).
    3 ==> Transformar en MP3 (es-ES, voz femenina, x1.00).
    4 ==> Sin definir
    5 ==> Sin definir
    6 ==> Sin definir
    7 ==> Sin definir
    8 ==> Salir del programa
""")


def seleccion_menu():
    while True:
        mostrar_menu()
        opcion = input("Opción: ").strip()
        if opcion == "1":
            seleccionar_archivo_markdown()
        if opcion == "2":
            mostrar_markdown_actual()
        elif opcion == "3":
            transformar_md_a_mp3()
        elif opcion == "8":
            salir_de_app()
        else:
            borrar_pantalla()
            print(f"❌ Selección incorrecta: '{opcion}'. Inténtalo de nuevo.")


# === Arranque del programa ===
if __name__ == "__main__":
    try:
        seleccion_menu()
    except KeyboardInterrupt:
        print("\n🛑 Interrumpido por el usuario.")
        salir_de_app()

