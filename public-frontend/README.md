# España en un gráfico — frontend público

Aplicación pública separada de la consola editorial interna. La marca visible del sitio se define en `lib/site.ts` (`SITE_NAME`).

## Ejecutar local

```bash
cd public-frontend
npm install
npm run dev
```

Por defecto consume `http://localhost:8000`.

Si la API está en otra URL:

```bash
NEXT_PUBLIC_STORIES_API_BASE_URL=https://api.tu-dominio.com npm run dev
```

URL pública del sitio (Open Graph, sitemap, `metadataBase`):

```bash
NEXT_PUBLIC_SITE_URL=https://tu-dominio.com npm run dev
```

La vista de ficha país está disponible en `/espana`. Por defecto usa datos seed (`lib/country-overview.ts`) y puede mezclar datos live por fuente cuando se configuran endpoints JSON:

```bash
COUNTRY_OVERVIEW_BDE_URL=https://...
COUNTRY_OVERVIEW_INE_URL=https://...
COUNTRY_OVERVIEW_EUROSTAT_URL=https://...
COUNTRY_OVERVIEW_OECD_URL=https://...
COUNTRY_OVERVIEW_FMI_URL=https://...
```

Si el backend expone `GET /public/country-overview`, el frontend lo consume primero automáticamente (usa `NEXT_PUBLIC_STORIES_API_BASE_URL`). También se puede forzar una URL concreta con:

```bash
COUNTRY_OVERVIEW_API_URL=https://api.tu-dominio.com/public/country-overview
```

Cada endpoint puede devolver parches parciales por `id` sobre `executiveKpis`, `executiveNarrative` y `sections[].indicators[]`; si una fuente falla, el dashboard conserva los datos seed.

Incluye `sitemap.xml`, `robots.txt`, `feed.xml` (RSS 2.0), metadatos Open Graph por historia, imágenes OG/Twitter generadas (`opengraph-image`, `twitter-image`), JSON-LD (`WebSite`, `Article`, `BreadcrumbList` donde aplica), pie con Sobre, Metodología, RSS y enlaces legales.

**Legal y cookies:** aviso legal y privacidad en español (RGPD / LSSI), indexables; bloque identificativo del titular vía `NEXT_PUBLIC_LEGAL_*` y `NEXT_PUBLIC_CONTACT_*`. Banner de consentimiento (`espana_grafico_consent_v1` en `localStorage`) y carga opcional de **Plausible** o **GA4** según `NEXT_PUBLIC_ANALYTICS_PROVIDER`.

## Componentes de presentación (`app/components/`)

Librería interna para el frontend público (estilo editorial / newsletter, sin “dashboard UI”). Todo el aspecto visual vive en `app/globals.css` bajo clases `story-*`.

| Componente    | Rol breve | Dónde se usa |
|---------------|-----------|----------------|
| `StoryHero`   | Título grande, bajada (`dek` o `subtitle`) y meta (fecha, tema, tags) | `app/stories/[slug]/page.tsx` |
| `StoryCard`   | Tarjeta enlazable: título, bajada corta, meta fecha + tema + tags (layout `card` en `StoryMeta`) | Solo vía `StoryList` (presentación pura) |
| `StoryList`   | Lista homogénea a partir de `PublicStoryListItem[]` | `app/page.tsx`, `app/topics/[topic]/page.tsx` |
| `StoryMeta`   | Fecha (`formatDate`), pill de tema, tags en línea; `layout`: `default` / `hero` / `card` | `StoryHero`, `StoryCard` |
| `StoryChart`  | Contenedor del gráfico (`caption`, `ariaHeadingId`, `className`); `hasStoryChartSpec()` para comprobar specs no vacíos | `app/stories/[slug]/page.tsx` (principal + `secondary_chart_spec` opcional) |

**Extender:** añade props opcionales a los componentes y estilos en `globals.css` con prefijo `story-` para no mezclar con el resto del sitio. Para nuevos listados, reutiliza `StoryList` o mapea manualmente a `StoryCard` si necesitas variantes. Fechas: centraliza en `lib/format-date.ts` (`formatDate`).

**Diseño:** tipografía acotada (título display + cuerpo sans), fondos cálidos del tema existente, sombras suaves y bordes discretos; las tarjetas evitan bordes fríos tipo panel y no añaden iconografía decorativa.

## Tests (Vitest)

```bash
cd public-frontend
npm test
```

Pruebas en `tests/`: `formatDate` (fechas inválidas + patrón legible) y `StoryMeta` (roles y contenido, sin depender de la zona horaria). `ChartFromSpec` admite `ariaHeadingId` para que principal y complementario no dupliquen el mismo `id` en la ficha.
