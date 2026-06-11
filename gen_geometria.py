# -*- coding: utf-8 -*-
"""Genera data/geometria.json con la posición de cada campo del formulario,
a partir de un PDF de referencia que conserve el AcroForm.

Uso:  python gen_geometria.py ["pdf de referencia"]

Esta geometría permite extraer también los PDFs "aplanados" (impresos a PDF),
que pierden el formulario pero conservan el dibujo en las mismas coordenadas.
"""
import json
import sys
from pathlib import Path

from pypdf import PdfReader

REFERENCIA = r"C:\Users\andre\OneDrive\Escritorio\Porras Mundial SC\Formulario USA 2026_Casca.pdf"
SALIDA = Path(__file__).parent / "data" / "geometria.json"


def nombre_completo(obj):
    partes = []
    o = obj
    while o is not None:
        t = o.get("/T")
        if t:
            partes.append(str(t))
        o = o.get("/Parent")
        o = o.get_object() if o is not None else None
    return ".".join(reversed(partes))


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else REFERENCIA
    reader = PdfReader(ruta)
    geometria = {}
    for num_pag, page in enumerate(reader.pages):
        for annot in page.get("/Annots") or []:
            a = annot.get_object()
            if a.get("/Subtype") != "/Widget":
                continue
            # el annot puede ser el propio campo o un kid de un radio
            campo = a if a.get("/T") else (a.get("/Parent").get_object() if a.get("/Parent") else None)
            if campo is None:
                continue
            nombre = nombre_completo(campo)
            ft = campo.get("/FT")
            # sube hasta encontrar el /FT heredado
            padre = campo
            while ft is None and padre.get("/Parent") is not None:
                padre = padre["/Parent"].get_object()
                ft = padre.get("/FT")
            rect = [round(float(x), 2) for x in a["/Rect"]]
            if str(ft) == "/Btn":
                entrada = geometria.setdefault(nombre, {"tipo": "radio", "pagina": num_pag, "botones": []})
                entrada["botones"].append(rect)
            else:
                geometria[nombre] = {"tipo": "texto", "pagina": num_pag, "rect": rect}
    # ordenar botones de izquierda a derecha
    for g in geometria.values():
        if g["tipo"] == "radio":
            g["botones"].sort(key=lambda r: r[0])
    SALIDA.parent.mkdir(exist_ok=True)
    SALIDA.write_text(json.dumps(geometria, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(geometria)} campos -> {SALIDA}")


if __name__ == "__main__":
    main()
