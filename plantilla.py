# -*- coding: utf-8 -*-
"""Datos fijos de la plantilla del formulario 'Porra mundial USA-México-Canadá 2026'."""

# Equipos por grupo (nombres canónicos = los de los desplegables del PDF)
GRUPOS = {
    "A": ["México", "Rep. Checa", "Corea del Sur", "Sudáfrica"],
    "B": ["Canadá", "Suiza", "Qatar", "Bosnia"],
    "C": ["Brasil", "Marruecos", "Haití", "Escocia"],
    "D": ["Estados Unidos", "Turquía", "Paraguay", "Australia"],
    "E": ["Alemania", "Ecuador", "Costa de Marfil", "Curaçao"],
    "F": ["Países Bajos", "Japón", "Suecia", "Túnez"],
    "G": ["Bélgica", "Egipto", "Irán", "Nueva Zelanda"],
    "H": ["España", "Uruguay", "Arabia Saudí", "Cabo Verde"],
    "I": ["Francia", "Noruega", "Senegal", "Iraq"],
    "J": ["Argentina", "Austria", "Argelia", "Jordania"],
    "K": ["Portugal", "Colombia", "Uzbekistán", "RD Congo"],
    "L": ["Inglaterra", "Croacia", "Ghana", "Panamá"],
}

# Los 6 partidos de cada grupo, en el orden en que aparecen en el formulario
# (coincide con los campos GroupX1..GroupX6)
PARTIDOS_GRUPO = {
    "A": [("México", "Sudáfrica"), ("Corea del Sur", "Rep. Checa"), ("Rep. Checa", "Sudáfrica"),
          ("México", "Corea del Sur"), ("Rep. Checa", "México"), ("Sudáfrica", "Corea del Sur")],
    "B": [("Canadá", "Bosnia"), ("Qatar", "Suiza"), ("Suiza", "Bosnia"),
          ("Canadá", "Qatar"), ("Bosnia", "Qatar"), ("Suiza", "Canadá")],
    "C": [("Brasil", "Marruecos"), ("Haití", "Escocia"), ("Escocia", "Marruecos"),
          ("Brasil", "Haití"), ("Marruecos", "Haití"), ("Escocia", "Brasil")],
    "D": [("Estados Unidos", "Paraguay"), ("Australia", "Turquía"), ("Estados Unidos", "Australia"),
          ("Turquía", "Paraguay"), ("Paraguay", "Australia"), ("Turquía", "Estados Unidos")],
    "E": [("Alemania", "Curaçao"), ("Costa de Marfil", "Ecuador"), ("Alemania", "Costa de Marfil"),
          ("Ecuador", "Curaçao"), ("Curaçao", "Costa de Marfil"), ("Ecuador", "Alemania")],
    "F": [("Países Bajos", "Japón"), ("Suecia", "Túnez"), ("Países Bajos", "Suecia"),
          ("Túnez", "Japón"), ("Japón", "Suecia"), ("Túnez", "Países Bajos")],
    "G": [("Bélgica", "Egipto"), ("Irán", "Nueva Zelanda"), ("Bélgica", "Irán"),
          ("Nueva Zelanda", "Egipto"), ("Egipto", "Irán"), ("Nueva Zelanda", "Bélgica")],
    "H": [("España", "Cabo Verde"), ("Arabia Saudí", "Uruguay"), ("España", "Arabia Saudí"),
          ("Uruguay", "Cabo Verde"), ("Cabo Verde", "Arabia Saudí"), ("Uruguay", "España")],
    "I": [("Francia", "Senegal"), ("Iraq", "Noruega"), ("Francia", "Iraq"),
          ("Noruega", "Senegal"), ("Senegal", "Iraq"), ("Noruega", "Francia")],
    "J": [("Argentina", "Argelia"), ("Austria", "Jordania"), ("Argentina", "Austria"),
          ("Jordania", "Argelia"), ("Argelia", "Austria"), ("Jordania", "Argentina")],
    "K": [("Portugal", "RD Congo"), ("Uzbekistán", "Colombia"), ("Portugal", "Uzbekistán"),
          ("Colombia", "RD Congo"), ("RD Congo", "Uzbekistán"), ("Colombia", "Portugal")],
    "L": [("Inglaterra", "Croacia"), ("Ghana", "Panamá"), ("Inglaterra", "Ghana"),
          ("Panamá", "Croacia"), ("Croacia", "Ghana"), ("Panamá", "Inglaterra")],
}


def clave_partido(local, visitante):
    return f"{local}|{visitante}"


