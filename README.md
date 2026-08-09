# Descargador de Jurisprudencia — Corte Constitucional de Colombia (Fase 1)

MVP funcional de punta a punta: busca providencias en el buscador oficial de la
Relatoría de la Corte Constitucional, descarga el HTML original de cada una,
extrae sus metadatos (incluida la taxonomía oficial de temas/subtemas), las
clasifica en un área de primer nivel (reglas de palabras clave + IA de
respaldo para casos ambiguos) y las organiza en carpetas con un índice SQLite
consultable.

## Cómo funciona (resumen de la investigación del sitio)

- Buscador: `https://www.corteconstitucional.gov.co/relatoria/buscador_new/`
  (GET con parámetros, resultados en HTML plano — no requiere JS).
- **El botón "Exportar a Excel" está bloqueado por el WAF del sitio**
  (`POST` a `views/search/result_export_excel.php` devuelve
  `HTTP 500 "The URL you requested has been blocked"`, incluso enviando
  headers de navegador). Por eso el proyecto usa scraping HTML de:
  - la tabla de resultados de la búsqueda,
  - la "ficha" de detalle de cada providencia (expediente, magistrados,
    fechas, resuelve) — endpoint AJAX `accion=ver_modal_detalle_providencia`,
  - las "titulaciones" oficiales tema(descriptor)/subtema(restrictor) —
    endpoint AJAX `accion=ver_titulacionesXIDprovidencia`.
- **Importante sobre el User-Agent**: el WAF del sitio bloquea (HTTP 500)
  cualquier User-Agent que contenga la subcadena `CCBot` (coincide con el
  crawler de Common Crawl) y también rechaza user-agents que no empiecen por
  un token tipo navegador (`Mozilla/5.0 (...)`). El User-Agent configurado en
  `src/config.py` ya evita ambos problemas; si lo cambia, vuelva a probarlo
  contra el sitio antes de automatizar.
- `robots.txt` (revisado manualmente) permite explícitamente `/relatoria/`
  (`Allow: /relatoria/`, no aparece en ningún `Disallow`).

## Estructura de salida

```
jurisprudencia/
  corte-constitucional/
    <area-de-primer-nivel>/
      <tema-oficial-slug>/
        T-388-19.htm            # HTML original, bytes tal cual (windows-1252)
        T-388-19_metadata.json  # metadatos estructurados
data/
  indice.sqlite                 # índice consultable (radicado, fechas, área, tema, ruta, etc.)
```

Las áreas de primer nivel son una agrupación propuesta (la Corte no clasifica
por área tradicional del derecho, sino por derechos y figuras
constitucionales); los niveles "tema" y "subtema" reales usados para el
`metadata.json` y el índice son siempre los oficiales de la Relatoría
("titulaciones").

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Clasificación por IA (opcional, para casos ambiguos): configure
`ANTHROPIC_API_KEY` en el entorno. Sin esa variable, el programa sigue
funcionando normalmente: usa solo las reglas de palabras clave y, si no hay
coincidencia clara, marca el caso como `otros-sin-clasificar` (o con el
método `reglas_ambiguo` si hubo alguna coincidencia parcial) para revisión
manual.

## Uso

```bash
# Búsqueda puntual (ejemplo de prueba end-to-end)
python -m src.cli --buscar-por "T-388 DE 2019" --finicio 1992-01-01 --ffin 2023-04-17

# Simulación sin escribir en disco/DB
python -m src.cli --buscar-por "LIBERTAD DE EXPRESION" --dry-run

# Modo incremental: solo trae providencias nuevas desde la última fecha de
# publicación registrada en el índice (pensado para cron externo; este
# proyecto NO trae un scheduler interno)
python -m src.cli --buscar-por "T-" --incremental

# Desactivar la clasificación por IA (solo reglas)
python -m src.cli --buscar-por "T-388 DE 2019" --no-ia
```

Argumentos principales (ver `python -m src.cli --help` para todos):

| Argumento | Descripción |
|---|---|
| `--buscar-por` | Término de búsqueda (número de providencia, tema, etc.) |
| `--finicio` / `--ffin` | Rango de fechas `YYYY-MM-DD` (por defecto `1992-01-01` a hoy) |
| `--search-option` | Modo de búsqueda del buscador (por defecto `prov_sentencia`; solo ese valor fue confirmado manualmente — pruebe otros en el navegador antes de usarlos) |
| `--cant-providencias` | Máximo de resultados por consulta (tope 5000 según el buscador) |
| `--incremental` | Solo descarga providencias nuevas desde la última `fecha_publicacion` en el índice |
| `--forzar-reprocesar` | Vuelve a descargar/clasificar providencias ya indexadas |
| `--no-ia` | Desactiva el clasificador de IA (solo reglas) |
| `--dry-run` | Consulta el buscador pero no descarga HTML ni escribe en disco/DB |
| `--rate-limit` | Segundos mínimos entre solicitudes (por defecto 1.5) |

## Automatización (cron externo)

El script no trae scheduler interno por diseño. Para correr periódicamente,
apunte un cron externo a, por ejemplo:

```
0 3 * * 1 cd /ruta/al/proyecto && .venv/bin/python -m src.cli --buscar-por "T-" --incremental >> log_cron.txt 2>&1
```

## Cumplimiento y buenas prácticas de scraping

- User-Agent identificable (ver nota sobre el WAF arriba).
- Límite de tasa configurable (por defecto 1.5s entre solicitudes) y
  reintentos con backoff exponencial en errores 5xx/timeouts.
- `robots.txt` revisado manualmente antes de programar el scraper; `/relatoria/`
  está explícitamente permitido.

## Estructura del código

```
src/
  config.py              # constantes del sitio (URLs, user-agent, límites)
  cli.py                 # punto de entrada (argparse)
  pipeline.py            # orquesta: buscar -> ficha -> titulaciones -> clasificar -> guardar -> indexar
  scraper/
    client.py            # sesión HTTP con rate limit + reintentos
    robots.py            # verificación programática de robots.txt
    search.py            # búsqueda y parseo de la tabla de resultados
    detail.py            # ficha/detalle de una providencia
    titulaciones.py      # temas/subtemas oficiales (taxonomía de la Relatoría)
    download.py          # descarga del HTML original de la providencia
  classify/
    areas.py             # las 10 áreas de primer nivel propuestas
    rules.py             # clasificación por palabras clave
    ai_classifier.py      # clasificación por IA (Anthropic) para casos ambiguos
    classify.py           # orquesta reglas -> IA -> fallback
  storage/
    db.py                 # esquema e índice SQLite
    files.py               # organización de carpetas + metadata.json
```

## Fase 2 (fuera de alcance de este MVP)

Extender el mismo patrón a la Corte Suprema de Justicia, que tiene un
buscador distinto por Sala (Civil, Laboral, Penal).
