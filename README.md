# Porra Mundial USA-México-Canadá 2026

Sistema para extraer los pronósticos de los PDFs de la porra y llevar la
clasificación automáticamente durante el torneo.

## Uso diario (durante el Mundial)

1. Arranca la web:
   ```
   python app.py
   ```
2. Abre http://localhost:5000
3. En **Meter resultados** se apunta lo mismo que pide el formulario de la porra:
   - el **1X2** de cada partido de grupos (la × quita una selección errónea);
   - el **orden final** de cada grupo cuando termine;
   - el **marcador exacto** solo de los 12 partidos del bonus;
   - grupo más/menos goleador y selección más goleadora (admiten empates);
   - los **clasificados** de cada ronda eliminatoria (da igual el orden), campeón
     y los contadores de goles (partidos con 3+ goles, goles en semis y final);
   - al final, máximo goleador y tréboles (marcando los pronósticos acertados).
4. La **Clasificación** se recalcula sola. Pincha en un nombre para ver el desglose de puntos.

### Actualización automática con football-data.org

Si existe `API-KEY` en `.env`, al arrancar `python app.py` se lanza una
actualización automática cada 30 minutos. Eso consume como máximo 48 consultas al
día, por debajo del límite gratuito de 100.

Variables opcionales:

```
FOOTBALL_DATA_DATE_FROM=2026-06-11
FOOTBALL_DATA_DATE_TO=2026-07-19
FOOTBALL_DATA_COMPETITIONS=WC
FOOTBALL_DATA_INTERVAL_SECONDS=1800
```

La sincronización usa una sola llamada a `GET https://api.football-data.org/v4/matches`
con la cabecera `X-Auth-Token`, actualiza `data/resultados.json` y guarda el estado
en la clave `_football_data`. Desde
**Meter resultados** también hay un botón para forzar una actualización manual.


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
| `data/predicciones.json` | pronósticos extraídos |
| `data/resultados.json` | resultados reales (lo que metes en la web) |
| `data/correcciones.json` | retoques manuales a porras (opcional) |

Requisitos: Python con `flask`, `pypdf` y `pdfplumber` (ya instalados).
