import os
import sys
import asyncio
from moviepy.editor import AudioFileClip, CompositeAudioClip, ImageClip, CompositeVideoClip, ColorClip
from typing import List, Dict, Tuple
from PIL import Image
import subprocess
import tempfile
import shutil

FFMPEG_BIN = "ffmpeg"  # asume ffmpeg en PATH

# Parche compatibilidad Pillow ≥10

if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# === Variables globales ===

ruta_markdown = None        # Ruta completa del archivo seleccionado.
nombre_markdown = None      # Nombre del archivo seleccionado.
ruta_audio = None           # Ruta completa del mp3 generado.
nombre_audio = None         # Nombre del mp3 generado.
ruta_imagen  = None         # Ruta completa de la imagen seleccionada.
nombre_imagen = None        # Nombre de la imagen seleccionada.
ruta_video = None         # Ruta completa del mp4 generado.
nombre_video = None       # Nombre del mp4 generado.

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



def _archivo_por_defecto(extension: str) -> str | None:
    """
    Devuelve la ruta candidata por defecto:
    - Mismo nombre y ruta que el Markdown seleccionado.
    - Extensión proporcionada (ej. '.png', '.mp3').
    """
    if not ruta_markdown:
        return None
    base = os.path.splitext(ruta_markdown)[0]
    candidato = base + extension
    return candidato if os.path.isfile(candidato) else None


def anadir_archivo(extension: str, descripcion: str):
    """
    Función genérica para añadir un archivo asociado al Markdown actual.
    - Requiere haber seleccionado antes el Markdown.
    - Busca por defecto un archivo con la misma base que el .md y la extensión indicada.
    - Si no se acepta o no existe, permite selección manual.
    - Actualiza variables globales (ruta y nombre) según el tipo de archivo.
    """
    global ruta_markdown, ruta_imagen, nombre_imagen, ruta_audio, nombre_audio

    if not ruta_markdown:
        print("ℹ️ Debes seleccionar antes un archivo Markdown (opción 1).")
        return ir_al_menu()

    ext = extension.lower()

    # 1) Intento con archivo por defecto
    candidata = _archivo_por_defecto(ext)
    if candidata:
        print(f"🔎 {descripcion} por defecto encontrado:\n   {candidata}")
        if _pregunta_si_no(f"¿Quieres usar este {descripcion.lower()}?"):
            if ext == ".png":
                ruta_imagen = candidata
                nombre_imagen = os.path.basename(candidata)
            elif ext == ".mp3":
                ruta_audio = candidata
                nombre_audio = os.path.basename(candidata)
            print(f"✅ {descripcion} seleccionado: {candidata}")
            return ir_al_menu("\n🔄 Pulsa ENTER para volver al menú...")
        else:
            print(f"ℹ️ Has rechazado el {descripcion.lower()} por defecto. Vamos a seleccionar uno manualmente.")

    # 2) Selección manual
    while True:
        ruta = input(f"Introduce la ruta absoluta del {descripcion} ({extension}): ").strip()
        ruta = os.path.abspath(ruta)
        if os.path.isfile(ruta) and ruta.lower().endswith(ext):
            if ext == ".png":
                ruta_imagen, nombre_imagen = ruta, os.path.basename(ruta)
            elif ext == ".mp3":
                ruta_audio,  nombre_audio  = ruta, os.path.basename(ruta)
            print(f"✅ {descripcion} seleccionado: {ruta}")
            return ir_al_menu("\n🔄 Pulsa ENTER para volver al menú...")
        else:
            print(f"❌ La ruta no es válida o el archivo no es {extension}. "
                  "Inténtalo de nuevo (Ctrl+C para cancelar).")

def _pregunta_si_no(pregunta: str) -> bool:
    """
    Pregunta cerrada S/Si/s/si o N/No/n/no hasta que el usuario responda correctamente.
    Devuelve True para Sí, False para No.
    """
    while True:
        resp = input(f"{pregunta} [S/N]: ").strip()
        if resp in ("S", "SI", "s", "si"):
            return True
        if resp in ("N", "NO", "n", "no"):
            return False
        print("⚠️ Respuesta no válida. Debes contestar S/SI/s/si o N/NO/n/no.")

