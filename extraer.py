# -*- coding: utf-8 -*-
"""Extrae los pronósticos de los PDFs de la porra y los guarda en data/predicciones.json.

Uso:
    python extraer.py ["carpeta con los PDFs"]

Si no se indica carpeta, usa la carpeta de OneDrive por defecto.

Lee dos tipos de PDF:
  - con formulario (AcroForm): lectura directa de los campos;
  - "aplanados" (impresos a PDF, sin formulario): usa data/geometria.json
    (generado con gen_geometria.py) para leer texto y marcas por coordenadas.

Si existe data/correcciones.json se aplican retoques manuales por participante.
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader

import plantilla as P

DATA = Path(__file__).parent / "data"
SALIDA = DATA / "predicciones.json"
GEOMETRIA = DATA / "geometria.json"
CORRECCIONES = DATA / "correcciones.json"

_SIGNOS = {0: "1", 1: "X", 2: "2"}


# ---------------------------------------------------------------- lectores

class LectorFormulario:
    """Lee un PDF que conserva el AcroForm."""

    def __init__(self, ruta):
        reader = PdfReader(str(ruta))
        acro = reader.trailer["/Root"].get("/AcroForm")
        if acro is None:
            raise ValueError("sin formulario")
        self.campos = dict(self._walk(acro["/Fields"]))

    @staticmethod
    def _walk(fields, prefix=""):
        for f in fields:
            o = f.get_object()
            nombre = str(o.get("/T") or "")
            completo = f"{prefix}.{nombre}" if prefix else nombre
            hijos = [k for k in (o.get("/Kids") or []) if k.get_object().get("/T")]
            if hijos:
                yield from LectorFormulario._walk(hijos, completo)
            else:
                yield completo, o

    def texto(self, nombre):
        o = self.campos.get(nombre)
        if o is None:
            return None
        v = o.get("/V")
        return str(v).strip() if v is not None else None

    def radio_idx(self, nombre):
        """Índice (0,1,2,...) de la opción marcada, por posición izq->dcha.
        Se usa la posición y no el valor exportado porque la plantilla tiene
        valores erróneos en algunos botones ('/5' en vez de '/2', '/x', etc.)."""
        o = self.campos.get(nombre)
        if o is None:
            return None
        v = o.get("/V")
        if v is None or str(v) == "/Off":
            return None
        v = str(v)
        botones = []
        for k in o.get("/Kids", []):
            ko = k.get_object()
            estados = [s for s in ko.get("/AP", {}).get("/N", {}).keys() if str(s) != "/Off"]
            if estados:
                botones.append((float(ko["/Rect"][0]), str(estados[0])))
        botones.sort()
        for i, (_, estado) in enumerate(botones):
            if estado == v:
                return i
        return None


class LectorPosicional:
    """Lee valores por posición usando la geometría de la plantilla. Cubre dos
    casos en los que el dato no está en el campo del formulario:

    - PDFs aplanados (impresos a PDF): el texto queda en el contenido de la
      página y los radios marcados llevan un punto relleno dibujado dentro.
    - Valores escritos como ANOTACIONES (apps móviles tipo "Mobile User"):
      texto en anotaciones FreeText y marcas de radio como sellos (/Stamp)
      o trazos (/Ink) diminutos sobre el círculo.
    """

    def __init__(self, ruta):
        import pdfplumber
        if not GEOMETRIA.exists():
            raise ValueError("falta data/geometria.json (ejecuta gen_geometria.py)")
        self.geo = json.loads(GEOMETRIA.read_text(encoding="utf-8"))
        self.palabras = []      # por página: [(cx, cy, x0, texto)] del contenido
        self.puntos = []        # por página: [(cx, cy)] puntos rellenos / sellos
        self.anotaciones = []   # por página: [(rect_pdf, texto)] de FreeText
        with pdfplumber.open(str(ruta)) as pdf:
            for page in pdf.pages:
                H = page.height
                ws = []
                for w in page.extract_words():
                    cx = (w["x0"] + w["x1"]) / 2
                    cy = H - (w["top"] + w["bottom"]) / 2
                    ws.append((cx, cy, w["x0"], w["text"]))
                self.palabras.append(ws)
                ps = []
                for c in page.curves:
                    ancho = c["x1"] - c["x0"]
                    alto = c["bottom"] - c["top"]
                    if c.get("fill") and 1.5 <= ancho <= 7 and 1.5 <= alto <= 7:
                        ps.append(((c["x0"] + c["x1"]) / 2, H - (c["top"] + c["bottom"]) / 2))
                self.puntos.append(ps)
                self.anotaciones.append([])
        # anotaciones vía pypdf (subtipo y contenido fiables)
        reader = PdfReader(str(ruta))
        for num, page in enumerate(reader.pages):
            for a in (page.get("/Annots") or []):
                o = a.get_object()
                sub = str(o.get("/Subtype"))
                rect = [float(x) for x in o.get("/Rect", [0, 0, 0, 0])]
                if sub == "/FreeText":
                    cont = str(o.get("/Contents") or "").strip()
                    if cont:
                        self.anotaciones[num].append((rect, cont))
                elif sub in ("/Stamp", "/Ink", "/Square", "/Circle"):
                    ancho, alto = rect[2] - rect[0], rect[3] - rect[1]
                    if ancho <= 14 and alto <= 14:  # marca pequeña = punto de radio
                        self.puntos[num].append(((rect[0] + rect[2]) / 2,
                                                 (rect[1] + rect[3]) / 2))

    @staticmethod
    def _dentro(cx, cy, rect, margen=2.0):
        x0, y0, x1, y1 = rect
        return x0 - margen <= cx <= x1 + margen and y0 - margen <= cy <= y1 + margen

    @staticmethod
    def _solape(r1, r2):
        ancho = min(r1[2], r2[2]) - max(r1[0], r2[0])
        alto = min(r1[3], r2[3]) - max(r1[1], r2[1])
        return max(ancho, 0) * max(alto, 0)

    def texto(self, nombre):
        g = self.geo.get(nombre)
        if g is None or g["tipo"] != "texto":
            return None
        # 1) palabras del contenido de la página dentro del rectángulo
        dentro = [(x0, t) for cx, cy, x0, t in self.palabras[g["pagina"]]
                  if self._dentro(cx, cy, g["rect"])]
        dentro.sort()
        valor = " ".join(t for _, t in dentro).strip()
        if valor:
            return valor
        # 2) anotación FreeText con mayor solape con el campo
        candidatos = [(self._solape(g["rect"], rect), cont)
                      for rect, cont in self.anotaciones[g["pagina"]]]
        candidatos = [c for c in candidatos if c[0] > 0]
        if candidatos:
            return max(candidatos)[1]
        return None

    def radio_idx(self, nombre):
        g = self.geo.get(nombre)
        if g is None or g["tipo"] != "radio":
            return None
        for i, rect in enumerate(g["botones"]):
            if any(self._dentro(cx, cy, rect, 1.0) for cx, cy in self.puntos[g["pagina"]]):
                return i
        return None


# ---------------------------------------------------------------- parseo

def _parse_marcador(texto):
    """'2-0', '2 - 0', '2:0' -> (2, 0). None si no se puede interpretar."""
    if not texto:
        return None
    m = re.search(r"(\d+)\s*[-–—:]\s*(\d+)", str(texto))
    return (int(m.group(1)), int(m.group(2))) if m else None


def _parse_entero(texto):
    if texto is None:
        return None
    m = re.search(r"\d+", str(texto))
    return int(m.group(0)) if m else None


def extraer_pdf(ruta):
    """Extrae los pronósticos de un PDF. Devuelve (dict, avisos)."""
    avisos = []
    try:
        formulario = LectorFormulario(ruta)
    except ValueError:
        formulario = None
        avisos.append("PDF sin formulario (aplanado): extraído por posición")

    posicional = None

    def aux():
        # el análisis posicional es costoso: solo si hace falta
        nonlocal posicional
        if posicional is None:
            posicional = LectorPosicional(ruta)
        return posicional

    def texto(*nombres):
        """Valor del primer campo con contenido. Prueba cada alias de nombre
        (hay dos versiones de la plantilla) primero en el formulario y después
        por posición (PDFs aplanados o valores escritos como anotaciones)."""
        for n in nombres:
            if formulario:
                v = formulario.texto(n)
                if v and v.strip():
                    return v.strip()
        for n in nombres:
            v = aux().texto(n)
            if v and v.strip():
                return v.strip()
        return None

    def radio_idx(nombre):
        if formulario:
            idx = formulario.radio_idx(nombre)
            if idx is not None:
                return idx
        return aux().radio_idx(nombre)

    nombre = texto("Nombre y apellidos") or ruta.stem
    pred = {
        "nombre": nombre,
        "archivo": ruta.name,
        "grupos": {},
        "bonus": {},
        "segunda": {},
        "fase_final": {},
    }

    # --- Fase de grupos: 1X2 y orden ---
    for letra, partidos in P.PARTIDOS_GRUPO.items():
        signos = {}
        for i, (loc, vis) in enumerate(partidos, start=1):
            idx = radio_idx(f"Group{letra}{i}")
            if idx is None:
                avisos.append(f"sin 1X2 en {loc}-{vis} (grupo {letra})")
            signos[P.clave_partido(loc, vis)] = _SIGNOS.get(idx)
        orden = []
        for pos in (1, 2, 3):
            val = texto(f"{pos}º Grupo {letra}")
            eq = P.equipo_canonico(val)
            if eq is None and val:
                avisos.append(f"equipo no reconocido en {pos}º Grupo {letra}: {val!r}")
            if eq is None and not val:
                avisos.append(f"vacío: {pos}º Grupo {letra}")
            orden.append(eq)
        pred["grupos"][letra] = {"signos": signos, "orden": orden}

    # --- Bonus primera fase ---
    def letra_grupo(val):
        if not val:
            return None
        m = re.search(r"[A-L]\s*$", val.strip())
        return m.group(0).strip() if m else None

    pred["bonus"]["grupo_mas"] = letra_grupo(texto("Grupo + goleador"))
    pred["bonus"]["grupo_menos"] = letra_grupo(texto("Grupo - goleador"))

    exactos = {}
    for campo, (loc, vis) in P.EXACTOS_CAMPOS.items():
        val = texto(campo)
        marcador = _parse_marcador(val)
        if marcador is None:
            avisos.append(f"marcador ilegible en {campo}: {val!r}")
        exactos[P.clave_partido(loc, vis)] = list(marcador) if marcador else None
    pred["bonus"]["exactos"] = exactos

    idx = radio_idx("+goles")
    pred["bonus"]["equipo_mas_goles"] = P.BONUS_EQUIPOS[idx] if idx is not None else None

    # --- Segunda fase ---
    def lista_equipos(patrones, n):
        equipos = []
        for i in range(1, n + 1):
            val = texto(*[p.format(i) for p in patrones])
            eq = P.equipo_canonico(val)
            if eq is None:
                avisos.append(f"equipo no reconocido en {patrones[0].format(i)}: {val!r}")
            equipos.append(eq)
        return equipos

    pred["segunda"]["clasif_octavos"] = lista_equipos(["Octavo finalista {}", "1/8 finalista {}"], 16)
    pred["segunda"]["clasif_cuartos"] = lista_equipos(["1/4 finalista {}"], 8)
    pred["segunda"]["clasif_semifinales"] = lista_equipos(["Semifinalista {}"], 4)
    pred["segunda"]["clasif_final"] = lista_equipos(["Finalista {}"], 2)
    pred["segunda"]["campeon"] = P.equipo_canonico(texto("Campeon", "Campeón"))
    pred["segunda"]["goles3_dieciseisavos"] = _parse_entero(texto("Goles 1/16"))
    pred["segunda"]["goles3_octavos"] = _parse_entero(texto("Goles 1/8"))
    pred["segunda"]["goles3_cuartos"] = _parse_entero(texto("Goles 1/4"))
    pred["segunda"]["goles_semifinales"] = _parse_entero(texto("Goles semifinales"))
    pred["segunda"]["goles_final"] = _parse_entero(texto("Goles Final"))

    # --- Fase final ---
    pred["fase_final"]["goleador"] = texto("Maximo goleador")
    pred["fase_final"]["treboles"] = [radio_idx(f"Trebol {i}") for i in range(1, 13)]

    return pred, avisos


# ---------------------------------------------------------------- correcciones

def _merge(base, extra):
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v


def aplicar_correcciones(participantes):
    if not CORRECCIONES.exists():
        return []
    correcciones = json.loads(CORRECCIONES.read_text(encoding="utf-8"))
    aplicadas = []
    for clave, cambios in correcciones.items():
        for p in participantes:
            if p["nombre"] == clave or p["archivo"] == clave:
                _merge(p, cambios)
                aplicadas.append(clave)
                break
    return aplicadas


# ---------------------------------------------------------------- main

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    carpeta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "OneDrive" / "Porra Mundial 2022"
    pdfs = sorted(carpeta.glob("*.pdf"))
    if not pdfs:
        print(f"No hay PDFs en {carpeta}")
        sys.exit(1)

    participantes = []
    todos_avisos = {}
    for pdf in pdfs:
        try:
            pred, avisos = extraer_pdf(pdf)
        except Exception as e:
            print(f"ERROR en {pdf.name}: {e}")
            continue
        participantes.append(pred)
        if avisos:
            todos_avisos[pred["nombre"]] = avisos
        print(f"OK  {pdf.name}  ->  {pred['nombre']}")

    aplicadas = aplicar_correcciones(participantes)
    if aplicadas:
        print(f"Correcciones manuales aplicadas a: {', '.join(aplicadas)}")

    DATA.mkdir(exist_ok=True)
    datos = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "carpeta": str(carpeta),
        "participantes": participantes,
        "avisos": todos_avisos,
    }
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{len(participantes)} porras guardadas en {SALIDA}")
    if todos_avisos:
        print("\nAvisos (revisar):")
        for nombre, avisos in todos_avisos.items():
            for a in avisos:
                print(f"  [{nombre}] {a}")


if __name__ == "__main__":
    main()
