# Operations Runbook

## Servicios (Docker Compose)

- `db`: PostgreSQL principal.
- `api`: FastAPI HTTP service (`SCHEDULER_ENABLED=false`).
- `scheduler`: worker dedicado a jobs editoriales (`SCHEDULER_ENABLED=true`).

## Arranque

1. `cp .env.example .env`
2. `docker compose up --build -d`
3. `docker compose exec api alembic upgrade head`
4. (Opcional) `docker compose exec api python -m app.tasks.seed`

### Cambios en `.env` (p. ej. `COUNTRY_OVERVIEW_SERIES_MAP`)

Las variables definidas en `env_file` se **inyectan al crear el contenedor**. Un `docker compose restart api` **no** vuelve a leer el `.env` del host. Tras editar el mapa de series u otras claves de entorno:

- `docker compose up -d --force-recreate api`

(o bajar y subir el stack).

## Carga real mínima (INE)

Para poblar la consola con un lote real inicial (3 series INE) y generar pipeline editorial completo:

- Local:
  - `python -m app.tasks.run bootstrap_real_ine`
- Docker:
  - `docker compose exec api python -m app.tasks.run bootstrap_real_ine`

Este comando:
- ingiere series reales `CP335`, `IPC206449`, `EPA87` (ocupados EPA, miles de personas), `EPA77038` (tasa de actividad EPA)
- ejecuta detección de señales
- enriquece candidates con score, draft y cruces

### Carga real + historia en `public_stories` (middleware → fachada)

Tras `alembic upgrade head` (incluye tabla `public_stories`), para **ingestar INE**, aceptar el **último candidato** y crear una fila en **`public_stories`**:

- Borrador listo para publicar (no visible en `GET /public/stories` hasta publicar):
  - `docker compose exec api python -m app.tasks.run bootstrap_real_ine_public_story`
- Misma ruta pero **ya publicada** en la API pública (`GET /public/stories`):
  - `docker compose exec api python -m app.tasks.run bootstrap_real_ine_public_story --publish`

## Mantenimiento: deduplicación histórica de observaciones

Para limpiar duplicados antiguos de `series_observations` (solo slice base `revision_date = NULL`):

- Simulación (sin borrar):
  - `python -m app.tasks.run maintenance_dedupe_observations --dry-run`
- Ejecución real:
  - `python -m app.tasks.run maintenance_dedupe_observations`

Regla aplicada:
- para cada `(series_id, obs_date)` con más de una fila base, conserva la fila más nueva y elimina el resto.

## Healthchecks

- API básica: `GET /health`
- Fuentes: `GET /health/sources`
- Operativo scheduler/locking: `GET /health/ops`

`/health/ops` expone:
- estado del scheduler (running/jobs)
- backend de locking (`postgresql_advisory_lock` en Postgres)
- probe de adquisición de lock

## Jobs programados (scheduler)

Con `SCHEDULER_ENABLED=true` en el servicio `scheduler`, el stack ejecuta:

- `detect_daily_signals`: lunes–domingo a las **07:05** (Europe/Madrid)
- `refresh_scores`: lunes–domingo a las **07:20**
- `detect_weekly_signals`: **lunes** a las **07:30**
- `maintenance_dedupe_observations`: **domingo** a las **03:15** (deduplicación histórica de observaciones base)

El comando manual equivalente a la deduplicación sigue siendo:

- `python -m app.tasks.run maintenance_dedupe_observations`

## Seguridad mínima

- Define `API_KEYS` en `.env` para exigir `x-api-key`.
- Formato: `token-admin:admin,token-editor:editor,token-viewer:viewer`
- Roles:
  - `viewer`: lectura
  - `editor`: ejecución y revisión
  - `admin`: operaciones destructivas (p.ej. rollback/delete de reglas)

## Editorial Console (UI interna)

Consola server-rendered para operación editorial básica, montada sobre el backend existente.

- URL base: `GET /editorial/ui/`
- Queue (fase 1): `GET /editorial/ui/queue`
- Candidate detail (fase 1): `GET /editorial/ui/candidates/{candidate_id}`
- Signals (fase 2): `GET /editorial/ui/signals`
- Published (fase 2): `GET /editorial/ui/published`
- Dashboard visual: `GET /editorial/ui/dashboard`

Autenticación/roles:
- Reutiliza el mismo esquema de `x-api-key` y roles del backend.
- `viewer`: puede abrir queue y detalle.
- `editor`: además puede ejecutar acciones desde UI (`shortlist`, `approve`, `discard`, `send-to-cms`, **Publicar en la web**).

Flujo básico de operación:
1. Abrir `GET /editorial/ui/queue` y filtrar por estado/score/fecha.
2. Entrar a detalle con **Ver detalle**.
3. Ejecutar revisión editorial (`shortlist`, `approve`, `discard`).
4. Si aplica, enviar con **Send to CMS** desde la vista de candidate.
4b. (Opcional) Con candidato **accepted**, usar el formulario **Publicar en la web** en el mismo detalle: envía `POST /editorial/ui/candidates/{id}/publish-web` y actualiza `public_stories` (misma lógica que `POST /candidates/{id}/publish`).
5. Revisar señales recientes en `GET /editorial/ui/signals` y ejecutar `run` o `simulate`.
6. Ver histórico de publicados en `GET /editorial/ui/published`.
7. Revisar tendencia y actividad en `GET /editorial/ui/dashboard`.

Notas:
- Esta UI no sustituye la API; la lógica de scoring/detección/publicación sigue en servicios existentes.
- `signals` y `published` son vistas operativas mínimas para uso interno.
- Candidate detail y signals incluyen charts básicos con Chart.js (serie principal/sparklines).

## Historias públicas (`public_stories`) y API `/public`

Capa limpia entre el middleware editorial (`story_candidates`, señales, scoring, etc.) y el frontend público.

**Flujo recomendado**

1. Revisar el candidato en la consola o vía API (`shortlist` / `approve` como corresponda).
2. Cuando el candidato esté en estado `accepted`, publicar con **`POST /candidates/{id}/publish`** (API JSON, rol `editor`) **o** desde la consola con el formulario **Publicar en la web** (`POST /editorial/ui/candidates/{id}/publish-web`, mismos datos en campos de formulario).
3. El servicio crea o actualiza la fila en **`public_stories`** (como mucho **una** historia pública por `candidate_id`) y deja auditoría en `editorial_reviews` (`action=publish_public_story`).
4. El frontend consume solo **`GET /public/stories`**, **`GET /public/stories/{slug}`** y **`GET /public/stories/by-topic/{topic}`** (solo filas con `status=published`).

**Notas**

- Es independiente de **`POST .../send-to-cms`** y de la tabla **`published_stories`** (adaptadores CMS / dry-run).
- `slug` es único y, por defecto, estable por candidato; `status` y `published_at` deben cumplir las restricciones de BD (`published` exige fecha).
- Variables de entorno del frontend deben apuntar al mismo host de API; rutas públicas llevan prefijo **`/public`**.

## Incidencias comunes

- **Jobs duplicados**: validar que existe una sola réplica de `scheduler`; si hay varias por diseño, el advisory lock de Postgres evita doble ejecución del mismo job.
- **No corre scheduler**: comprobar `SCHEDULER_ENABLED=true` en servicio `scheduler`.
- **429 frecuentes**: ajustar `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS` o desactivar temporalmente `RATE_LIMIT_ENABLED`.
- **Errores de ingest CNMV**: revisar `CNMV_REGISTRY_URL` y formato JSON de respuesta.
