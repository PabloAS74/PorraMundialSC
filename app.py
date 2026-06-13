# -*- coding: utf-8 -*-
"""Web local de la porra del Mundial 2026.

Uso:  python app.py   y abrir http://localhost:5000

Los resultados reales se meten igual que los pide el formulario de la porra:
1/X/2 por partido, marcador exacto solo en los 12 partidos del bonus,
orden de cada grupo, clasificados de cada ronda y contadores de goles.
"""
import json
import os
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, abort, flash, session
from werkzeug.utils import secure_filename

import extraer
import api_football
import plantilla as P
import puntuacion
import dotenv

dotenv.load_dotenv()

BASE = Path(__file__).parent
DATA = BASE / "data"
PREDICCIONES = DATA / "predicciones.json"
RESULTADOS = DATA / "resultados.json"
SUBIDAS = DATA / "subidas"
PASSWORD = os.environ.get("PASSWORD")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "porra-mundial-local")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024


def requiere_login(vista):
    @wraps(vista)
    def wrapper(*args, **kwargs):
        if not session.get("autenticado"):
            return redirect(url_for("login", next=request.full_path))
        return vista(*args, **kwargs)
    return wrapper


def resultados_vacios():
    return {
        "grupos_1x2": {},        # clave_partido -> "1" / "X" / "2"
        "exactos": {},           # clave_partido -> [g1, g2] (solo los 12 del bonus)
        "orden": {},             # letra -> [1º, 2º, 3º]
        "grupo_mas": [],         # letras (varias si empatan)
        "grupo_menos": [],
        "equipo_mas_goles": [],  # equipos del bonus (varios si empatan)
        "clasificados": {"octavos": [], "cuartos": [], "semifinales": [], "final": []},
        "campeon": None,
        "goles3": {},            # dieciseisavos/octavos/cuartos -> nº partidos con 3+ goles
        "goles_semifinales": None,
        "goles_final": None,
        "goleador_correctos": [],   # pronósticos de goleador marcados como acertados
        "trebol_ganadores": {},     # "1".."12" -> índices ganadores (0,1,2)
    }


def cargar_resultados():
    base = resultados_vacios()
    if RESULTADOS.exists():
        base.update(json.loads(RESULTADOS.read_text(encoding="utf-8")))
    return base


def guardar_resultados(datos):
    DATA.mkdir(exist_ok=True)
    RESULTADOS.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")


def cargar_predicciones():
    if not PREDICCIONES.exists():
        return None
    return json.loads(PREDICCIONES.read_text(encoding="utf-8"))


def guardar_predicciones(datos):
    DATA.mkdir(exist_ok=True)
    PREDICCIONES.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")


def predicciones_vacias():
    return {
        "generado": None,
        "carpeta": "subidas desde la web",
        "participantes": [],
        "avisos": {},
    }


def ruta_subida_segura(nombre_archivo):
    SUBIDAS.mkdir(parents=True, exist_ok=True)
    nombre = secure_filename(nombre_archivo) or "porra.pdf"
    if not nombre.lower().endswith(".pdf"):
        nombre = f"{nombre}.pdf"
    ruta = SUBIDAS / nombre
    contador = 1
    while ruta.exists():
        ruta = SUBIDAS / f"{Path(nombre).stem}_{contador}{Path(nombre).suffix}"
        contador += 1
    return ruta


def next_seguro(valor):
    return valor if valor and valor.startswith("/") and not valor.startswith("//") else url_for("home")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == PASSWORD:
            session["autenticado"] = True
            flash("Sesión iniciada correctamente.", "ok")
            return redirect(next_seguro(request.form.get("next")))
        flash("Contraseña incorrecta.", "error")
    return render_template("login.html", next=next_seguro(request.args.get("next")))


@app.route("/logout")
def logout():
    session.pop("autenticado", None)
    flash("Sesión cerrada.", "ok")
    return redirect(url_for("home"))


@app.route("/")
def home():
    datos = cargar_predicciones()
    if datos is None:
        return render_template("sin_datos.html")
    resultados = cargar_resultados()
    filas = puntuacion.clasificacion(datos["participantes"], resultados)
    return render_template("clasificacion.html", filas=filas,
                           generado=datos.get("generado"),
                           avisos=datos.get("avisos", {}))


