# ECHO MINI Normalizer 🎧

[🇪🇸 Español](#echo-mini-normalizer-🎧-español)

A multithreaded Python script to normalize `.flac` file metadata, optimizing tags for the Echo Mini device. It automatically adds genres and cover art using MusicBrainz.

---

## 🔥 Features

- 🔁 Ensures metadata is in **Vorbis Comments** format (the correct standard for FLAC).
- 🎼 Automatically adds **genre**:
  - Searches by song (`artist + title`).
  - Falls back to artist if no match is found.
- 🖼️ Automatically adds **cover art**:
  - Searches by album (`artist + album`).
  - Falls back to filename if no match is found.
  - Uses the first available image (500px).

## ⚙️ Requirements

- Python 3.8+
- `metaflac` must be installed and accessible in the `PATH`.  
  👉 Download it from: [https://xiph.org/flac/download.html](https://xiph.org/flac/download.html)
- Songs should have minimal tags or an identifiable song name.
- Complements [Deezer-Downloader](https://github.com/kmille/deezer-downloader) for post-processing files.

Install dependencies with:

```bash
pip install -r requirements.txt
```

### How it works:

- Processes all `.flac` files in the current directory.
- Uses multiple threads to speed up the process.
- Only adds genre or cover art if they are missing.

## 🛡️ Disclaimer

This script **does not overwrite existing metadata**; it only fills in missing information.  
Changes are made directly to the files, so make a backup if needed.

## 📜 License

MIT

---

## ECHO MINI Normalizer 🎧 (Español)

[🔝 Back to English section](#echo-mini-normalizer-🎧)

Un script multihilo en Python para normalizar metadatos de archivos `.flac`, optimizando etiquetas para el dispositivo Echo Mini. Añade géneros y carátulas automáticamente usando MusicBrainz.

---

## 🔥 Características

- 🔁 Asegura que los metadatos estén en formato **Vorbis Comments** (el estándar correcto para FLAC).
- 🎼 Añade **género** automáticamente:
  - Busca por canción (`artist + title`).
  - Si no encuentra coincidencias, intenta por artista.
- 🖼️ Añade **portada** automáticamente:
  - Busca por álbum (`artist + album`).
  - Si no encuentra coincidencias, intenta por nombre de archivo.
  - Usa la primera imagen disponible (500px).

## ⚙️ Requisitos

- Python 3.8+
- `metaflac` debe estar instalado y accesible en el `PATH`.  
  👉 Descárgalo desde: [https://xiph.org/flac/download.html](https://xiph.org/flac/download.html)
- Las canciones deben tener etiquetas mínimas o un nombre identificable.
- Complementa [Deezer-Downloader](https://github.com/kmille/deezer-downloader) para el post-procesamiento de archivos.

Instala las dependencias con:

```bash
pip install -r requirements.txt
```

### Cómo funciona:

- Procesa todos los archivos `.flac` en el directorio actual.
- Usa varios hilos para acelerar el proceso.
- Solo añade género o portada si no existen en el archivo.

## 🛡️ Aviso

Este script **no sobrescribe metadatos existentes**, solo completa los que faltan.  
Los cambios se realizan directamente sobre los archivos, así que haz un respaldo si lo necesitas.

## 📜 Licencia

MIT