def _info_archivo(ruta: str | None, esperado_ext: str) -> tuple[bool, str, str, str]:
    """
    Devuelve (existe, dir, base_sin_ext, nombre_archivo) para una ruta dada.
    Si ruta es None o no existe o la extensión no coincide, 'existe' será False.
    """
    if not ruta:
        return False, "", "", ""
    ruta_abs = os.path.abspath(ruta)
    existe = os.path.isfile(ruta_abs) and ruta_abs.lower().endswith(esperado_ext.lower())
    if not existe:
        return False, "", "", os.path.basename(ruta_abs)
    directorio = os.path.dirname(ruta_abs)
    nombre = os.path.basename(ruta_abs)
    base, _ = os.path.splitext(nombre)
    return True, directorio, base, nombre


def _print_linea_estado(titulo: str, existe: bool, nombre: str, ruta: str | None):
    estado = "✅" if existe else "❌"
    if ruta:
        print(f"  {estado} {titulo:<10} | {nombre or '(sin nombre)'}")
        print(f"     ↳ {ruta}")
    else:
        print(f"  ❌ {titulo:<10} | (no seleccionado)")

def seleccionar_directorio(prompt: str = "Introduce la ruta absoluta de la carpeta con Markdown: ") -> str | None:
    """
    Pide un directorio válido al usuario. Devuelve la ruta absoluta o None si no es válido.
    """
    ruta = input(prompt).strip()
    ruta = os.path.abspath(ruta)
    if os.path.isdir(ruta):
        return ruta
    print("❌ La ruta no es un directorio válido.")
    return None

def _listar_markdown_en_directorio(dirpath: str) -> list[str]:
    """
    Devuelve una lista de rutas absolutas a archivos .md dentro del directorio (no recursivo).
    """
    try:
        nombres = os.listdir(dirpath)
    except Exception as e:
        print(f"❌ No se pudo leer el directorio: {e}")
        return []

    rutas = []
    for nombre in sorted(nombres):
        ruta = os.path.join(dirpath, nombre)
        if os.path.isfile(ruta) and nombre.lower().endswith(".md"):
            rutas.append(os.path.abspath(ruta))
    return rutas

def _generar_mp3_para_markdown(ruta_md: str, voice: str, rate: str, sobrescribir: bool = False) -> tuple[bool, str]:
    """
    Genera el MP3 para un archivo Markdown dado.
    - Limpia el MD con md_a_texto().
    - Crea <base>.mp3 en el mismo directorio.
    - Respeta 'sobrescribir=False' para saltar si el MP3 ya existe.
    Devuelve (exito, ruta_mp3).
    """
    try:
        with open(ruta_md, "r", encoding="utf-8") as f:
            contenido_md = f.read()
    except Exception as e:
        print(f"   ❌ [{os.path.basename(ruta_md)}] Error leyendo MD: {e}")
        return False, ""

    texto = md_a_texto(contenido_md)
    if not texto:
        print(f"   ⚠️ [{os.path.basename(ruta_md)}] Tras limpiar, el texto está vacío. Se omite.")
        return False, ""

    base_sin_ext, _ = os.path.splitext(os.path.basename(ruta_md))
    dir_md = os.path.dirname(ruta_md)
    nombre_audio = f"{base_sin_ext}.mp3"
    ruta_mp3 = os.path.join(dir_md, nombre_audio)

    if os.path.exists(ruta_mp3) and not sobrescribir:
        print(f"   ⏭️ [{base_sin_ext}] MP3 ya existe. Saltando (usa sobrescribir=True para regenerar).")
        return True, ruta_mp3

    try:
        # Probamos import aquí para fallar pronto si falta la dependencia
        import edge_tts  # noqa: F401
    except ImportError:
        print("❌ Falta la dependencia 'edge-tts'. Instálala con: pip install edge-tts")
        return False, ""

    try:
        asyncio.run(_tts_edge_guardar(
            texto=texto,
            salida_mp3=ruta_mp3,
            voz=voice,
            rate=rate
        ))
        print(f"   ✅ [{base_sin_ext}] MP3 generado: {ruta_mp3}")
        return True, ruta_mp3
    except Exception as e:
        print(f"   ❌ [{base_sin_ext}] Error generando audio: {e}")
        return False, ""

def _ruta_salida_video() -> tuple[str, str]:
    """
    Devuelve (ruta_salida_video, nombre_video) usando el mismo directorio
    y nombre base que el Markdown seleccionado, con extensión .mp4.
    """
    base = "salida"
    directorio = "."
    if ruta_markdown:
        directorio = os.path.dirname(ruta_markdown)
        base = os.path.splitext(os.path.basename(ruta_markdown))[0]
    nombre = f"{base}.mp4"
    return os.path.join(directorio, nombre), nombre

