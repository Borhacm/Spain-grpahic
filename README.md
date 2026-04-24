# Spain Data Editorial Backend (MVP+Editorial Intelligence)

Backend unificado para una plataforma editorial de datos sobre España (referentes de producto: newsletters de data storytelling).

Incluye dos capas en el mismo proyecto:

- **Data Backend Layer**: conectores, pipelines, normalizacion, almacenamiento y API de datos.
- **Editorial Intelligence Layer**: deteccion de señales, story candidates, scoring, borradores, review queue y adaptadores de publicacion.

## Stack

- FastAPI + SQLAlchemy + PostgreSQL
- Alembic para migraciones
- httpx + pandas + pydantic
- APScheduler (jobs editoriales programados cuando `SCHEDULER_ENABLED=true`)
- pytest, black, ruff
- Docker + docker-compose

## Estructura

```text
app/
  api/
    routes/
  editorial/
    api/
    models/
    repositories/
    schemas/
    services/
      signal_detector.py
      score_engine.py
      cross_suggester.py
      draft_generator.py
      review_service.py
      publication_service.py
      candidate_service.py
    tasks/
  core/
  db/
  models/
  schemas/
  services/
  connectors/
    datosgob/
    ine/
    aemet/
    bde/
    cnmv/
    registradores/
    bme/
  pipelines/
  tasks/
  utils/
  main.py
alembic/
tests/
```

## Modelo de datos inicial

Incluye tablas:

- `sources`, `source_runs`
- `datasets`, `dataset_resources`
- `series`, `series_observations`
- `geographies`, `categories`, `organizations`
- `companies`, `company_aliases`, `company_identifiers`, `company_snapshots`
- `filings`
- `articles`, `article_chart_specs`, `tags`
- `story_candidates`, `candidate_signals`, `candidate_scores`
- `candidate_related_series`, `candidate_related_companies`
- `candidate_crosses`, `candidate_drafts`
- `editorial_reviews`
- `publication_targets`, `published_stories`
- `signal_rules`

## Levantar local con Docker

1. Copia variables:

```bash
cp .env.example .env
```

2. Levanta servicios:

```bash
docker compose up --build
```

Esto levanta:
- API backend (`http://localhost:8000`)
- Scheduler editorial
- Frontend público Next.js (`http://localhost:3000`)

Variables útiles del frontend público en compose: `NEXT_PUBLIC_STORIES_API_BASE_URL`, `NEXT_PUBLIC_SITE_URL`, identificación legal (`NEXT_PUBLIC_LEGAL_*`, `NEXT_PUBLIC_CONTACT_*`) y analítica opcional (`NEXT_PUBLIC_ANALYTICS_PROVIDER`, Plausible o GA4).

3. Ejecuta migraciones:

```bash
docker compose exec api alembic upgrade head
```

4. (Opcional) Seeds iniciales:

```bash
docker compose exec api python -m app.tasks.seed
```

API disponible en `http://localhost:8000` y docs en `http://localhost:8000/docs`.
Fachada pública disponible en `http://localhost:3000`.

### Comandos rapidos con Make

```bash
make up       # build + levantar stack
make init     # migraciones + seed
make ps       # estado de servicios
make health   # check de health endpoint
make doctor   # diagnostico rapido (docker + servicios + health)
make logs     # logs en streaming
make down     # apagar stack
make reset    # reset completo (volumen + build + migrate + seed)
```

## Frontend público separado (España en un gráfico)

El frontend público está en `public-frontend/` y no comparte stack de render con la consola interna.

Páginas incluidas:
- `home` (`/`)
- `story page` (`/stories/[slug]`)
- `topic pages` (`/topics/[topic]`)
- `sobre` (`/sobre`), `metodología` (`/metodologia`), legales en borrador (`/legal/*`), `feed.xml` (RSS)

Consume la API pública (prefijo `/public`, solo historias con `status=published`):
- `GET /public/stories?page=&page_size=&topic=&tag=`
- `GET /public/stories/{slug}`
- `GET /public/stories/by-topic/{topic}` (alias cómodo del listado con filtro por tema)

Arquitectura runtime recomendada:
- `api` para tráfico HTTP
- `scheduler` dedicado para jobs editoriales periódicos

## Levantar local sin Docker

