# Porra Mundial USA-México-Canadá 2026

Sistema para extraer los pronósticos de los PDFs de la porra y llevar la
clasificación automáticamente durante el torneo.

## Contexto del proyecto

Este proyecto nace para poder hacer seguimiento de las porras del Mundial de
mis amigos desde una aplicación web sencilla, con carga de pronósticos,
clasificación automática y actualización de resultados mediante API.

La mayor parte del desarrollo se ha hecho con ayuda de asistentes de programación basados en IA como Claude Code y Codex. Además de resolver una necesidad real durante el torneo, el proyecto sirve como excusa práctica para experimentar con Docker, Linux, nginx y el despliegue de una aplicación en un VPS de AWS.


## Uso diario (durante el Mundial)

La aplicación ha sido desplegada en un VPS para tener accesibilidad contínua y es accesible a través de un internet, sin embargo, no puedo compartir la url para proteger la identidad de los participantes de la porra.

No obstante, para crear tu propia porra puedes desplegar la app en local de la siguiente forma:

1. Clona el repositorio:
```bash
  git clone https://github.com/PabloAS74/PorraMundialSC.git
```
2. Crea un archivo .env en la raíz del proyecto y configura una contraseña y una api-key de la api football-org en caso de querer disponer de actualización automática:
```
PASSWORD=
API-KEY=
```
Para obtener la api de football-org puedes crear una cuenta free tier en https://www.football-data.org/

3. Arranca la web:
   ```
   python app.py
   ```
4. Abre http://localhost:5000
5. Como admin puedes pulsar en la sección **Entrar** para introducir participantes y meter resultados
6. En la subsección **Meter participantes** puedes introducir los pdfs rellenos por cada uno de los participantes de la porra. Estos pdfs son las participaciones rellenadas sobre 'Formulario USA 2026.pdf' que puedes encontrar en este repositorio.
7. En **Meter resultados** puedes comprobar los resultados introducidos vía API (si dispones de una API-KEY) o actualizarlos tú mismo.
8. La **Clasificación** se recalcula sola. Pincha en un nombre para ver el desglose de puntos.


### Actualización automática con football-data.org

Si existe `API-KEY` en `.env`, al arrancar `python app.py` se lanza una
actualización automática cada 10 minutos. El límite de la API se encuentra en 10 consultas para la free tier, por lo que se puede reducir el tiempo si se desea.

Variables opcionales:

```
FOOTBALL_DATA_DATE_FROM=2026-06-11
FOOTBALL_DATA_DATE_TO=2026-07-19
FOOTBALL_DATA_COMPETITIONS=WC
FOOTBALL_DATA_INTERVAL_SECONDS=1800
```

La sincronización usa una sola llamada a `GET https://api.football-data.org/v4/matches`con la cabecera `X-Auth-Token`, actualiza `data/resultados.json` y guarda el estado en la clave `_football_data`. Desde **Meter resultados** también hay un botón para forzar una actualización manual.


## Reglas de puntuación (las del propio formulario)

- **1ª fase (máx. 202):** 1 pt por acierto 1X2 (72 partidos); 3+2+1 por orden de cada
  grupo; bonus: grupo más/menos goleador (3+3), 12 resultados exactos (4 c/u),
  selección más goleadora de las 11 propuestas (4).
- **2ª fase (máx. 220):** clasificados a 1/8 (3 c/u), 1/4 (5 c/u), semis (10 c/u),
  final (20 c/u); campeón (30); nº de partidos con 3+ goles en 1/16 (5), 1/8 (4) y
  1/4 (3); goles totales en semis (5) y en la final (5).
- **Fase final (máx. 76):** máximo goleador (40) y 12 tréboles (3 c/u).

Notas de funcionamiento:

- Cada concepto puntúa en cuanto se rellena su dato real; lo que esté en blanco
  aparece como "pendiente" en el desglose.
- El orden de grupo puntúa cuando están elegidas las 3 primeras posiciones.
- Goleador y tréboles: se marcan los pronósticos acertados (admite empates:
  se puede marcar más de uno).

## Ficheros

| Fichero | Qué es |
|---|---|
| `extraer.py` | PDFs → `data/predicciones.json` |
| `gen_geometria.py` | regenera `data/geometria.json` desde un PDF con formulario |
| `plantilla.py` | datos fijos: grupos, partidos, tréboles, puntuaciones |
| `puntuacion.py` | motor de puntuación |
| `app.py` | web local (Flask) |

(Carpeta generada al introducir participantes y resultados)
| `data/predicciones.json` | pronósticos extraídos |
| `data/resultados.json` | resultados reales (lo que metes en la web) |
| `data/correcciones.json` | retoques manuales a porras (opcional) |

Requisitos: Python con `flask`, `requests`, `pypdf` y `pdfplumber` (ya instalados).