# Los 12 partidos con pronóstico de resultado exacto (4 puntos cada uno).
# Mapea nombre del campo del PDF -> partido canónico.
EXACTOS_CAMPOS = {
    "Canadá-Bosnia": ("Canadá", "Bosnia"),
    "México-Corea del Sur": ("México", "Corea del Sur"),
    "Ecuador-Alemania": ("Ecuador", "Alemania"),
    "Brasil-Marruecos": ("Brasil", "Marruecos"),
    "Países Bajos-Suecia": ("Países Bajos", "Suecia"),
    "Turquía-EE.UU": ("Turquía", "Estados Unidos"),
    "Bélgica-Egipto": ("Bélgica", "Egipto"),
    "Túnez-Japón": ("Túnez", "Japón"),
    "Uruguay-España": ("Uruguay", "España"),
    "Austria-Jordania": ("Austria", "Jordania"),
    "Noruega-Senegal": ("Noruega", "Senegal"),
    "Colombia-Portugal": ("Colombia", "Portugal"),
}

# Equipos del bonus "¿cuál marcará más goles en la primera fase?",
# en orden de aparición (izquierda a derecha) en el formulario.
BONUS_EQUIPOS = ["Sudáfrica", "Qatar", "Haití", "Curaçao", "Nueva Zelanda",
                 "Cabo Verde", "Iraq", "Jordania", "RD Congo", "Uzbekistán", "Panamá"]

# Tréboles: 12 tríos (3 puntos por acierto). Orden = campos 'Trebol 1'..'Trebol 12'.
TREBOLES = [
    ["Harry Kane", "Mbappé", "C. Ronaldo"],
    ["Messi", "Kai Havertz", "Vinicius"],
    ["Lamine Yamal", "Haaland", "Memphis Depay"],
    ["Dembelé", "Julián Álvarez", "Raphina"],
    ["Inglaterra", "Bélgica", "Alemania"],
    ["Países Bajos", "España", "Portugal"],
    ["Francia", "Argentina", "Brasil"],
    ["Noruega", "Suecia", "Colombia"],
    ["Egipto", "Argelia", "Senegal"],
    ["Suiza", "Marruecos", "Turquía"],
    ["EE.UU.", "México", "Canadá"],
    ["Corea del Sur", "Japón", "Ecuador"],
]

# Rondas eliminatorias: (clave, nombre, nº de partidos)
RONDAS = [
    ("dieciseisavos", "1/16 de final", 16),
    ("octavos", "1/8 de final", 8),
    ("cuartos", "1/4 de final", 4),
    ("semifinales", "Semifinales", 2),
    ("final", "Final", 1),
]

# Puntuaciones
PTS_1X2 = 1                 # por acierto 1X2 en fase de grupos
PTS_ORDEN = [3, 2, 1]       # 1º, 2º y 3º de grupo acertados
PTS_EXACTO = 4              # resultado exacto
PTS_GRUPO_MAS = 3           # grupo más goleador
PTS_GRUPO_MENOS = 3         # grupo menos goleador
PTS_EQUIPO_GOLES = 4        # selección que más goles marca (bonus)
PTS_CLASIF = {"octavos": 3, "cuartos": 5, "semifinales": 10, "final": 20}
PTS_CAMPEON = 30
PTS_GOLES3 = {"dieciseisavos": 5, "octavos": 4, "cuartos": 3}  # nº partidos con 3+ goles
PTS_GOLES_SEMIS = 5         # goles totales en las dos semifinales
PTS_GOLES_FINAL = 5         # goles en la final
PTS_GOLEADOR = 40           # máximo goleador
PTS_TREBOL = 3              # por trébol acertado

TODOS_EQUIPOS = sorted({e for eqs in GRUPOS.values() for e in eqs})

import unicodedata


def normalizar(texto):
    """Normaliza nombres para comparar: sin acentos, minúsculas, sin puntos ni espacios extra."""
    if texto is None:
        return ""
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower().replace(".", " ").strip()
    t = " ".join(t.split())
    return t


# Alias frecuentes -> nombre canónico
_ALIAS = {
    "ee uu": "Estados Unidos",
    "eeuu": "Estados Unidos",
    "usa": "Estados Unidos",
    "paises bajos": "Países Bajos",
    "arabia s": "Arabia Saudí",
    "n zelanda": "Nueva Zelanda",
    "corea sur": "Corea del Sur",
    "costa marfil": "Costa de Marfil",
}
_CANON = {normalizar(e): e for e in TODOS_EQUIPOS}


def equipo_canonico(texto):
    """Devuelve el nombre canónico del equipo, o None si no se reconoce."""
    n = normalizar(texto)
    if not n:
        return None
    if n in _CANON:
        return _CANON[n]
    if n in _ALIAS:
        return _ALIAS[n]
    return None