1. Crea y activa entorno virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Instala dependencias:

```bash
pip install -e ".[dev]"
```

3. Copia variables:

```bash
cp .env.example .env
```

4. Asegura PostgreSQL local en `localhost:5432` y ejecuta migraciones:

```bash
alembic upgrade head
```

5. Arranca la API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Seguridad y operacion base

- Si `API_KEYS` esta vacio, la API editorial no exige autenticacion (modo local/dev).
- Si `API_KEYS` se define, los endpoints editoriales exigen cabecera `x-api-key`.
- Formato recomendado: `API_KEYS="token-admin:admin,token-editor:editor,token-viewer:viewer"`.
- Roles:
  - `viewer`: lectura
  - `editor`: ejecucion de pipelines, scoring, drafts, revisiones
  - `admin`: operaciones destructivas de reglas (delete/rollback)
- Se incluye middleware de `x-request-id`, manejo global de errores y CORS configurable por entorno.
- Scheduler activable con `SCHEDULER_ENABLED=true` para jobs editoriales diarios/semanales.
- Ingestas programadas recomendadas para ficha país:
  - INE: diario (`SCHEDULER_INGEST_INE_CRON`, por defecto `15 6 * * *`).
  - BdE: 3 veces por semana (`SCHEDULER_INGEST_BDE_CRON`, por defecto `45 6 * * 1,3,5`).
  - OECD: semanal (`SCHEDULER_INGEST_OECD_CRON`, por defecto `30 7 * * 1`).
  - Para BdE debes definir `SCHEDULER_BDE_CODES` (lista de códigos separada por comas).
  - Para OECD puedes definir `SCHEDULER_OECD_CODES` (por defecto `GOV_DGOGD_2025:DG:ESP,GOV_DGOGD_2025:OUR:ESP`).
- Rate limit HTTP opcional en memoria con `RATE_LIMIT_ENABLED=true`.

## Endpoints implementados

### Salud
- `GET /health`
- `GET /health/sources`
- `GET /health/ops`

### Catalogo
- `GET /sources`
- `GET /datasets`
- `GET /datasets/{id}`
- `GET /series`
- `GET /series/{id}`
- `GET /series/{id}/observations`

### Empresas
- `GET /companies`
- `GET /companies/{id}`
- `GET /companies/{id}/snapshots`
- `GET /companies/{id}/filings`
- `GET /companies/search?q=`

### Story-ready
- `GET /story/series/{id}/latest`
- `GET /story/series/{id}/summary`
- `GET /story/series/{id}/compare?geo=...`
- `GET /story/rankings/companies?metric=filings_count`
- `GET /story/explore?topic=economia`
- `GET /story/chart/{id}/spec`

### Editorial intelligence

#### Señales
- `GET /signals`
- `POST /signals/run`
- `POST /signals/simulate?series_id=...`
- `GET /signals/{id}`
- `GET /signal-rules`
- `GET /signal-rules/{id}`
- `POST /signal-rules`
- `PUT /signal-rules/{id}`
- `DELETE /signal-rules/{id}`
- `POST /signal-rules/{id}/recompute`
- `GET /signal-rules/{id}/revisions`
- `GET /signal-rule-revisions/{id}`
- `GET /signal-rules/{id}/revisions/{rev_a}/diff/{rev_b}`
- `GET /signal-rules/{id}/timeline`
- `POST /signal-rules/{id}/impact-preview`
- `GET /signal-rules/{id}/impact-previews`
- `GET /signal-rule-impact-previews/{id}`
- `POST /signal-rule-impact-previews/{id}/evaluate`
- `GET /signal-rule-impact-previews/{id}/evaluations`
- `GET /signal-rule-impact-evaluations/{id}`
- `GET /signal-rules/impact-accuracy-leaderboard`
- `GET /signal-rules/{id}/impact-accuracy-trend`
- `GET /signal-rules/impact-accuracy-alerts`
- `POST /signal-rules/{id}/rollback/{revision_id}`

#### Story candidates
- `GET /candidates`
- `GET /candidates/{id}`
- `POST /candidates/run`
- `POST /candidates/{id}/score`
- `POST /candidates/{id}/draft`
- `POST /candidates/{id}/crosses`
- `POST /candidates/{id}/approve`
- `POST /candidates/{id}/discard`
- `POST /candidates/{id}/shortlist`
- `POST /candidates/{id}/send-to-cms`
- `POST /candidates/{id}/publish` (publicar en la capa web `public_stories`; rol editor)

