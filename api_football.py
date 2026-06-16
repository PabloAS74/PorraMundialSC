# -*- coding: utf-8 -*-
"""Actualizacion de resultados desde football-data.org."""
import json
import os
import threading
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import plantilla as P


BASE_URL = "https://api.football-data.org/v4/competitions/WC/matches"
DEFAULT_INTERVAL_SECONDS = 10 * 60
DEFAULT_DATE_FROM = "2026-06-11"
DEFAULT_DATE_TO = "2026-07-19"
FINISHED_STATUSES = {"FINISHED", "AWARDED"}
META_KEY = "_football_data"


ALIASES_API = {
    "algeria": "Argelia",
    "argentina": "Argentina",
    "australia": "Australia",
    "austria": "Austria",
    "belgium": "Bélgica",
    "bosnia and herzegovina": "Bosnia",
    "bosnia-herzegovina": "Bosnia",
    "bosnia herzegovina": "Bosnia",
    "brazil": "Brasil",
    "canada": "Canadá",
    "cape verde": "Cabo Verde",
    "cape verde islands": "Cabo Verde",
    "colombia": "Colombia",
    "congo dr": "RD Congo",
    "cote d ivoire": "Costa de Marfil",
    "cote d'ivoire": "Costa de Marfil",
    "côte d'ivoire": "Costa de Marfil",
    "croatia": "Croacia",
    "curacao": "Curaçao",
    "czech republic": "Rep. Checa",
    "czechia": "Rep. Checa",
    "democratic republic of the congo": "RD Congo",
    "dr congo": "RD Congo",
    "ecuador": "Ecuador",
    "egypt": "Egipto",
    "england": "Inglaterra",
    "france": "Francia",
    "germany": "Alemania",
    "ghana": "Ghana",
    "haiti": "Haití",
    "holland": "Países Bajos",
    "iran": "Irán",
    "ir iran": "Irán",
    "iraq": "Iraq",
    "ivory coast": "Costa de Marfil",
    "japan": "Japón",
    "jordan": "Jordania",
    "korea republic": "Corea del Sur",
    "korea, republic of": "Corea del Sur",
    "mexico": "México",
    "morocco": "Marruecos",
    "netherlands": "Países Bajos",
    "new zealand": "Nueva Zelanda",
    "norway": "Noruega",
    "panama": "Panamá",
    "paraguay": "Paraguay",
    "portugal": "Portugal",
    "qatar": "Qatar",
    "republic of korea": "Corea del Sur",
    "republic of the congo": "RD Congo",
    "saudi arabia": "Arabia Saudí",
    "scotland": "Escocia",
    "senegal": "Senegal",
    "south africa": "Sudáfrica",
    "south korea": "Corea del Sur",
    "spain": "España",
    "sweden": "Suecia",
    "switzerland": "Suiza",
    "tunisia": "Túnez",
    "turkey": "Turquía",
    "turkiye": "Turquía",
    "türkiye": "Turquía",
    "united states": "Estados Unidos",
    "united states of america": "Estados Unidos",
    "uruguay": "Uruguay",
    "usa": "Estados Unidos",
    "uzbekistan": "Uzbekistán",
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _api_key():
    return (
        os.environ.get("API-KEY")
        or os.environ.get("FOOTBALL_DATA_TOKEN")
        or os.environ.get("FOOTBALL_DATA_API_KEY")
    )


def _canon_equipo(nombre):
    if not nombre:
        return None
    canon = P.equipo_canonico(nombre)
    if canon:
        return canon
    alias = ALIASES_API.get(P.normalizar(nombre))
    return alias or P.equipo_canonico(alias)


def _match_finished(match):
    return match.get("status") in FINISHED_STATUSES


def _goles(match):
    full_time = (match.get("score") or {}).get("fullTime") or {}
    local, visitante = full_time.get("home"), full_time.get("away")
    if local is None or visitante is None:
        return None
    return int(local), int(visitante)


def _home_team(match):
    return _canon_equipo((match.get("homeTeam") or {}).get("name"))


def _away_team(match):
    return _canon_equipo((match.get("awayTeam") or {}).get("name"))


def _ganador(match):
    winner = (match.get("score") or {}).get("winner")
    if winner == "HOME_TEAM":
        return _home_team(match)
    if winner == "AWAY_TEAM":
        return _away_team(match)

    goles = _goles(match)
    if not goles:
        return None
    if goles[0] > goles[1]:
        return _home_team(match)
    if goles[1] > goles[0]:
        return _away_team(match)
    return None


def _resultado_1x2(goles):
    if goles[0] > goles[1]:
        return "1"
    if goles[1] > goles[0]:
        return "2"
    return "X"


def _grupo_de_equipo(equipo):
    for letra, equipos in P.GRUPOS.items():
        if equipo in equipos:
            return letra
    return None


def _es_partido_grupo(local, visitante):
    letra = _grupo_de_equipo(local)
    return letra if letra and _grupo_de_equipo(visitante) == letra else None


def _partido_grupo_canonico(local, visitante):
    """Devuelve el partido tal como esta definido en la plantilla."""
    grupo = _es_partido_grupo(local, visitante)
    if not grupo:
        return None
    equipos = {local, visitante}
    for loc, vis in P.PARTIDOS_GRUPO[grupo]:
        if {loc, vis} == equipos:
            return grupo, loc, vis
    return None


def _goles_orientados(goles, local_api, visitante_api, local_tpl, visitante_tpl):
    if local_api == local_tpl and visitante_api == visitante_tpl:
        return goles
    if local_api == visitante_tpl and visitante_api == local_tpl:
        return goles[1], goles[0]
    return None


def _round_text(match):
    valores = [
        match.get("stage"),
        match.get("group"),
        str(match.get("matchday") or ""),
    ]
    return P.normalizar(" ".join(v for v in valores if v))


def _ronda_eliminatoria(match):
    texto = _round_text(match)
    if any(x in texto for x in ("last 32", "round of 32", "1/16", "dieciseisavos")):
        return "dieciseisavos"
    if any(x in texto for x in ("last 16", "round of 16", "1/8", "octavos")):
        return "octavos"
    if any(x in texto for x in ("quarter", "1/4", "cuartos")):
        return "cuartos"
    if any(x in texto for x in ("semi", "semifinal")):
        return "semifinales"
    if "final" in texto and "third" not in texto and "3rd" not in texto:
        return "final"
    return None


def _tabla_grupo(equipos):
    return {e: {"pts": 0, "gf": 0, "gc": 0, "pj": 0} for e in equipos}


def _aplicar_partido_tabla(tabla, local, visitante, goles):
    gl, gv = goles
    tabla[local]["pj"] += 1
    tabla[visitante]["pj"] += 1
    tabla[local]["gf"] += gl
    tabla[local]["gc"] += gv
    tabla[visitante]["gf"] += gv
    tabla[visitante]["gc"] += gl
    if gl > gv:
        tabla[local]["pts"] += 3
    elif gv > gl:
        tabla[visitante]["pts"] += 3
    else:
        tabla[local]["pts"] += 1
        tabla[visitante]["pts"] += 1


def _ordenar_tabla(tabla):
    return sorted(
        tabla,
        key=lambda e: (
            -tabla[e]["pts"],
            -(tabla[e]["gf"] - tabla[e]["gc"]),
            -tabla[e]["gf"],
            e,
        ),
    )


def _fetch_matches():
    key = _api_key()
    if not key:
        raise RuntimeError("Falta API-KEY en .env")

    params = {}
    competitions = os.environ.get("FOOTBALL_DATA_COMPETITIONS")
    if competitions:
        params["competitions"] = competitions
    params["dateFrom"] = os.environ.get("FOOTBALL_DATA_DATE_FROM", DEFAULT_DATE_FROM)
    params["dateTo"] = os.environ.get("FOOTBALL_DATA_DATE_TO", DEFAULT_DATE_TO)

    url = BASE_URL
    if params:
        url = f"{url}?{urlencode(params)}"

    req = Request(url, headers={"X-Auth-Token": key})
    try:
        with urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"football-data.org devolvio HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"No se pudo conectar con football-data.org: {exc.reason}") from exc

    return payload.get("matches", [])


def _limpiar_meta_antigua(r):
    r.pop("_api_football", None)


def _esta_vacio(valor):
    return valor is None or valor == "" or valor == [] or valor == {}


def _poner_si_vacio(diccionario, clave, valor):
    if _esta_vacio(diccionario.get(clave)):
        diccionario[clave] = valor


def _fusionar_resultados(actuales, matches):
    r = dict(actuales)
    _limpiar_meta_antigua(r)
    r.setdefault("grupos_1x2", {})
    r.setdefault("exactos", {})
    r.setdefault("orden", {})
    r.setdefault("clasificados", {"octavos": [], "cuartos": [], "semifinales": [], "final": []})
    r.setdefault("goles3", {})
    r.setdefault("grupo_mas", [])
    r.setdefault("grupo_menos", [])
    r.setdefault("equipo_mas_goles", [])
    for ronda in ("octavos", "cuartos", "semifinales", "final"):
        r["clasificados"].setdefault(ronda, [])

    tablas = {letra: _tabla_grupo(equipos) for letra, equipos in P.GRUPOS.items()}
    goles_grupo = {letra: 0 for letra in P.GRUPOS}
    partidos_grupo_jugados = {letra: 0 for letra in P.GRUPOS}
    goles_equipo = {equipo: 0 for equipos in P.GRUPOS.values() for equipo in equipos}
    ganadores = {"dieciseisavos": [], "octavos": [], "cuartos": [], "semifinales": []}
    goles3 = {"dieciseisavos": 0, "octavos": 0, "cuartos": 0}
    jugados_ronda = {"dieciseisavos": 0, "octavos": 0, "cuartos": 0, "semifinales": 0, "final": 0}
    goles_semis = 0
    goles_final = None
    campeon = None

    exactos_claves = {P.clave_partido(*partido) for partido in P.EXACTOS_CAMPOS.values()}

    for match in matches:
        if not _match_finished(match):
            continue
        local = _home_team(match)
        visitante = _away_team(match)
        goles = _goles(match)
        if not local or not visitante or goles is None:
            continue

        partido_grupo = _partido_grupo_canonico(local, visitante)
        if partido_grupo:
            grupo, local_tpl, visitante_tpl = partido_grupo
            goles_tpl = _goles_orientados(goles, local, visitante, local_tpl, visitante_tpl)
            if goles_tpl is None:
                continue
            clave = P.clave_partido(local_tpl, visitante_tpl)
            _poner_si_vacio(r["grupos_1x2"], clave, _resultado_1x2(goles_tpl))
            if clave in exactos_claves:
                _poner_si_vacio(r["exactos"], clave, [goles_tpl[0], goles_tpl[1]])
            _aplicar_partido_tabla(tablas[grupo], local_tpl, visitante_tpl, goles_tpl)
            partidos_grupo_jugados[grupo] += 1
            goles_grupo[grupo] += goles_tpl[0] + goles_tpl[1]
            goles_equipo[local_tpl] += goles_tpl[0]
            goles_equipo[visitante_tpl] += goles_tpl[1]
            continue

        ronda = _ronda_eliminatoria(match)
        if not ronda:
            continue
        jugados_ronda[ronda] += 1
        total_goles = goles[0] + goles[1]
        if ronda in goles3 and total_goles >= 3:
            goles3[ronda] += 1
        if ronda == "semifinales":
            goles_semis += total_goles
        if ronda == "final":
            goles_final = total_goles
            campeon = _ganador(match)
        else:
            ganador = _ganador(match)
            if ganador and ronda in ganadores:
                ganadores[ronda].append(ganador)

    for letra, jugados in partidos_grupo_jugados.items():
        if jugados == 6:
            _poner_si_vacio(r["orden"], letra, _ordenar_tabla(tablas[letra])[:3])

    if all(v == 6 for v in partidos_grupo_jugados.values()):
        max_goles = max(goles_grupo.values())
        min_goles = min(goles_grupo.values())
        if _esta_vacio(r.get("grupo_mas")):
            r["grupo_mas"] = [g for g, total in goles_grupo.items() if total == max_goles]
        if _esta_vacio(r.get("grupo_menos")):
            r["grupo_menos"] = [g for g, total in goles_grupo.items() if total == min_goles]
        bonus_goles = {e: goles_equipo[e] for e in P.BONUS_EQUIPOS}
        max_bonus = max(bonus_goles.values())
        if _esta_vacio(r.get("equipo_mas_goles")):
            r["equipo_mas_goles"] = [e for e, total in bonus_goles.items() if total == max_bonus]

    mapa_clasificados = {
        "dieciseisavos": "octavos",
        "octavos": "cuartos",
        "cuartos": "semifinales",
        "semifinales": "final",
    }
    for ronda, destino in mapa_clasificados.items():
        if ganadores[ronda]:
            _poner_si_vacio(r["clasificados"], destino, ganadores[ronda])

    esperados = {"dieciseisavos": 16, "octavos": 8, "cuartos": 4}
    for ronda, n in esperados.items():
        if jugados_ronda[ronda] == n:
            _poner_si_vacio(r["goles3"], ronda, goles3[ronda])

    if jugados_ronda["semifinales"] == 2:
        if _esta_vacio(r.get("goles_semifinales")):
            r["goles_semifinales"] = goles_semis
    if jugados_ronda["final"] == 1:
        if _esta_vacio(r.get("goles_final")):
            r["goles_final"] = goles_final
        if _esta_vacio(r.get("campeon")):
            r["campeon"] = campeon

    meta = dict(r.get(META_KEY) or {})
    meta.update({
        "last_success": _now_iso(),
        "date_from": os.environ.get("FOOTBALL_DATA_DATE_FROM", DEFAULT_DATE_FROM),
        "date_to": os.environ.get("FOOTBALL_DATA_DATE_TO", DEFAULT_DATE_TO),
        "competitions": os.environ.get("FOOTBALL_DATA_COMPETITIONS"),
        "matches": len(matches),
    })
    r[META_KEY] = meta
    return r


def actualizar_resultados(resultados_path):
    """Hace una llamada a football-data.org y actualiza resultados.json."""
    path = Path(resultados_path)
    actuales = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    matches = _fetch_matches()
    nuevos = _fusionar_resultados(actuales, matches)
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(nuevos, ensure_ascii=False, indent=1), encoding="utf-8")
    return nuevos[META_KEY]