@app.route("/detalle/<nombre>")
def detalle(nombre):
    datos = cargar_predicciones()
    if datos is None:
        return redirect(url_for("home"))
    pred = next((p for p in datos["participantes"] if p["nombre"] == nombre), None)
    if pred is None:
        abort(404)
    resultados = cargar_resultados()
    fila = puntuacion.puntuar(pred, resultados)
    return render_template("detalle.html", fila=fila, pred=pred, P=P, resultados=resultados)


@app.route("/resultados", methods=["GET"])
@requiere_login
def resultados_vista():
    datos = cargar_predicciones()
    resultados = cargar_resultados()
    goleadores = sorted({(p["fase_final"]["goleador"] or "").strip()
                         for p in (datos["participantes"] if datos else [])
                         if (p["fase_final"]["goleador"] or "").strip()})
    return render_template("resultados.html", P=P, r=resultados, goleadores=goleadores)


@app.route("/resultados/actualizar-api", methods=["POST"])
@requiere_login
def actualizar_resultados_api():
    try:
        meta = api_football.actualizar_resultados(RESULTADOS)
        flash(f"Resultados actualizados desde football-data.org ({meta.get('matches', 0)} partidos leídos).", "ok")
    except Exception as exc:
        flash(f"No se pudo actualizar desde football-data.org: {exc}", "error")
    return redirect(url_for("resultados_vista"))


@app.route("/resultados/grupos", methods=["POST"])
@requiere_login
def guardar_grupos():
    r = cargar_resultados()
    for letra, partidos in P.PARTIDOS_GRUPO.items():
        for loc, vis in partidos:
            clave = P.clave_partido(loc, vis)
            v = request.form.get(f"1x2|{clave}", "").strip()
            if v in ("1", "X", "2"):
                r["grupos_1x2"][clave] = v
            else:
                r["grupos_1x2"].pop(clave, None)
        # orden del grupo (puntúa cuando estén las 3 primeras posiciones)
        orden = [request.form.get(f"orden|{letra}|{i}", "").strip() for i in range(3)]
        if any(orden):
            r["orden"][letra] = orden
        else:
            r["orden"].pop(letra, None)
    # los 12 marcadores exactos
    for loc, vis in P.EXACTOS_CAMPOS.values():
        clave = P.clave_partido(loc, vis)
        g1 = request.form.get(f"ex1|{clave}", "").strip()
        g2 = request.form.get(f"ex2|{clave}", "").strip()
        if g1.isdigit() and g2.isdigit():
            r["exactos"][clave] = [int(g1), int(g2)]
        else:
            r["exactos"].pop(clave, None)
    r["grupo_mas"] = request.form.getlist("grupo_mas")
    r["grupo_menos"] = request.form.getlist("grupo_menos")
    r["equipo_mas_goles"] = request.form.getlist("equipo_mas_goles")
    guardar_resultados(r)
    return redirect(url_for("resultados_vista") + "#grupos")


@app.route("/resultados/eliminatorias", methods=["POST"])
@requiere_login
def guardar_eliminatorias():
    r = cargar_resultados()
    tam = {"octavos": 16, "cuartos": 8, "semifinales": 4, "final": 2}
    for ronda, n in tam.items():
        equipos = []
        for i in range(n):
            v = request.form.get(f"clasif|{ronda}|{i}", "").strip()
            equipos.append(v or None)
        r["clasificados"][ronda] = equipos
    r["campeon"] = request.form.get("campeon", "").strip() or None
    for clave in P.PTS_GOLES3:
        v = request.form.get(f"goles3|{clave}", "").strip()
        if v.isdigit():
            r["goles3"][clave] = int(v)
        else:
            r["goles3"].pop(clave, None)
    v = request.form.get("goles_semifinales", "").strip()
    r["goles_semifinales"] = int(v) if v.isdigit() else None
    v = request.form.get("goles_final", "").strip()
    r["goles_final"] = int(v) if v.isdigit() else None
    guardar_resultados(r)
    return redirect(url_for("resultados_vista") + "#eliminatorias")


@app.route("/resultados/premios", methods=["POST"])
@requiere_login
def guardar_premios():
    r = cargar_resultados()
    r["goleador_correctos"] = request.form.getlist("goleador")
    trebol = {}
    for i in range(1, 13):
        ganadores = [int(v) for v in request.form.getlist(f"trebol|{i}")]
        if ganadores:
            trebol[str(i)] = ganadores
    r["trebol_ganadores"] = trebol
    guardar_resultados(r)
    return redirect(url_for("resultados_vista") + "#premios")


