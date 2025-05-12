import os
import requests
import musicbrainzngs
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess

musicbrainzngs.set_useragent("FLACNormalizer", "1.0", "tucorreo@ejemplo.com")

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
        result = musicbrainzngs.search_releases(artist=artist, release=album, limit=10)
        for release in result["release-list"]:
            rid = release["id"]
            portada = descargar_portada(rid)
            if portada:
                return portada
    except Exception as e:
        print(f"⚠️ Error buscando portada por tags: {e}")
    return None

def buscar_portada_por_nombre(nombre_archivo):
    try:
        result = musicbrainzngs.search_releases(query=nombre_archivo, limit=10)
        for release in result["release-list"]:
            rid = release["id"]
            portada = descargar_portada(rid)
            if portada:
                return portada
    except Exception as e:
        print(f"⚠️ Error buscando portada por nombre: {e}")
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
    except Exception as e:
        print(f"⚠️ Error buscando género por recording: {e}")
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
    except Exception as e:
        print(f"⚠️ Error buscando género por artista: {e}")
    return None

def procesar_archivo(path):
    try:
        eliminar_id3(path)
        audio = FLAC(path)

        # ---- GÉNERO ----
        if "genre" not in audio:
            artist = audio.get("artist", [None])[0]
            title = audio.get("title", [None])[0]
            if artist and title:
                print(f"🔍 Buscando género: {artist} - {title}")
                genre = obtener_genero_por_recording(artist, title)
                if not genre:
                    print(f"↪️ Probando con artista: {artist}")
                    genre = obtener_genero_por_artista(artist)
                if genre:
                    audio["genre"] = genre
                    print(f"✅ Género añadido: {genre}")
                else:
                    print("🚫 No se encontró género.")
            else:
                print("⚠️ Faltan tags de artista o título para género.")

        # ---- PORTADA ----
        if not tiene_portada(audio):
            artist = audio.get("artist", [None])[0]
            album = audio.get("album", [None])[0]
            base_name = os.path.splitext(os.path.basename(path))[0]

            portada = None
            if artist and album:
                print(f"🖼️ Buscando portada por tags: {artist} - {album}")
                portada = buscar_portada_por_tags(artist, album)
            if not portada:
                print(f"🔄 Reintentando con nombre: {base_name}")
                portada = buscar_portada_por_nombre(base_name)
            if portada:
                incrustar_portada(audio, portada)
                print(f"✅ Portada embebida.")
            else:
                print(f"🚫 No se encontró portada.")

        audio.save()
    except Exception as e:
        print(f"❌ Error procesando {path}: {e}")

def procesar_carpeta(ruta, max_hilos=5):
    archivos = [os.path.join(ruta, f) for f in os.listdir(ruta) if f.lower().endswith(".flac")]
    with ThreadPoolExecutor(max_workers=max_hilos) as executor:
        futures = [executor.submit(procesar_archivo, f) for f in archivos]
        for _ in as_completed(futures):
            pass

# Ejecutar
procesar_carpeta(".", max_hilos=5)
