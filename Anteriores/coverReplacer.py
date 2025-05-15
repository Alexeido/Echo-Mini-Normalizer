#!/usr/bin/env python3
import os
import sys
import threading
import musicbrainzngs
import requests
from io import BytesIO
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from mutagen.flac import FLAC, Picture
from concurrent.futures import ThreadPoolExecutor, as_completed
from mutagen.flac import FLAC

def has_valid_cover(path):
    """
    Devuelve True si el FLAC en 'path' tiene al menos una imagen con mime image/…
    """
    try:
        audio = FLAC(path)
        for pic in audio.pictures:
            if pic.mime and pic.mime.startswith("image/"):
                return True
    except Exception:
        pass
    return False

# Configuración MusicBrainz
musicbrainzngs.set_useragent("CoverSelector", "1.0", "you@example.com")

# Funciones de búsqueda y descarga
def descargar_portada(release_id):
    try:
        url = f"https://coverartarchive.org/release/{release_id}/front"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.content
            img = Image.open(BytesIO(data))
            if img.format != "JPEG":
                buf = BytesIO()
                img.convert("RGB").save(buf, format="JPEG")
                return buf.getvalue()
            return data
    except Exception as e:
        print(f"DEBUG: fallo descargar_portada({release_id}): {e}")
    return None

def buscar_por_tags(artist, album, limit=10):
    try:
        print(f"DEBUG: buscar_por_tags {artist} - {album}")
        res = musicbrainzngs.search_releases(artist=artist, release=album, limit=limit)
        for rel in res["release-list"]:
            img = descargar_portada(rel["id"])
            if img:
                yield img
    except Exception as e:
        print(f"DEBUG: error buscar_por_tags: {e}")

def buscar_por_nombre(nombre, limit=10):
    try:
        print(f"DEBUG: buscar_por_nombre {nombre}")
        res = musicbrainzngs.search_releases(query=nombre, limit=limit)
        for rel in res["release-list"]:
            img = descargar_portada(rel["id"])
            if img:
                yield img
    except Exception as e:
        print(f"DEBUG: error buscar_por_nombre: {e}")

def buscar_por_grupo(artist, limit=10):
    try:
        print(f"DEBUG: buscar_por_grupo {artist}")
        res = musicbrainzngs.search_releases(artist=artist, limit=limit)
        for rel in res["release-list"]:
            img = descargar_portada(rel["id"])
            if img:
                yield img
    except Exception as e:
        print(f"DEBUG: error buscar_por_grupo: {e}")

# Embebido
def tiene_portada(audio: FLAC):
    return bool(audio.pictures)

def incrustar(imagen_bytes, flac_path):
    audio = FLAC(flac_path)
    pic = Picture()
    pic.data = imagen_bytes
    pic.type = 3
    pic.mime = "image/jpeg"
    img = Image.open(BytesIO(imagen_bytes))
    pic.width, pic.height = img.size
    pic.depth = 24
    audio.clear_pictures()
    audio.add_picture(pic)
    audio.save()