@app.route("/participantes/nuevo", methods=["GET", "POST"])
@requiere_login
def subir_participante():
    if request.method == "POST":
        archivo = request.files.get("pdf")
        if not archivo or not archivo.filename:
            flash("Selecciona un PDF de una porra.", "error")
            return redirect(url_for("subir_participante"))
        if not archivo.filename.lower().endswith(".pdf"):
            flash("El archivo debe ser un PDF.", "error")
            return redirect(url_for("subir_participante"))

        ruta = ruta_subida_segura(archivo.filename)
        archivo.save(ruta)
        try:
            pred, avisos = extraer.extraer_pdf(ruta)
            extraer.aplicar_correcciones([pred])
        except Exception as exc:
            ruta.unlink(missing_ok=True)
            flash(f"No se pudo extraer la porra: {exc}", "error")
            return redirect(url_for("subir_participante"))

        datos = cargar_predicciones() or predicciones_vacias()
        participantes = datos.setdefault("participantes", [])
        reemplazado = False
        for i, participante in enumerate(participantes):
            if participante.get("nombre") == pred["nombre"] or participante.get("archivo") == pred["archivo"]:
                participantes[i] = pred
                reemplazado = True
                break
        if not reemplazado:
            participantes.append(pred)

        avisos_por_participante = datos.setdefault("avisos", {})
        if avisos:
            avisos_por_participante[pred["nombre"]] = avisos
        else:
            avisos_por_participante.pop(pred["nombre"], None)
        datos["generado"] = datetime.now().isoformat(timespec="seconds")
        guardar_predicciones(datos)

        accion = "actualizada" if reemplazado else "añadida"
        extra = f" con {len(avisos)} aviso(s)" if avisos else ""
        flash(f"Porra de {pred['nombre']} {accion}{extra}.", "ok")
        return redirect(url_for("subir_participante"))

    datos = cargar_predicciones() or predicciones_vacias()
    participantes = sorted(p["nombre"] for p in datos.get("participantes", []) if p.get("nombre"))
    return render_template("subir_participante.html", participantes=participantes)


@app.route("/comparativa")
def comparativa():
    datos = cargar_predicciones()
    if datos is None:
        return render_template("sin_datos.html")
    resultados = cargar_resultados()
    participantes = datos["participantes"]

    exactos_lista = [
        {"clave": P.clave_partido(loc, vis), "label": f"{loc} – {vis}"}
        for loc, vis in P.EXACTOS_CAMPOS.values()
    ]

    rondas_clasif = {}
    for ronda in ["octavos", "cuartos", "semifinales", "final"]:
        teams = set()
        for p in participantes:
            for e in p["segunda"].get(f"clasif_{ronda}", []):
                if e:
                    teams.add(e)
        real = {e for e in resultados.get("clasificados", {}).get(ronda, []) if e}
        teams |= real
        rondas_clasif[ronda] = {"teams": sorted(teams), "real": real}

    goles_preguntas = [
        {"campo": "goles3_dieciseisavos", "label": "3+ goles en 1/16",
         "real": resultados.get("goles3", {}).get("dieciseisavos")},
        {"campo": "goles3_octavos", "label": "3+ goles en 1/8",
         "real": resultados.get("goles3", {}).get("octavos")},
        {"campo": "goles3_cuartos", "label": "3+ goles en 1/4",
         "real": resultados.get("goles3", {}).get("cuartos")},
        {"campo": "goles_semifinales", "label": "Goles totales semis",
         "real": resultados.get("goles_semifinales")},
        {"campo": "goles_final", "label": "Goles en la final",
         "real": resultados.get("goles_final")},
    ]

    def ncorto(nombre):
        if "(" in nombre:
            return nombre.split("(")[1].rstrip(")")
        return nombre.split()[0]

    return render_template(
        "comparativa.html",
        participantes=participantes,
        resultados=resultados,
        P=P,
        exactos_lista=exactos_lista,
        rondas_clasif=rondas_clasif,
        goles_preguntas=goles_preguntas,
        ncorto=ncorto,
        generado=datos.get("generado"),
    )


if __name__ == "__main__":
    api_football.lanzar_actualizador(RESULTADOS)
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
