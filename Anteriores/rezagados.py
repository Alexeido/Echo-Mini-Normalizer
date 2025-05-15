import os
import requests
import musicbrainzngs
from mutagen.flac import FLAC, Picture
from concurrent.futures import ThreadPoolExecutor, as_completed

musicbrainzngs.set_useragent("FLACMetadataCompleter", "1.0", "tucorreo@ejemplo.com")

def extraer_grupo_y_titulo(nombre_archivo):
    base = os.path.splitext(nombre_archivo)[0]
    if " - " in base:
        partes = base.split(" - ", 1)
        return partes[0].strip(), partes[1].strip()
    return None, None

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

def buscar_info_por_recording(artist, title):
    try:
        result = musicbrainzngs.search_recordings(artist=artist, recording=title, limit=5)
        for rec in result["recording-list"]:
            release_list = rec.get("release-list", [])
            if release_list:
                release = release_list[0]
                release_id = release.get("id")
                return {
                    "artist": rec.get("artist-credit", [{}])[0].get("name"),
                    "title": rec.get("title"),
                    "album": release.get("title"),
                    "release_id": release_id
                }
    except Exception:
        pass
    return None

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
        nombre_archivo = os.path.basename(path)

        artist = audio.get("artist", [None])[0]
        title = audio.get("title", [None])[0]

        # Si no hay tags, los intentamos extraer del nombre del archivo
        if not artist or not title:
            artist, title = extraer_grupo_y_titulo(nombre_archivo)

        if not artist or not title:
            print(f"❌ No se puede procesar (falta artista o título): {nombre_archivo}")
            return
        
        # Si tiene album nos retiramos de buscarlo
        if album := audio.get("album", [None])[0]:
            return

        print(f"\n🎵 Completando: {artist} - {title}")

        # Buscar datos desde MusicBrainz
        info = buscar_info_por_recording(artist, title)
        if not info:
            print("🚫 No se encontró info para esta canción.")
            return

        modified = False

        # Añadir campos si están vacíos
        if "artist" not in audio and info.get("artist"):
            audio["artist"] = info["artist"]
            modified = True
            print(f"🧩 Añadido artista: {info['artist']}")

        if "title" not in audio and info.get("title"):
            audio["title"] = info["title"]
            modified = True
            print(f"🧩 Añadido título: {info['title']}")

        if "album" not in audio and info.get("album"):
            audio["album"] = info["album"]
            modified = True
            print(f"🧩 Añadido álbum: {info['album']}")

        if "genre" not in audio:
            genre = obtener_genero_por_recording(artist, title) or obtener_genero_por_artista(artist)
            if genre:
                audio["genre"] = genre
                modified = True
                print(f"🎼 Añadido género: {genre}")

        if not tiene_portada(audio) and info.get("release_id"):
            portada = descargar_portada(info["release_id"])
            if portada:
                pic = Picture()
                pic.data = portada
                pic.type = 3
                pic.mime = "image/jpeg"
                pic.desc = "Cover"
                pic.width = 500
                pic.height = 500
                pic.depth = 24
                audio.add_picture(pic)
                modified = True
                print("🖼️ Portada añadida.")

        if modified:
            audio.save()
            print(f"✅ Guardado: {nombre_archivo}")
        else:
            print(f"✅ Sin cambios necesarios: {nombre_archivo}")

    except Exception as e:
        print(f"❌ Error procesando {path}: {e}")

def procesar_carpeta(ruta, max_hilos=15):
    archivos = [os.path.join(ruta, f) for f in os.listdir(ruta) if f.lower().endswith(".flac")]
    with ThreadPoolExecutor(max_workers=max_hilos) as executor:
        futures = [executor.submit(procesar_archivo, f) for f in archivos]
        for _ in as_completed(futures):
            pass

# Ejecutar
procesar_carpeta(".", max_hilos=15)
