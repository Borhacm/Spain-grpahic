"""Schemas Pydantic para la capa pública de historias (`/public/stories`) y publicación editorial."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChartAxisLabels(BaseModel):
    """Etiquetas opcionales de ejes."""

    model_config = ConfigDict(extra="ignore")

    x: str | None = Field(default=None, description="Etiqueta eje X", examples=["Fecha"])
    y: str | None = Field(default=None, description="Etiqueta eje Y", examples=["Valor"])


class ChartSeriesDataset(BaseModel):
    """Una serie de datos para el gráfico (puntos o filas normalizadas)."""

    model_config = ConfigDict(extra="ignore")

    key: str = Field(description="Identificador estable de la serie", examples=["primary"])
    label: str | None = Field(default=None, examples=["IPC anual"])
    points: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Filas con campos alineados con x_field / y_field (p. ej. x=fecha, y=número).",
        examples=[[{"x": "2024-01-01", "y": 3.4}, {"x": "2024-02-01", "y": 3.1}]],
    )


class ChartOptions(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str | None = Field(default=None, examples=["Evolución del indicador"])
    legend: bool | None = Field(default=True)
    axes: dict[str, Any] | None = Field(
        default=None,
        description="Opciones adicionales de ejes (ticks, formato) para el renderizador del front.",
        examples=[{"y_format": "0.0%"}],
    )


class ChartSpec(BaseModel):
    """
    Especificación mínima del gráfico principal/secundario para el frontend (Chart.js, Plotly, etc.).
    No pretende ser Vega-Lite; es explícita y extensible.
    """

    model_config = ConfigDict(extra="allow")

    type: str = Field(
        default="line",
        description="Tipo de gráfico sugerido",
        examples=["line"],
    )
    x_field: str = Field(default="x", description="Nombre del campo en cada punto para el eje X", examples=["x"])
    y_field: str = Field(default="y", description="Nombre del campo en cada punto para el eje Y", examples=["y"])
    series_key: str | None = Field(
        default=None,
        description="Campo que discrimina series si los puntos están fusionados",
        examples=[None],
    )
    labels: ChartAxisLabels | None = None
    series: list[ChartSeriesDataset] = Field(default_factory=list)
    options: ChartOptions | None = None

    @field_validator("type")
    @classmethod
    def normalize_type(cls, v: str) -> str:
        return (v or "line").strip().lower() or "line"


class PublicCorrelationItem(BaseModel):
    """Comparación con otra serie (texto para público general, coeficiente opcional)."""

    model_config = ConfigDict(extra="ignore")

    series_title: str = Field(min_length=1, max_length=500)
    comparison_text: str = Field(min_length=1, max_length=4000)
    coefficient: float | None = Field(default=None, description="Correlación de Pearson sobre fechas comunes, si aplica")


class PublishCandidatePayload(BaseModel):
    """Contenido editorial final al publicar (no modifica el `StoryCandidate` original)."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=500)
    subtitle: str | None = Field(default=None, max_length=2000)
    dek: str | None = Field(default=None, max_length=500, description="Standfirst / bajada corta")
    body_markdown: str = Field(min_length=1, description="Cuerpo en Markdown")
    topic: str | None = Field(
        default=None,
        max_length=80,
        description="Tema editorial (economy, housing, climate, companies, …)",
        examples=["economy"],
    )
    tags: list[str] | None = Field(default=None, examples=[["macro", "ipc"]])
    summary: str | None = Field(default=None, max_length=500, description="Resumen para listados; si falta se trunca en API")
    primary_chart_spec: ChartSpec | dict[str, Any] | None = Field(
        default=None,
        description="Si se omite, se genera a partir del candidato y series vinculadas.",
    )
    secondary_chart_spec: ChartSpec | dict[str, Any] | None = None
    chart_type: str | None = Field(default=None, max_length=50, examples=["line"])
    sources: list[dict[str, Any]] | None = Field(
        default=None,
        description="Fuentes listas para mostrar (título, url, organismo, etc.)",
        examples=[[{"title": "INE", "url": "https://www.ine.es"}]],
    )
    language: str = Field(default="es", max_length=8)
    slug: str | None = Field(
        default=None,
        max_length=220,
        description="Slug estable; si se omite se deriva del título y del id de candidato en creación.",
    )
    scheduled_at: datetime | None = Field(
        default=None,
        description="Si es futura, la historia queda en estado `scheduled` hasta esa fecha (v1: sin worker).",
    )
    save_as_draft: bool = Field(
        default=False,
        description="Si es True, guarda como `draft` sin `published_at` (no visible en API pública).",
    )
    narrative_context: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Textos de fachada opcionales; si se omiten, la API los genera al servir el detalle. "
            "Claves: chart_public_caption, analysis_economic, analysis_social, correlations (lista de objetos)."
        ),
    )


class PublicStoryListItem(BaseModel):
    """Elemento de listado para el frontend público."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    subtitle: str | None
    dek: str | None
    topic: str | None
    tags: list[str] | None
    published_at: datetime | None
    updated_at: datetime | None = None
    summary: str | None = None
    preview_chart_type: str | None = Field(
        default=None,
        description="Tipo de gráfico principal para teasers",
        examples=["line"],
    )


class PublicStoryDetail(BaseModel):
    """Historia completa expuesta al público (sin `candidate_id`)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    subtitle: str | None
    dek: str | None
    body_markdown: str
    topic: str | None
    tags: list[str] | None
    primary_chart_spec: dict[str, Any]
    secondary_chart_spec: dict[str, Any] | None
    chart_type: str | None
    sources: list[dict[str, Any]] | None
    summary: str | None
    chart_public_caption: str = Field(
        default="",
        description="Qué muestra el gráfico, en lenguaje claro para lectores no técnicos.",
    )
    analysis_economic: str = Field(default="", description="Lectura económica orientativa")
    analysis_social: str = Field(default="", description="Lectura social / ciudadana orientativa")
    correlations: list[PublicCorrelationItem] = Field(default_factory=list)
    published_at: datetime | None
    language: str
    updated_at: datetime


class PublicStoryListResponse(BaseModel):
    items: list[PublicStoryListItem]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class PublishPublicStoryResponse(BaseModel):
    public_story_id: int
    slug: str
    status: str
    published_at: datetime | None = None
    scheduled_at: datetime | None = None


class CountryOverviewSeriesPoint(BaseModel):
    model_config = ConfigDict(extra="ignore")

    period: str
    value: float


class PublicCountryOverviewKpi(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    value: str
    delta: str
    trend: list[float] = Field(default_factory=list)
    updated_at: str
    source: str
    status: str


class PublicCountryOverviewIndicator(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    value: str
    change: str
    period: str
    series: list[CountryOverviewSeriesPoint] = Field(default_factory=list)
    source: str
    status: str
    note: str


class PublicCountryOverviewSection(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    description: str
    indicators: list[PublicCountryOverviewIndicator] = Field(default_factory=list)


class PublicCountryOverviewResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    executive_kpis: list[PublicCountryOverviewKpi]
    executive_narrative: list[str]
    sections: list[PublicCountryOverviewSection]


class PublicCountryOverviewMappingStatusItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    indicator_id: str
    source_slug: str
    external_code: str
    mapped: bool
    latest_date: str | None = None
    points_loaded: int = 0
    is_stale: bool = False
    age_days: int = 0
    max_age_days: int = 0
    reason: str | None = None


class PublicCountryOverviewMappingStatusResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    configured_mappings: int
    resolved_mappings: int
    items: list[PublicCountryOverviewMappingStatusItem]
