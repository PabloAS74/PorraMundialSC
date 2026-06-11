# -*- coding: utf-8 -*-
"""Motor de puntuación de la porra.

Reglas (del propio formulario):
  1ª fase (máx. 202): 1 pt por 1X2; 3+2+1 por orden de grupo; bonus 58
    (grupo +/- goleador 3+3, 12 resultados exactos x4, selección más goleadora 4).
  2ª fase (máx. 220): clasificados 1/8 x3, 1/4 x5, semis x10, final x20,
    campeón 30; partidos con 3+ goles en 1/16 (5), 1/8 (4) y 1/4 (3);
    goles en semifinales (5) y en la final (5).
  Fase final (máx. 76): máximo goleador 40, tréboles 12x3.

Los resultados reales se meten tal y como los pide el formulario:
1/X/2 por partido, marcador exacto solo en los 12 partidos del bonus,
orden de cada grupo, clasificados de cada ronda, contadores de goles, etc.
"""
import plantilla as P


def _norm_set(equipos):
    return {P.normalizar(e) for e in equipos if e}


def puntuar(pred, r):
    """Calcula la puntuación de un participante con los resultados `r`.
    Devuelve un dict con el desglose por concepto y los totales por fase."""
    conceptos = []

    def add(fase, concepto, pron, real, pts, maximo):
        conceptos.append({"fase": fase, "concepto": concepto, "pronostico": pron,
                          "real": real, "puntos": pts, "maximo": maximo})

    # ---------- 1ª FASE ----------
    reales_1x2 = r.get("grupos_1x2", {})
    pts_1x2 = 0
    jugados = 0
    for letra, partidos in P.PARTIDOS_GRUPO.items():
        signos_pred = pred["grupos"][letra]["signos"]
        for loc, vis in partidos:
            clave = P.clave_partido(loc, vis)
            real = reales_1x2.get(clave)
            if real:
                jugados += 1
                if signos_pred.get(clave) == real:
                    pts_1x2 += P.PTS_1X2
    add("1ª fase", "Aciertos 1X2", None, f"{jugados}/72 jugados", pts_1x2, 72)

    ordenes = r.get("orden", {})
    pts_orden = 0
    for letra in P.GRUPOS:
        orden_real = ordenes.get(letra)
        if not orden_real or not all(orden_real[:3]):
            continue
        orden_pred = pred["grupos"][letra]["orden"]
        for pos in range(3):
            if orden_pred[pos] and P.normalizar(orden_pred[pos]) == P.normalizar(orden_real[pos]):
                pts_orden += P.PTS_ORDEN[pos]
    add("1ª fase", "Orden de grupos (3+2+1)", None, None, pts_orden, 72)

    exactos_reales = r.get("exactos", {})
    pts_exactos = 0
    for clave, m_pred in pred["bonus"]["exactos"].items():
        m_real = exactos_reales.get(clave)
        if m_pred and m_real and list(m_pred) == list(m_real):
            pts_exactos += P.PTS_EXACTO
    add("1ª fase", "Resultados exactos (12 x 4)", None, None, pts_exactos, 48)

    gmas_real = r.get("grupo_mas", [])
    pts = P.PTS_GRUPO_MAS if pred["bonus"]["grupo_mas"] in gmas_real else 0
    add("1ª fase", "Grupo más goleador", pred["bonus"]["grupo_mas"],
        ", ".join(gmas_real) or None, pts, 3)

    gmenos_real = r.get("grupo_menos", [])
    pts = P.PTS_GRUPO_MENOS if pred["bonus"]["grupo_menos"] in gmenos_real else 0
    add("1ª fase", "Grupo menos goleador", pred["bonus"]["grupo_menos"],
        ", ".join(gmenos_real) or None, pts, 3)

    equipo_real = r.get("equipo_mas_goles", [])
    pron = pred["bonus"]["equipo_mas_goles"]
    pts = P.PTS_EQUIPO_GOLES if (pron and P.normalizar(pron) in _norm_set(equipo_real)) else 0
    add("1ª fase", "Selección más goleadora (bonus)", pron,
        ", ".join(equipo_real) or None, pts, 4)

    # ---------- 2ª FASE ----------
    clasif = r.get("clasificados", {})
    nombres = {"octavos": "Clasificados 1/8 (16 x 3)", "cuartos": "Clasificados 1/4 (8 x 5)",
               "semifinales": "Semifinalistas (4 x 10)", "final": "Finalistas (2 x 20)"}
    for ronda, pts_regla in P.PTS_CLASIF.items():
        reales = [e for e in clasif.get(ronda, []) if e]
        reales_n = _norm_set(reales)
        pred_lista = pred["segunda"][f"clasif_{ronda}"]
        aciertos = sum(1 for e in pred_lista if e and P.normalizar(e) in reales_n)
        n = len(pred_lista)
        add("2ª fase", nombres[ronda], None, f"{len(reales)}/{n} conocidos",
            aciertos * pts_regla, n * pts_regla)

    campeon_real = r.get("campeon")
    pron = pred["segunda"]["campeon"]
    pts = P.PTS_CAMPEON if (campeon_real and pron and
                            P.normalizar(pron) == P.normalizar(campeon_real)) else 0
    add("2ª fase", "Campeón", pron, campeon_real, pts, 30)

    goles3 = r.get("goles3", {})
    nombres_ronda = {c: n for c, n, _ in P.RONDAS}
    for clave, pts_regla in P.PTS_GOLES3.items():
        real = goles3.get(clave)
        pron = pred["segunda"][f"goles3_{clave}"]
        pts = pts_regla if (real is not None and pron is not None and pron == real) else 0
        add("2ª fase", f"Partidos con 3+ goles en {nombres_ronda[clave]}", pron, real, pts, pts_regla)

    real = r.get("goles_semifinales")
    pron = pred["segunda"]["goles_semifinales"]
    pts = P.PTS_GOLES_SEMIS if (real is not None and pron is not None and pron == real) else 0
    add("2ª fase", "Goles totales en semifinales", pron, real, pts, P.PTS_GOLES_SEMIS)

    real = r.get("goles_final")
    pron = pred["segunda"]["goles_final"]
    pts = P.PTS_GOLES_FINAL if (real is not None and pron is not None and pron == real) else 0
    add("2ª fase", "Goles en la final", pron, real, pts, P.PTS_GOLES_FINAL)

    # ---------- FASE FINAL ----------
    correctos = {g.strip() for g in r.get("goleador_correctos", [])}
    pron = (pred["fase_final"]["goleador"] or "").strip()
    pts = P.PTS_GOLEADOR if (pron and pron in correctos) else 0
    add("Fase final", "Máximo goleador", pron or None,
        ", ".join(sorted(correctos)) if correctos else None, pts, 40)

    trebol_g = r.get("trebol_ganadores", {})
    pts_treb = 0
    for i, idx_pred in enumerate(pred["fase_final"]["treboles"]):
        if idx_pred is not None and idx_pred in trebol_g.get(str(i + 1), []):
            pts_treb += P.PTS_TREBOL
    add("Fase final", "Tréboles (12 x 3)", None, None, pts_treb, 36)

    fase1 = sum(c["puntos"] for c in conceptos if c["fase"] == "1ª fase")
    fase2 = sum(c["puntos"] for c in conceptos if c["fase"] == "2ª fase")
    fase_final = sum(c["puntos"] for c in conceptos if c["fase"] == "Fase final")
    return {
        "nombre": pred["nombre"],
        "conceptos": conceptos,
        "fase1": fase1,
        "fase2": fase2,
        "fase_final": fase_final,
        "total": fase1 + fase2 + fase_final,
    }


def clasificacion(predicciones, resultados):
    filas = [puntuar(p, resultados) for p in predicciones]
    filas.sort(key=lambda f: (-f["total"], -f["fase2"], f["nombre"].lower()))
    return filas
