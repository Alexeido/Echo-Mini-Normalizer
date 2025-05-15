
from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mutagen.flac import FLAC
import os
from typing import Optional
from pydantic import BaseModel


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FLAC_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "flacs"))

app = FastAPI()

# Habilitar CORS para desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción restringe a tu frontend
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo para los metadatos que se pueden actualizar
class FlacMetadata(BaseModel):
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    tracknumber: Optional[str] = None
    genre: Optional[str] = None
    date: Optional[str] = None
    discnumber: Optional[str] = None
    totaldiscs: Optional[str] = None
    year: Optional[str] = None
    lyrics: Optional[str] = None


@app.get("/api/flacs")
async def list_flacs():
    files = [f for f in os.listdir(FLAC_DIR) if f.lower().endswith(".flac")]
    result = []
    for f in files:
        path = os.path.join(FLAC_DIR, f)
        try:
            audio = FLAC(path)
            metadata = {
                "filename": f,
                "title": audio.get("title", [""])[0],
                "artist": audio.get("artist", [""])[0],
                "album": audio.get("album", [""])[0],
                "tracknumber": audio.get("tracknumber", [""])[0],
                "genre": audio.get("genre", [""])[0],
                "date": audio.get("date", [""])[0],
                "length": audio.info.length,
                "bitrate": audio.info.bitrate,
                "sample_rate": audio.info.sample_rate,
                "channels": audio.info.channels,
                "size": os.path.getsize(path),
                "discnumber": audio.get("discnumber", [""])[0],
                "totaldiscs": audio.get("totaldiscs", [""])[0],
                "year": audio.get("year", [""])[0],
                "lyrics": audio.get("lyrics", [""])[0] if "lyrics" in audio else None,
            }
        except:
            metadata = {"filename": f}
        result.append(metadata)
    return result

@app.get("/api/flacs/{filename}")
async def get_flac(filename: str):
    path = os.path.join(FLAC_DIR, filename)
    try:
        audio = FLAC(path)
        metadata = {
            "filename": filename,
            "title": audio.get("TITLE", [""])[0] or audio.get("title", [""])[0],
            "artist": audio.get("ARTIST", [""])[0] or audio.get("artist", [""])[0],
            "album": audio.get("ALBUM", [""])[0] or audio.get("album", [""])[0],
            "tracknumber": audio.get("TRACKNUMBER", [""])[0] or audio.get("tracknumber", [""])[0],
            "genre": audio.get("GENRE", [""])[0] or audio.get("genre", [""])[0],
            "date": audio.get("DATE", [""])[0] or audio.get("date", [""])[0],
            "length": audio.info.length,
            "bitrate": audio.info.bitrate,
            "sample_rate": audio.info.sample_rate,
            "channels": audio.info.channels,
            "size": os.path.getsize(path),
            "discnumber": audio.get("DISCNUMBER", [""])[0] or audio.get("discnumber", [""])[0],
            "totaldiscs": audio.get("TOTALDISCS", [""])[0] or audio.get("totaldiscs", [""])[0],
            "year": audio.get("YEAR", [""])[0] or audio.get("year", [""])[0],
        }
    except:
        metadata = {"filename": filename}
    return metadata

@app.get("/api/cover/{filename}")
async def get_cover(filename: str):
    path = os.path.join(FLAC_DIR, filename)
    try:
        audio = FLAC(path)
        if audio.pictures:
            pic = audio.pictures[0]
            return Response(content=pic.data, media_type=pic.mime)
    except:
        pass
    # Si no hay imagen, devuelve un placeholder (pon uno en static/)
    with open(os.path.join(BASE_DIR, "../static/placeholder.png"), "rb") as f:
        data = f.read()
    return Response(content=data, media_type="image/png")



@app.put("/api/flacs/{filename}")
async def update_flac(filename: str, metadata: FlacMetadata):
    path = os.path.join(FLAC_DIR, filename)
    try:
        audio = FLAC(path)
        
        # Primero, borrar los campos existentes para evitar duplicados
        for key in metadata.dict(exclude_none=True).keys():
            if key.upper() in audio:
                del audio[key.upper()]
            if key.lower() in audio:
                del audio[key.lower()]
        
        # Mapeo de nombres de campo para compatibilidad con Windows
        field_mapping = {
            "title": "TITLE",
            "artist": "ARTIST",
            "album": "ALBUM",
            "tracknumber": "TRACKNUMBER",
            "genre": "GENRE",
            "date": "DATE",
            "discnumber": "DISCNUMBER",
            "totaldiscs": "TOTALDISCS",
            "year": "DATE",  # Windows usa DATE para mostrar el año
            "lyrics": "LYRICS"
        }
        
        # Actualizar los metadatos usando nombres estándar Vorbis
        for key, value in metadata.dict(exclude_none=True).items():
            vorbis_key = field_mapping.get(key, key.upper())
            audio[vorbis_key] = [value]  # En FLAC, los metadatos son listas de strings
            
            # Para compatibilidad adicional, también escribir con el nombre original
            if key != vorbis_key.lower():
                audio[key] = [value]
                
            # Caso especial para el año: establecerlo tanto en YEAR como en DATE
            if key == "year":
                audio["YEAR"] = [value]
                audio["DATE"] = [value]
        
        # Guardar cambios
        audio.save()
        
        # Devolver los metadatos actualizados
        return await get_flac(filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

from fastapi import FastAPI, Response, HTTPException, File, UploadFile, Form

# ... código existente ...

@app.put("/api/cover/{filename}")
async def update_cover(filename: str, cover: UploadFile = File(...)):
    path = os.path.join(FLAC_DIR, filename)
    try:
        # Leer el archivo FLAC
        audio = FLAC(path)
        
        # Leer la imagen subida
        image_data = await cover.read()
        
        # Determinar el tipo MIME
        mime_type = cover.content_type
        
        # Borrar imágenes existentes
        audio.clear_pictures()
        
        # Añadir la nueva imagen
        from mutagen.flac import Picture
        pic = Picture()
        pic.data = image_data
        pic.mime = mime_type
        pic.type = 3  # 3 para la portada frontal
        pic.width = 500  # estos valores son aproximados
        pic.height = 500
        pic.depth = 24  # profundidad de color típica
        
        audio.add_picture(pic)
        
        # Guardar el archivo
        audio.save()
        
        return {"success": True}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))