#### Review queue y dashboard
- `GET /editorial/queue`
- `GET /editorial/dashboard`
- `GET /editorial/dashboard/full`

#### Publicación
- `GET /published`
- `GET /published/{id}`

### Fachada pública (frontend externo)
- `GET /public/stories` (paginado; query `topic`, `tag`)
- `GET /public/stories/{slug}`
- `GET /public/stories/by-topic/{topic}`
- `GET /public/country-overview` (payload unificado para dashboard de ficha país)
- `GET /public/country-overview/mapping-status` (diagnóstico de mapeo a series internas)
- `GET /public/country-overview?strict=true` (en QA/CI falla con `422` si hay mappings sin resolver)

Variables opcionales para enriquecer `GET /public/country-overview`:
- `COUNTRY_OVERVIEW_SERIES_MAP` mapea ids de indicadores a series internas (`id=source_slug:external_code`) separadas por comas.
  - Ejemplo: `gdp=bde:be123,inflation=ine:ipc01,resumen-gdp=bde:be123`
- `COUNTRY_OVERVIEW_BDE_URL`, `COUNTRY_OVERVIEW_INE_URL`, `COUNTRY_OVERVIEW_EUROSTAT_URL`, `COUNTRY_OVERVIEW_OECD_URL`, `COUNTRY_OVERVIEW_FMI_URL` para aplicar parches JSON por fuente.

Tabla **`public_stories`** (`PublicStory`): historias listas para la web, separadas del adaptador CMS (`published_stories`). Incluye `body_markdown`, `primary_chart_spec` / `secondary_chart_spec`, `chart_type`, `sources`, `summary`, `language`, `published_at`, `status`, trazabilidad vía `candidate_id` (no expuesta en la API pública). Flujo: candidato aprobado → `POST /candidates/{id}/publish` → consumo por el front en `/public/stories*`. Detalle en `docs/OPERATIONS.md` (sección Historias públicas).

## Pipelines y CLI

Ejemplos:

```bash
python -m app.tasks.run ingest_datosgob_catalog
python -m app.tasks.run ingest_ine_series --code XXXX
python -m app.tasks.run ingest_bde_series --code XXXX
python -m app.tasks.run ingest_oecd_series --code "GOV_DGOGD_2025:DG:ESP"
python -m app.tasks.run ingest_fmi_series --code NGDP_RPCH --country ESP
python -m app.tasks.run ingest_aemet_stations
python -m app.tasks.run ingest_cnmv_issuers
python -m app.tasks.run backfill_story_summaries
python -m app.tasks.run detect_daily_signals
python -m app.tasks.run detect_weekly_signals
python -m app.tasks.run refresh_scores
python -m app.tasks.run generate_candidate_drafts
python -m app.tasks.run suggest_crosses
python -m app.tasks.run archive_low_score_candidates
python -m app.tasks.run evaluate_rule_accuracy_alerts
```

Pipelines funcionales en MVP:
- `ingest_datosgob_catalog`
- `ingest_ine_series`
- `ingest_bde_series`
- `ingest_oecd_series`
- `ingest_fmi_series`
- `ingest_cnmv_issuers` (si `CNMV_REGISTRY_URL` esta configurado)

Stubs listos para extension:
- `ingest_aemet_stations`, `ingest_aemet_observations`
- `ingest_cnmv_issuers`
- `ingest_registradores_companies`
- `ingest_bme_listed_companies`

Jobs editoriales:
- `detect_daily_signals`
- `detect_weekly_signals`
- `refresh_scores`
- `generate_candidate_drafts`
- `suggest_crosses`
- `archive_low_score_candidates`
- `evaluate_rule_accuracy_alerts`

Politica de recomendacion de chart (middleware editorial, `chart_policy=topic_default_v2`):
- Se aplica durante `run_signal_pipeline` sobre `StoryCandidate.chart_type_suggested` (alias de `suggested_chart_type`).
- Orden de evaluacion tematica:
  1. housing
  2. climate (AEMET)
  3. companies (CNMV/BME/Registradores)
  4. economy/macro
  5. fallback generico
