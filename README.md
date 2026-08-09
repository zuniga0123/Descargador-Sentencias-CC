# Descargador de Jurisprudencia — Corte Constitucional de Colombia (Fase 1)

Programa en Python que busca, descarga y clasifica providencias de la Corte
Constitucional desde el buscador oficial de la Relatoría
(`https://www.corteconstitucional.gov.co/relatoria/buscador_new/`), usando la
taxonomía oficial de tema/subtema, y las organiza en:

```
jurisprudencia/
  corte-constitucional/
    <area>/
      <tema>/
        [<subtema>/]
          T-388-19.htm
          T-388-19_metadata.json
  indice.sqlite
```

## ⚠️ Estado actual / limitaciones conocidas

Este proyecto se construyó **sin poder acceder al sitio real** de la Corte
Constitucional: el entorno de desarrollo bloqueó (403 a nivel de proxy de
egress) las conexiones a `corteconstitucional.gov.co` durante toda la sesión,
pese a intentar ajustar la política de red del entorno. Como consecuencia:

- Los parámetros de búsqueda confirmados (`config.SEARCH_OPTIONS`) solo
  incluyen el valor confirmado en el brief (`prov_sentencia`). Los demás
  modos de "Buscar en" (Temas/Subtema, Texto del resuelve, Normas demandadas,
  Número de sentencia) están **sin confirmar**.
- El parsing de HTML (`parsing.py`) y de la exportación a Excel
  (`excel_export.py`) están escritos con heurísticas tolerantes (por regex
  sobre el href de la providencia, mapeo dinámico de encabezados de Excel,
  extracción de campos por etiqueta de texto en vez de selectores CSS
  fijos), **pero no fueron validados contra el marcado real del sitio**.
- No se pudo verificar `robots.txt` en vivo (queda el comando
  `verificar-robots` listo para correrlo apenas haya acceso).

**Antes de una corrida real hay que calibrar**, en este orden:

```bash
python main.py verificar-robots
python main.py inspeccionar-formulario
python main.py descargar --tema "T-388 DE 2019" --desde 1992-01-01 --hasta 2023-04-17 --cant-providencias 5 --log-level DEBUG
```

y revisar con `--log-level DEBUG` (o abriendo el `.xlsx`/HTML descargado a
mano) si `parsing.py` / `excel_export.py` están leyendo los campos
correctos. Los puntos más probables a ajustar están marcados con comentarios
`NOTE`/docstrings en esos dos archivos.

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

```bash
python main.py descargar \
  --tema "LIBERTAD DE EXPRESION" \
  --desde 2015-01-01 \
  --hasta 2023-12-31 \
  --out-dir ./jurisprudencia \
  --cant-providencias 500
```

Flags relevantes:

- `--sin-ia`: desactiva la clasificación por IA de respaldo (deja los casos
  ambiguos como `sin_clasificar` para revisión manual).
- `--incremental`: antes de buscar, ajusta la fecha inicial a la última
  `fecha_publicacion` ya indexada en el SQLite (para corridas programadas
  que solo bajen lo nuevo — ver sección "Automatización").
- `--force`: vuelve a descargar providencias que ya estén en el índice.
- `--rate-limit`: segundos mínimos entre solicitudes (default 1.5).

Utilidades de diagnóstico:

- `python main.py verificar-robots`: descarga `robots.txt` y evalúa si la
  ruta del buscador y de una ficha de ejemplo están permitidas para el
  user-agent del proyecto.
- `python main.py inspeccionar-formulario`: vuelca los `<select>`/`<form>`
  de la página del buscador — útil para confirmar los valores reales de
  `searchOption` y otros campos.

## Automatización (corridas incrementales)

Esta fase no incluye un scheduler interno (decisión tomada con el usuario):
se deja el script listo para invocarse con `--incremental` desde `cron` (o
Task Scheduler) fuera del programa, por ejemplo, semanalmente:

```cron
0 6 * * 1 cd /ruta/al/proyecto && .venv/bin/python main.py descargar --tema "..." --desde 1992-01-01 --hasta $(date +%F) --incremental >> logs/cron.log 2>&1
```

## Clasificación por área del derecho

La Corte Constitucional clasifica por derechos y figuras constitucionales
(tema/subtema oficial de la Relatoría), no por área tradicional. Este
proyecto agrupa esa taxonomía oficial bajo 10 áreas de primer nivel
(`descargador_sentencias_cc/taxonomy.py`):

1. Derechos Fundamentales y Debido Proceso
2. Control de Constitucionalidad Abstracto
3. Derecho Laboral y Seguridad Social
4. Derecho de Familia y Derechos de Niños, Niñas y Adolescentes
5. Derecho Penal y Sistema Acusatorio
6. Derecho Administrativo y Función Pública
7. Derecho Constitucional Económico
8. Derechos Étnicos y Consulta Previa
9. Derecho a la Salud
10. Otros / Sin clasificar

El flujo es: reglas de palabras clave sobre tema/subtema/resumen primero; si
ninguna regla aplica y la IA está activa, se llama a la API de Claude
(`ai_classifier.py`) con el tema oficial y el resumen (no el HTML completo).
Requiere la variable de entorno `ANTHROPIC_API_KEY`. Si la IA falla o está
desactivada, el caso queda marcado como `sin_clasificar` para revisión
manual.

## Arquitectura

```
descargador_sentencias_cc/
  config.py        constantes: URL base, user-agent, rate limit, search options
  http_client.py   requests.Session con rate limit + reintentos/backoff
  models.py        SearchResult / Providencia (dataclasses)
  parsing.py       parsing de resultados HTML y de la ficha individual
  excel_export.py  descubrir y parsear la exportación a Excel del buscador
  search.py        arma la URL de búsqueda; intenta Excel, cae a HTML
  taxonomy.py       reglas de palabras clave -> área
  ai_classifier.py  clasificación por IA (Claude) para casos ambiguos
  storage.py        índice SQLite + organización de carpetas
  pipeline.py        orquesta: buscar -> descargar -> clasificar -> guardar
  cli.py             argparse: descargar / inspeccionar-formulario / verificar-robots
```

## Tests

```bash
pytest -q
```

Los tests de parsing usan fixtures HTML **sintéticas**
(`tests/fixtures/*.html`), escritas a mano a partir de la descripción del
brief — no son HTML capturado del sitio real (ver limitación arriba).

## Fuera de alcance (Fase 1)

- Corte Suprema de Justicia (Fase 2 del brief, buscador distinto por Sala).
- Scheduler interno (se usa cron externo).