def _nombre_base(path: str) -> str:
    """Devuelve el nombre base sin extensión."""
    return os.path.splitext(os.path.basename(path))[0]

def _coinciden_en_misma_carpeta(md: str, png: str, mp3: str) -> bool:
    """Verifica que los 3 archivos estén en la misma carpeta y compartan nombre base."""
    if not (md and png and mp3):
        return False
    d_md, d_png, d_mp3 = os.path.dirname(md), os.path.dirname(png), os.path.dirname(mp3)
    if not (d_md == d_png == d_mp3):
        return False
    b_md, b_png, b_mp3 = _nombre_base(md), _nombre_base(png), _nombre_base(mp3)
    return b_md == b_png == b_mp3

def _buscar_tripletas_en_carpeta(carpeta: str) -> Tuple[List[Dict], List[str], List[str]]:
    """
    Recorre 'carpeta' y construye tríos (md, png, mp3) por nombre base.
    Devuelve: (validas, faltan_png, faltan_mp3)
    - validas: lista de dicts {'base','md','png','mp3','salida_mp4'}
    - faltan_png/mp3: lista de rutas md que no tienen su png/mp3 correspondiente
    """
    if not os.path.isdir(carpeta):
        raise ValueError(f"No es una carpeta válida: {carpeta}")

    archivos = os.listdir(carpeta)
    bases_md = [os.path.splitext(f)[0] for f in archivos if f.lower().endswith(".md")]

    validas: List[Dict] = []
    faltan_png: List[str] = []
    faltan_mp3: List[str] = []

    for base in sorted(set(bases_md)):
        md = os.path.join(carpeta, f"{base}.md")
        png = os.path.join(carpeta, f"{base}.png")
        mp3 = os.path.join(carpeta, f"{base}.mp3")

        tiene_png = os.path.isfile(png)
        tiene_mp3 = os.path.isfile(mp3)

        if tiene_png and tiene_mp3 and _coinciden_en_misma_carpeta(md, png, mp3):
            salida_mp4 = os.path.join(carpeta, f"{base}.mp4")
            validas.append({"base": base, "md": md, "png": png, "mp3": mp3, "salida_mp4": salida_mp4})
        else:
            if not tiene_png:
                faltan_png.append(md)
            if not tiene_mp3:
                faltan_mp3.append(md)

    return validas, faltan_png, faltan_mp3

def _generar_video_desde_recursos(ruta_png: str, ruta_mp3: str, salida_mp4: str) -> None:
    """
    Genera un vídeo MP4 con la misma puesta en escena que la opción 8:
      - 0.0s → pantalla negra
      - 1.0s → aparece imagen con fade-in 0.5s y comienza el audio
      - (fin audio) + 1.0s → fade-out de imagen 0.5s y termina el vídeo
    """
    # Import local para no romper otros flujos si falta moviepy en el entorno
    from moviepy.editor import AudioFileClip, ImageClip, CompositeVideoClip, ColorClip

    # Cargar recursos
    audio = AudioFileClip(ruta_mp3)
    dur_audio = audio.duration

    # Timings
    t0_negro = 0.0
    t_audio_start = 1.0
    fade_in = 0.5
    fade_out = 0.5
    cola_final = 1.0

    dur_total = t_audio_start + dur_audio + cola_final  # vídeo total

    # Clips
    fondo = ColorClip(size=(1920, 1080), color=(0, 0, 0), duration=dur_total)

    img = (ImageClip(ruta_png)
           .set_duration(dur_total - t_audio_start)  # visible desde que aparece hasta el final
           .set_start(t_audio_start)
           .resize(height=1080)  # encajar alto; si quieres 'contain' o 'cover', ajusta aquí
           .fx(lambda clip: clip.crossfadein(fade_in))
           )

    # Fade-out al final de la imagen
    img = img.fx(lambda clip: clip.crossfadeout(fade_out))

    # Audio empieza en 1s
    audio = audio.set_start(t_audio_start)

    video = CompositeVideoClip([fondo, img], size=(1920, 1080))
    video = video.set_audio(audio)

    # Exportar
    video.write_videofile(
        salida_mp4,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=0
    )

def _run_ffmpeg(cmd: list[str]) -> bool:
    """Ejecuta ffmpeg y devuelve True si sale con código 0."""
    try:
        res = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return res.returncode == 0
    except Exception as e:
        print("❌ ffmpeg falló:", e)
        return False