def _leer_meta(path):
    try:
        datos = json.loads(Path(path).read_text(encoding="utf-8"))
        return datos.get(META_KEY) or datos.get("_api_football") or {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _segundos_desde_ultimo_exito(path):
    last_success = _leer_meta(path).get("last_success")
    if not last_success:
        return None
    try:
        dt = datetime.fromisoformat(last_success)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds()


def _interval_seconds(interval_seconds):
    return int(
        interval_seconds
        or os.environ.get("FOOTBALL_DATA_INTERVAL_SECONDS")
        or os.environ.get("API_FOOTBALL_INTERVAL_SECONDS", DEFAULT_INTERVAL_SECONDS)
    )


def lanzar_actualizador(resultados_path, interval_seconds=None):
    """Arranca un hilo daemon que actualiza como maximo una vez por intervalo."""
    if not _api_key():
        return None
    interval = _interval_seconds(interval_seconds)
    if interval <= 0:
        return None

    def loop():
        while True:
            espera = 0
            transcurrido = _segundos_desde_ultimo_exito(resultados_path)
            if transcurrido is not None and transcurrido < interval:
                espera = interval - transcurrido
            if espera:
                time.sleep(espera)
            try:
                actualizar_resultados(resultados_path)
            except Exception as exc:
                path = Path(resultados_path)
                datos = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
                _limpiar_meta_antigua(datos)
                meta = dict(datos.get(META_KEY) or {})
                meta.update({"last_error": str(exc), "last_error_at": _now_iso()})
                datos[META_KEY] = meta
                path.parent.mkdir(exist_ok=True)
                path.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
            time.sleep(interval)

    hilo = threading.Thread(target=loop, name="football-data-updater", daemon=True)
    hilo.start()
    return hilo