- Reglas principales:
  - housing: temporal `line`, comparativas `bar`, evolucion relativa `multi_line`, relacion de metricas `scatter`
  - climate: temperatura temporal `line`, precipitacion agregada `column`, comparativas regionales `bar`, extremos `line_with_annotations`, espacial `map`
  - companies: precio/beneficio temporal `line`, ranking `bar`, relacion entre metricas `scatter`, comparativa sectorial matricial `heatmap`
  - economy: temporal `line`, comparacion por categoria `bar`, multiserie relativa `multi_line`, relacion de indicadores `scatter`
  - fallback: temporal `line`, comparacion categorica `bar`
- Se guarda racional breve en `StoryCandidate.chart_spec_json["chart_rationale"]`.
- Consola interna `GET /editorial/ui/chart-audit`: distribuciones por chart/policy, tabla de audit y **semaforo de calidad** (% rationales con mencion a fallback, % sin `chart_rationale`, top rationales y top reglas por senales en la muestra). Umbrales aproximados: OK si fallback bajo 15% y sin rationale bajo 10%; atencion si fallback bajo 35% y sin rationale bajo 25%; critico en caso contrario.
- Filtros GET opcionales: `chart_type` (valor `__unset__` = sin tipo sugerido) y `chart_policy` (`__unset__` = sin policy en JSON). Export: `GET /editorial/ui/chart-audit/export` con los mismos query params (CSV UTF-8 con BOM, hasta 2000 filas filtradas).

Reglas activas en detector (fase 2 inicial):
- variacion fuerte periodo a periodo
- variacion interanual
- maximos/minimos en ventana
- ruptura de tendencia
- anomalia estadistica por z-score (rolling)
- divergencia entre series comparables
- nuevos filings
- cambios en snapshots de tejido empresarial

Las reglas son configurables desde `signal_rules.params_json` (ejemplos):
- `mom_threshold_pct`
- `yoy_threshold_pct`
- `trend_threshold_pct`
- `zscore_threshold`
- `divergence_threshold_pct`

## Calidad

```bash
pip install -e ".[dev]"
ruff check .
black .
pytest
```

## Operacion

- Runbook: `docs/OPERATIONS.md`

### Hardening pre-release checklist

1. Validar cadena de migraciones en entorno limpio:

```bash
alembic history
alembic upgrade head
```

2. Ejecutar tests de API editorial y reglas:

```bash
pytest tests/test_signal_rules_api.py tests/test_editorial_end_to_end.py
```

3. Ejecutar integración con PostgreSQL real:

```bash
export DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/spain_graphic"
pytest tests/test_postgres_integration.py
```

Nota de compatibilidad Alembic: el revision ID canónico histórico de `0005_signal_rule_impact_evaluations.py`
es `0005_signal_rule_impact_eval`. Mantener esta referencia evita drift entre entornos ya migrados y nuevos.

## Notas importantes de fase 1 MVP

- CNMV/Registradores/BME quedan con adapters desacoplados preparados para parsing prudente.
- AEMET ya soporta API key via `.env` (`AEMET_API_KEY`) y flujo de doble llamada.
- Se conserva `raw_payload_json` / `raw_metadata_json` para trazabilidad de cada fuente.
- `source_runs` guarda estado de ejecucion, contadores y errores resumidos.
- El sistema **no publica automaticamente**: requiere accion humana (`/candidates/{id}/send-to-cms`) y deja `editorial_reviews`.
- Deduplicacion inicial de candidatos por `dedupe_hash` (tipo señal + serie + geografia + periodo).
- Publicacion desacoplada con adapter base (dry-run) y extension prevista a Notion/Ghost/WordPress/Supabase/frontend propio.

## Siguientes pasos recomendados

1. Añadir reglas avanzadas (`signal_rules`) para anomalías robustas y divergencias entre series.
2. Mejorar deduplicacion con similitud semantica de candidates.
3. Completar adapters reales de publicacion (Notion/Ghost/WordPress/Supabase).
4. Ampliar catálogo de jobs programados (ingestas, QA de datos, alertas) según necesidades operativas.
5. Añadir tests de integracion para flujo end-to-end: señal -> candidate -> review -> published.