def _check_ffmpeg() -> bool:
    """Comprueba si ffmpeg está disponible."""
    try:
        subprocess.run([FFMPEG_BIN, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        print("❌ No se encontró 'ffmpeg'. Instálalo (ej. sudo apt install ffmpeg).")
        return False

def _generar_video_hibrido(ruta_png: str, ruta_mp3: str, salida_mp4: str,
                           fps: int = 12, size: tuple[int,int] = (1920,1080)) -> None:
    """
    Genera un video híbrido:
      - MoviePy: fade-in 0.5s y fade-out 0.5s (video-only)
      - FFmpeg : tramo largo de imagen fija + negros (video-only) y mux de audio con offset 1.0s
    Requiere ffmpeg instalado.
    """
    if not _check_ffmpeg():
        # Fallback limpio a tu versión previa (todo MoviePy) si no hay ffmpeg
        print("ℹ️ Sin ffmpeg → usando render completo con MoviePy.")
        return _generar_video_desde_recursos(ruta_png, ruta_mp3, salida_mp4)

    from moviepy.editor import ImageClip, ColorClip, CompositeVideoClip, AudioFileClip

    # Duraciones base (leemos audio para calcular longitudes)
    audio = AudioFileClip(ruta_mp3)
    dur_audio = float(audio.duration)
    audio.close()

    # Parámetros del timeline
    t_preroll_negro = 1.0
    t_fade = 0.5
    t_postroll_negro = 1.0

    # Duración visible total de la imagen = audio + 2.0s (como tu opción 8)
    dur_imagen_total = dur_audio + 2.0
    # Tramo central sin fades:
    dur_tramo_central = max(0.0, dur_imagen_total - 2 * t_fade)  # = dur_audio + 1.0

    W, H = size
    tmpdir = tempfile.mkdtemp(prefix="vidhybrid_")
    try:
        seg0 = os.path.join(tmpdir, "seg0_black.mp4")
        seg1 = os.path.join(tmpdir, "seg1_fadein.mp4")
        seg2 = os.path.join(tmpdir, "seg2_static.mp4")
        seg3 = os.path.join(tmpdir, "seg3_fadeout.mp4")
        seg4 = os.path.join(tmpdir, "seg4_black.mp4")
        concat_list = os.path.join(tmpdir, "files.txt")
        video_concat = os.path.join(tmpdir, "video_concat.mp4")
        video_with_audio = os.path.join(tmpdir, "video_audio.mp4")

        # === SEG0: Negro preroll (ffmpeg color source) ===
        ok = _run_ffmpeg([
            FFMPEG_BIN, "-y",
            "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={fps}",
            "-t", f"{t_preroll_negro}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
            seg0
        ])
        if not ok: raise RuntimeError("No se pudo crear seg0 (negro).")

        # === SEG1: Fade-in 0.5s con MoviePy ===
        # Fondo negro + imagen con fadein, centrada y encajada a H
        fondo = ColorClip(size=(W, H), color=(0, 0, 0), duration=t_fade)
        img = (ImageClip(ruta_png)
               .resize(height=H)
               .set_position("center")
               .set_duration(t_fade)
               .fadein(t_fade))
        clip1 = CompositeVideoClip([fondo, img], size=(W, H)).set_duration(t_fade)
        clip1.write_videofile(seg1, fps=fps, codec="libx264", audio=False,
                              preset="ultrafast", threads=0, verbose=False, logger=None)

        # === SEG2: Tramo central estático (ffmpeg, rápido) ===
        # Montamos la imagen con letterbox centrado mediante filtros
        # - scale con aspect ratio
        # - pad para rellenar a 1920x1080
        if dur_tramo_central > 0:
            ok = _run_ffmpeg([
                FFMPEG_BIN, "-y",
                "-loop", "1", "-i", ruta_png,
                "-t", f"{dur_tramo_central}",
                "-vf", f"scale=-2:{H}:force_original_aspect_ratio=decrease,"
                       f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,fps={fps}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
                seg2
            ])
            if not ok: raise RuntimeError("No se pudo crear seg2 (estático).")
        else:
            # Crea un dummy de 1 frame para no romper el concat
            ok = _run_ffmpeg([
                FFMPEG_BIN, "-y",
                "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={fps}",
                "-t", "0.001",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
                seg2
            ])
            if not ok: raise RuntimeError("No se pudo crear seg2 (dummy).")

        # === SEG3: Fade-out 0.5s con MoviePy ===
        fondo = ColorClip(size=(W, H), color=(0, 0, 0), duration=t_fade)
        img = (ImageClip(ruta_png)
               .resize(height=H)
               .set_position("center")
               .set_duration(t_fade)
               .fadeout(t_fade))
        # Empezamos opaco y caemos a negro
        clip3 = CompositeVideoClip([fondo, img.set_opacity(1.0)], size=(W, H)).set_duration(t_fade)
        clip3.write_videofile(seg3, fps=fps, codec="libx264", audio=False,
                              preset="ultrafast", threads=0, verbose=False, logger=None)

        # === SEG4: Negro postroll ===
        ok = _run_ffmpeg([
            FFMPEG_BIN, "-y",
            "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={fps}",
            "-t", f"{t_postroll_negro}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
            seg4
        ])
        if not ok: raise RuntimeError("No se pudo crear seg4 (negro final).")

        # === Concat de los 5 segmentos (video-only) ===
        with open(concat_list, "w", encoding="utf-8") as f:
            for p in (seg0, seg1, seg2, seg3, seg4):
                f.write(f"file '{p}'\n")

        ok = _run_ffmpeg([
            FFMPEG_BIN, "-y",
            "-f", "concat", "-safe", "0", "-i", concat_list,
            "-c", "copy",
            video_concat
        ])
        if not ok: raise RuntimeError("Fallo al concatenar segmentos de vídeo.")

        # === Mux de audio con offset 1.0s, sin recomprimir video ===
        # -itsoffset 1.0 aplica retardo de inicio al audio
        ok = _run_ffmpeg([
            FFMPEG_BIN, "-y",
            "-itsoffset", "1.0", "-i", ruta_mp3,
            "-i", video_concat,
            "-map", "1:v:0", "-map", "0:a:0",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",    # corta si el audio acaba antes (aquí no debería)
            video_with_audio
        ])
        if not ok: raise RuntimeError("Fallo al multiplexar audio con vídeo.")

        # Mover resultado final
        shutil.move(video_with_audio, salida_mp4)
        print(f"   ✔️ OK (híbrido): {salida_mp4}")

    finally:
        # Limpieza temporal
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass



# === Funciones de las opciones ===

# === Nueva función: opción 1 ===

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

# === Nueva función: opción 3 ===

# Constantes al inicio

VOZ_TTS = "es-ES-ElviraNeural"
RATE_TTS = "+00%"

def transformar_md_a_mp3() -> tuple[str | None, str | None]:
    """
    Transformar en MP3 (es-ES, voz femenina, velocidad x1.00).
    - Requiere haber seleccionado antes un Markdown.
    - Salida: '<nombre_sin_ext>.mp3' en la misma carpeta.
    - Devuelve (ruta_audio_generado, nombre_audio_generado) o (None, None) si falla.
    - Sincroniza las variables globales ruta_audio/nombre_audio con el archivo generado.
    """
    global ruta_markdown, nombre_markdown, ruta_audio, nombre_audio

    print("🎙️ Transformar Markdown en MP3 (es-ES, voz femenina, x1.00)")

    if not (ruta_markdown and nombre_markdown):
        print("⚠️ No se ha seleccionado ningún archivo Markdown todavía (opción 1).")
        ir_al_menu()
        return None, None

    try:
        with open(ruta_markdown, "r", encoding="utf-8") as f:
            contenido_md = f.read()
    except Exception as e:
        print(f"❌ Error leyendo el archivo: {e}")
        ir_al_menu()
        return None, None

    texto = md_a_texto(contenido_md)
    if not texto:
        print("⚠️ El Markdown está vacío tras limpiar formato. Nada que locutar.")
        ir_al_menu()
        return None, None

    # Preparar ruta de salida
    base_sin_ext, _ = os.path.splitext(nombre_markdown)
    nombre_audio_generado = f"{base_sin_ext}.mp3"
    directorio = os.path.dirname(ruta_markdown)
    ruta_audio_generado = os.path.join(directorio, nombre_audio_generado)

    try:
        import edge_tts
    except ImportError:
        print("❌ Falta la dependencia 'edge-tts'.")
        print("   Instálala en tu entorno con: pip install edge-tts")
        ir_al_menu()
        return None, None

    try:
        asyncio.run(_tts_edge_guardar(
            texto=texto,
            salida_mp3=ruta_audio_generado,
            voz=VOZ_TTS,
            rate=RATE_TTS
        ))
        print(f"✅ Audio generado: {ruta_audio_generado}")
        print(f"📄 Nombre del audio: {nombre_audio_generado}")

        # === Sincronizar estado global del "audio actual" ===
        ruta_audio, nombre_audio = ruta_audio_generado, nombre_audio_generado

    except Exception as e:
        print(f"❌ Error generando el audio: {e}")
        ir_al_menu()
        return None, None

    ir_al_menu()
    return ruta_audio_generado, nombre_audio_generado

# === Nueva función: opción 4 ===

def generar_mp3_para_carpeta():
    """
    Opción 7: Genera audios MP3 para TODOS los .md de una carpeta (no recursivo).
    - Usa la voz y rate globales (VOZ_TTS, RATE_TTS).
    - Por defecto NO sobrescribe MP3 existentes (pregunta al usuario).
    - Muestra un resumen final con conteos.
    """
    global VOZ_TTS, RATE_TTS

    print("\n📚 Generar MP3 para todos los Markdown de una carpeta")
    print("────────────────────────────────────────────────────")

    carpeta = seleccionar_directorio()
    if not carpeta:
        return ir_al_menu()

    # ¿Sobrescribir archivos existentes?
    sobrescribir = _pregunta_si_no("¿Quieres sobrescribir MP3 existentes si ya están creados?")

    # Listado de .md
    markdowns = _listar_markdown_en_directorio(carpeta)
    if not markdowns:
        print("ℹ️ No se encontraron archivos .md en la carpeta indicada.")
        return ir_al_menu()

    print(f"\n🔎 Se procesarán {len(markdowns)} archivos .md en: {carpeta}\n")

    total = len(markdowns)
    ok = 0
    fallos = 0
    generados = 0
    saltados = 0

    for ruta_md in markdowns:
        antes = os.path.exists(os.path.splitext(ruta_md)[0] + ".mp3")
        exito, ruta_mp3 = _generar_mp3_para_markdown(ruta_md, VOZ_TTS, RATE_TTS, sobrescribir=sobrescribir)
        if exito:
            ok += 1
            despues = os.path.exists(ruta_mp3)
            if (not antes) and despues:
                generados += 1
            if antes and not sobrescribir:
                saltados += 1
        else:
            fallos += 1

    print("\n📊 Resumen")
    print("──────────")
    print(f"   🧾 Total .md:       {total}")
    print(f"   ✅ Correctos:       {ok}")
    print(f"   🎧 Generados:       {generados}")
    print(f"   ⏭️  Saltados:        {saltados}")
    print(f"   ❌ Fallos:          {fallos}")
    print(f"\nVoz usada: {VOZ_TTS} | Velocidad: {RATE_TTS}")

    return ir_al_menu()

# === Nueva función: opción 5 ===

def anadir_imagen_png():
    """Opción 4: Añadir imagen PNG"""
    anadir_archivo(".png", "Imagen (PNG)")

# === Nueva función: opción 6 ===

def anadir_audio_mp3():
    """Opción 5: Añadir audio MP3"""
    anadir_archivo(".mp3", "Audio (MP3)")

# === Nueva función: opción 7 ===

def mostrar_estado_proyecto():
    """
    Opción 6: Muestra el estado del Markdown, PNG y MP3.
    Verifica:
      - Que existen físicamente.
      - Que están en la MISMA carpeta.
      - Que comparten el MISMO nombre base (sin extensión) que el Markdown.
    """
    global ruta_markdown, nombre_markdown, ruta_imagen, nombre_imagen, ruta_audio, nombre_audio

    print("\n📦 Estado del proyecto")
    print("──────────────────────")

    # Recolectar info
    md_ok,  md_dir,  md_base,  md_nombre   = _info_archivo(ruta_markdown, ".md")
    png_ok, png_dir, png_base, png_nombre  = _info_archivo(ruta_imagen,   ".png")
    mp3_ok, mp3_dir, mp3_base, mp3_nombre  = _info_archivo(ruta_audio,    ".mp3")

    # Mostrar líneas
    _print_linea_estado("Markdown", md_ok,  md_nombre,  ruta_markdown)
    _print_linea_estado("Imagen",   png_ok, png_nombre, ruta_imagen)
    _print_linea_estado("Audio",    mp3_ok, mp3_nombre, ruta_audio)

    print("\n🔎 Verificaciones")
    print("─────────────────")

    # 1) Verificar que el Markdown existe (si no, el resto no tiene sentido de “coincidir con el md”)
    if not md_ok:
        print("❌ No hay Markdown válido seleccionado o el archivo no existe. "
              "Selecciona un .md (opción 1) y vuelve a intentarlo.")
        return ir_al_menu()

    # 2) Directorios (solo comprobamos para los que existan)
    dir_ok = True
    detalles_dir = []
    for label, ok, d in (("PNG", png_ok, png_dir), ("MP3", mp3_ok, mp3_dir)):
        if ok and d != md_dir:
            dir_ok = False
            detalles_dir.append(f"{label} → {d}")

    if dir_ok:
        print(f"✅ Mismo directorio para todos los archivos existentes: {md_dir}")
    else:
        print("❌ Directorios distintos detectados respecto al Markdown:")
        print(f"   MD  → {md_dir}")
        for det in detalles_dir:
            print(f"   {det}")

    # 3) Nombre base (solo comparamos los que existan)
    base_ok = True
    detalles_base = []
    for label, ok, b in (("PNG", png_ok, png_base), ("MP3", mp3_ok, mp3_base)):
        if ok and b != md_base:
            base_ok = False
            detalles_base.append(f"{label} → {b}")

    if base_ok:
        print(f"✅ Mismo nombre base para todos los archivos existentes: {md_base}")
    else:
        print("❌ Nombres base distintos respecto al Markdown:")
        print(f"   MD  → {md_base}")
        for det in detalles_base:
            print(f"   {det}")

    # 4) Resumen final
    todo_ok = md_ok and (not png_ok or (png_ok and dir_ok and base_ok)) and (not mp3_ok or (mp3_ok and dir_ok and base_ok))
    if todo_ok:
        print("\n🎉 Estado consistente: los archivos existentes comparten carpeta y nombre base con el Markdown.")
    else:
        print("\n⚠️ Estado inconsistente: ajusta nombres o mueve archivos para alinearlos con el Markdown.")

    return ir_al_menu()

# === Nueva función: opción 8 ===

def generar_video():
    """
    Opción 8: Genera un video con el PNG y el MP3 seleccionados.
    Timeline:
      - 0.0s → pantalla negra
      - 1.0s → aparece imagen con fade-in 0.5s y comienza el audio
      - (fin audio) + 1.0s → fade-out de imagen 0.5s
      - (fin audio) + 2.0s → corte final (1s negro extra)
    """
    global ruta_audio, ruta_imagen, ruta_markdown, nombre_markdown, ruta_video, nombre_video

    if not (ruta_audio and os.path.isfile(ruta_audio)):
        print("❌ Falta el audio MP3 (opción 6).")
        return ir_al_menu()
    if not (ruta_imagen and os.path.isfile(ruta_imagen)):
        print("❌ Falta la imagen PNG (opción 5).")
        return ir_al_menu()

    try:
        # Cargar recursos
        audio_clip = AudioFileClip(ruta_audio)
        dur_audio = audio_clip.duration

        # Duración total del timeline: 1s negro + audio + 2s negros extra
        dur_total = dur_audio + 3.0

        # Imagen: aparece en t=1.0 y dura audio + 2s
        img_clip = (
            ImageClip(ruta_imagen)
            .set_start(1.0)
            .set_duration(dur_audio + 2.0)
            .fadein(0.5)
            .fadeout(0.5)
        )

        # Fondo negro que cubre todo el timeline
        fondo = ColorClip(size=img_clip.size, color=(0, 0, 0), duration=dur_total)

        # Audio desplazado 1s usando CompositeAudioClip (respeta offsets)
        audio_offset = CompositeAudioClip([audio_clip.set_start(1.0)])

        # Composición de video + audio
        video = CompositeVideoClip([fondo, img_clip], size=img_clip.size, bg_color=(0, 0, 0))
        video = video.set_audio(audio_offset).set_duration(dur_total)

        # Salida: mismo nombre base que el Markdown
        salida, nombre = _ruta_salida_video()
        ruta_video, nombre_video = salida, nombre

        print(f"🎬 Generando video: {salida}")
        video.write_videofile(salida, fps=24, codec="libx264", audio_codec="aac")
        print("✅ Video generado correctamente.")

    except ImportError:
        print("❌ Falta 'moviepy'. Instálala con: pip install moviepy")
        print("   (Opcional recomendado: pip install imageio[ffmpeg])")
    except Exception as e:
        print(f"❌ Error generando el video: {e}")
    finally:
        try:
            audio_clip.close()
        except Exception:
            pass

    return ir_al_menu()

# === Nueva función: opción 9 ===


def generar_videos_para_carpeta():
    """
    Opción 9: Genera vídeos MP4 para TODOS los .md de una carpeta
    que tengan su .png y .mp3 con el mismo nombre y en la misma ruta.
    Usa el modo híbrido (fades cortos con MoviePy + tramo central con FFmpeg).
    """
    # Si hay un markdown seleccionado, sugerimos su carpeta
    sugerida = os.path.dirname(ruta_markdown) if ruta_markdown else ""
    carpeta = input(f"Ruta de carpeta (ENTER para usar '{sugerida}'): ").strip() or sugerida

    if not carpeta:
        print("❌ No se especificó carpeta y no hay Markdown seleccionado.")
        return ir_al_menu()

    if not os.path.isdir(carpeta):
        print(f"❌ La ruta no es una carpeta válida: {carpeta}")
        return ir_al_menu()

    try:
        validas, faltan_png, faltan_mp3 = _buscar_tripletas_en_carpeta(carpeta)
    except Exception as e:
        print(f"❌ Error listando carpeta: {e}")
        return ir_al_menu()

    if not validas and not (faltan_png or faltan_mp3):
        print("ℹ️ No se encontraron archivos .md en la carpeta.")
        return ir_al_menu()

    # Reportes de faltantes
    if faltan_png:
        print("\n⚠️ Faltan PNG para los siguientes Markdown:")
        for md in faltan_png:
            print("   -", md)

    if faltan_mp3:
        print("\n⚠️ Faltan MP3 para los siguientes Markdown:")
        for md in faltan_mp3:
            print("   -", md)

    if not validas:
        print("\n❌ No hay tríos completos (md+png+mp3) para generar vídeos.")
        return ir_al_menu()

    print(f"\n✅ Se generarán vídeos (modo híbrido) para {len(validas)} archivo(s):")
    exitos = 0
    fallos = 0

    for item in validas:
        base = item["base"]
        png = item["png"]
        mp3 = item["mp3"]
        salida = item["salida_mp4"]

        print(f"\n→ Generando '{base}.mp4' ...")
        try:
            _generar_video_hibrido(png, mp3, salida, fps=12, size=(1920, 1080))
            print(f"   ✔️ OK: {salida}")
            exitos += 1
        except Exception as e:
            print(f"   ❌ Falló '{base}': {e}")
            fallos += 1

    print("\n=== Resumen ===")
    print(f"   Generados correctamente: {exitos}")
    print(f"   Fallidos: {fallos}")
    return ir_al_menu()



# === Menú principal ===

def mostrar_menu():
    print("""
Seleccione una opción:
     1 ==> Seleccionar archivo MarkDown.
     2 ==> Mostrar archivo MarkDown seleccionado (nombre y ruta).
     3 ==> Transformar en MP3 (es-ES, voz femenina, x1.00).
     4 ==> Generar MP3 para TODOS los .md de una carpeta.
     5 ==> Añadir imagen (PNG).
     6 ==> Añadir audio (MP3).
     7 ==> Mostrar estado (MD/PNG/MP3).
     8 ==> Generar vídeo con el PNG/MP3 seleccionados.
     9 ==> Generar VÍDEOS en lote (modo híbrido con FFmpeg).
    00 ==> Salir del programa
""")

ACCIONES = {
    "1": seleccionar_archivo_markdown,
    "2": mostrar_markdown_actual,
    "3": transformar_md_a_mp3,
    "4": generar_mp3_para_carpeta,
    "5": anadir_imagen_png,
    "6": anadir_audio_mp3,
    "7": mostrar_estado_proyecto,
    "8": generar_video,
    "9": generar_videos_para_carpeta,   # NUEVA opción 9
    "00": salir_de_app,
}

def seleccion_menu():
    while True:
        mostrar_menu()
        accion = ACCIONES.get(input("Opción: ").strip())
        if accion:
            accion()
        else:
            borrar_pantalla()
            print("❌ Selección incorrecta. Inténtalo de nuevo.")

# === Arranque del programa ===

if __name__ == "__main__":
    try:
        seleccion_menu()
    except KeyboardInterrupt:
        print("\n🛑 Interrumpido por el usuario.")
        salir_de_app()