class CoverSelector(tk.Tk):
    def __init__(self, target, max_workers=5):
        super().__init__()
        self.title("Cover Selector")
        self.geometry("1000x600")
        self.max_workers = max_workers

        # Pre-scan de archivos FLAC
        if os.path.isfile(target) and target.lower().endswith(".flac"):
            self.flacs = [os.path.abspath(target)]
            self.allow_replace = True
        else:
            print(f"DEBUG: escaneando carpeta {target} con {self.max_workers} hilos")
            paths = [os.path.join(target, f) for f in os.listdir(target) if f.lower().endswith(".flac")]
            self.flacs = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
                future_map = {ex.submit(self._check_cover, p): p for p in paths}
                for fut in as_completed(future_map):
                    p = future_map[fut]
                    has = fut.result()
                    if not has:
                        self.flacs.append(p)
            self.allow_replace = False
            print(f"DEBUG: encontrados {len(self.flacs)} archivos sin portada")

        # UI layout
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Lista de archivos
        frame_list = ttk.Frame(self)
        frame_list.grid(row=0, column=0, sticky="ns")
        self.listbox = tk.Listbox(frame_list, width=30)
        for f in self.flacs:
            self.listbox.insert("end", os.path.basename(f))
        self.listbox.pack(fill="y", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # Panel derecho
        self.panel = ttk.Frame(self)
        self.panel.grid(row=0, column=1, sticky="nsew")
        self.lbl_info = ttk.Label(self.panel, text="", font=("TkDefaultFont", 12, "bold"))
        self.lbl_info.pack(pady=5)

        # Tres filas de resultados
        self.frame_tags = ttk.LabelFrame(self.panel, text="Portadas por Álbum")
        self.frame_tags.pack(fill="x", padx=5, pady=2)
        self.frame_name = ttk.LabelFrame(self.panel, text="Portadas por Nombre de Archivo")
        self.frame_name.pack(fill="x", padx=5, pady=2)
        self.frame_group = ttk.LabelFrame(self.panel, text="Portadas por Grupo")
        self.frame_group.pack(fill="x", padx=5, pady=2)

        # Búsqueda libre
        search_frame = ttk.Frame(self.panel)
        search_frame.pack(fill="x", padx=5, pady=5)
        self.search_var = tk.StringVar()
        tk.Entry(search_frame, textvariable=self.search_var).pack(side="left", fill="x", expand=True)
        ttk.Button(search_frame, text="Buscar", command=self.on_search).pack(side="left", padx=5)
        self.frame_search = ttk.LabelFrame(self.panel, text="Resultados Búsqueda Libre")
        self.frame_search.pack(fill="x", padx=5, pady=2)

        self.thumb_size = (100,100)
        self.canvases = []

        if self.flacs:
            self.listbox.selection_set(0)
            self.on_select()

    def _check_cover(self, path):
        valid = has_valid_cover(path)
        print(f"DEBUG: {os.path.basename(path)} tiene portada válida? {valid}")
        return valid



    def clear_frame(self, frame):
        for w in frame.winfo_children():
            w.destroy()
        self.canvases.clear()

    def on_select(self, event=None):
        sel = self.listbox.curselection()
        if not sel: return
        self.current = self.flacs[sel[0]]
        audio = FLAC(self.current)
        artist = audio.get("artist", [""])[0]
        album  = audio.get("album", [""])[0]
        title  = audio.get("title", [""])[0]
        self.lbl_info.config(text=f"{title} — {artist} ({album})")
        for f in [self.frame_tags, self.frame_name, self.frame_group, self.frame_search]:
            self.clear_frame(f)
        threading.Thread(target=self.load_covers, daemon=True).start()

    def load_covers(self):
        audio = FLAC(self.current)
        artist = audio.get("artist", [""])[0]
        album  = audio.get("album", [""])[0]
        base   = os.path.splitext(os.path.basename(self.current))[0]

        # lanzamos 3 hilos de búsqueda
        threading.Thread(target=self._fetch_and_add, args=(buscar_por_tags, (artist, album), self.frame_tags), daemon=True).start()
        threading.Thread(target=self._fetch_and_add, args=(buscar_por_nombre, (base,), self.frame_name), daemon=True).start()
        threading.Thread(target=self._fetch_and_add, args=(buscar_por_grupo, (artist,), self.frame_group), daemon=True).start()

    def _fetch_and_add(self, func, args, frame):
        for imgdata in func(*args):
            self.after(0, self.add_thumbnail, frame, imgdata)

    def on_search(self):
        txt = self.search_var.get().strip()
        if not txt: return
        self.clear_frame(self.frame_search)
        threading.Thread(target=self._fetch_and_add, args=(buscar_por_nombre, (txt,), self.frame_search), daemon=True).start()

    def add_thumbnail(self, frame, imgdata):
        img = Image.open(BytesIO(imgdata))
        img.thumbnail(self.thumb_size)
        tkimg = ImageTk.PhotoImage(img)
        lbl = tk.Label(frame, image=tkimg, cursor="hand2", bd=2, relief="ridge")
        lbl.image = tkimg
        lbl.pack(side="left", padx=5, pady=5)
        lbl.bind("<Double-Button-1>", lambda e, d=imgdata: self.on_select_cover(d))

    def on_select_cover(self, imgdata):
        try:
            incrustar(imgdata, self.current)
            print(f"DEBUG: portada incrustada en {os.path.basename(self.current)}")
            messagebox.showinfo("OK", f"Portada incrustada en:\n{os.path.basename(self.current)}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = filedialog.askdirectory(title="Selecciona carpeta de FLAC")
        if not path:
            sys.exit(0)
    app = CoverSelector(path, max_workers=10)
    app.mainloop()
