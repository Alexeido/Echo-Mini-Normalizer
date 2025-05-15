import os
import subprocess
import requests
import musicbrainzngs
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCON, TRCK
from concurrent.futures import ThreadPoolExecutor, as_completed

musicbrainzngs.set_useragent("FLACAutoTagger", "1.0", "tucorreo@ejemplo.com")

def extraer_id3_y_convertir(path):
    try:
        tags = ID3(path)
        audio = FLAC(path)

        # Mapeo de campos ID3 a Vorbis
        if TIT2 in tags:
            audio["title"] = tags[TIT2].text[0]
        if TPE1 in tags:
            audio["artist"] = tags[TPE1].text[0]
        if TALB in tags:
            audio["album"] = tags[TALB].text[0]
        if TRCK in tags:
            audio["tracknumber"] = tags[TRCK].text[0]
        if TCON in tags:
            audio["genre"] = tags[TCON].text[0]

        audio.save()
        print(f"🔁 ID3 → Vorbis transferido: {os.path.basename(path)}")
        return True
    except Exception:
        return False

def eliminar_id3(path):
    try:
        subprocess.run(["metaflac", "--remove", "--block-type=ID3", path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"🧼 ID3 eliminado: {os.path.basename(path)}")
    except Exception as e:
        print(f"⚠️ No se pudo eliminar ID3: {e}")

def tiene_portada(audio):
    return len(audio.pictures) > 0

def descargar_portada(release_id):
    try:
        url = f"https://coverartarchive.org/release/{release_id}/front-500"
        resp = requests.get(url)
        if resp.status_code == 200:
            return resp.content
    except Exception:
        pass
    return None

def buscar_portada_por_tags(artist, album):
    try:
        result = musicbrainzngs.search_releases(artist=artist, release=album, limit=2)
        for release in result["release-list"]:
            portada = descargar_portada(release["id"])
            if portada:
                return portada
    except Exception:
        pass
    return None

def buscar_portada_por_nombre(nombre_archivo):
    try:
        result = musicbrainzngs.search_releases(query=nombre_archivo, limit=2)
        for release in result["release-list"]:
            portada = descargar_portada(release["id"])
            if portada:
                return portada
    except Exception:
        pass
    return None

def incrustar_portada(audio, image_data):
    pic = Picture()
    pic.data = image_data
    pic.type = 3
    pic.mime = "image/jpeg"
    pic.desc = "Cover"
    pic.width = 500
    pic.height = 500
    pic.depth = 24
    audio.add_picture(pic)

def obtener_genero_por_recording(artist, title):
    try:
        result = musicbrainzngs.search_recordings(artist=artist, recording=title, limit=5)
        for recording in result["recording-list"]:
            tags = recording.get("tag-list", [])
            if tags:
                sorted_tags = sorted(tags, key=lambda t: int(t.get("count", 0)), reverse=True)
                return sorted_tags[0]["name"].capitalize()
    except Exception:
        pass
    return None

def obtener_genero_por_artista(artist):
    try:
        result = musicbrainzngs.search_artists(artist=artist, limit=1)
        if not result["artist-list"]:
            return None
        artist_id = result["artist-list"][0]["id"]
        data = musicbrainzngs.get_artist_by_id(artist_id, includes=["tags"])
        tags = data["artist"].get("tag-list", [])
        if tags:
            sorted_tags = sorted(tags, key=lambda t: int(t.get("count", 0)), reverse=True)
            return sorted_tags[0]["name"].capitalize()
    except Exception:
        pass
    return None

def procesar_archivo(path):
    try:
        audio = FLAC(path)

        # 1. Transferir ID3 → Vorbis si hay
        if os.path.getsize(path) > 0 and "ID3" in subprocess.getoutput(f"metaflac --list \"{path}\""):
            if extraer_id3_y_convertir(path):
                eliminar_id3(path)
                audio = FLAC(path)  # Recargar tras guardado

        # 2. Añadir género si falta
        if "genre" not in audio:
            artist = audio.get("artist", [None])[0]
            title = audio.get("title", [None])[0]
            genre = None
            if artist and title:
                genre = obtener_genero_por_recording(artist, title)
                if not genre:
                    genre = obtener_genero_por_artista(artist)
                if genre:
                    audio["genre"] = genre
                    print(f"🎼 Género añadido: {genre}")
                else:
                    print(f"🚫 Sin género: {os.path.basename(path)}")

        # 3. Añadir portada si falta
        if not tiene_portada(audio):
            artist = audio.get("artist", [None])[0]
            album = audio.get("album", [None])[0]
            base = os.path.splitext(os.path.basename(path))[0]
            portada = None
            if artist and album:
                portada = buscar_portada_por_tags(artist, album)
            if not portada:
                portada = buscar_portada_por_nombre(base)
            if portada:
                incrustar_portada(audio, portada)
                print(f"🖼️ Portada añadida: {os.path.basename(path)}")
            else:
                print(f"🚫 Sin portada: {os.path.basename(path)}")

        audio.save()

    except Exception as e:
        print(f"❌ Error en {os.path.basename(path)}: {e}")

def procesar_carpeta(ruta, max_hilos=20):
    archivos = [os.path.join(ruta, f) for f in os.listdir(ruta) if f.lower().endswith(".flac")]
    with ThreadPoolExecutor(max_workers=max_hilos) as executor:
        futures = [executor.submit(procesar_archivo, f) for f in archivos]
        for _ in as_completed(futures):
            pass

# Ejecutar
procesar_carpeta(".", max_hilos=20)
