"""Textos de contexto para la fachada pública: lectura general, análisis y correlaciones."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.editorial.models import CandidateRelatedSeries, StoryCandidate
from app.models import Series, SeriesObservation


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 4 or n != len(ys):
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys, strict=True))
    dx = sum((a - mx) ** 2 for a in xs)
    dy = sum((b - my) ** 2 for b in ys)
    if dx <= 0 or dy <= 0:
        return None
    r = num / (dx**0.5 * dy**0.5)
    return max(-1.0, min(1.0, r))


def _corr_strength_es(r: float) -> str:
    a = abs(r)
    if a >= 0.75:
        return "muy fuerte" if a >= 0.9 else "fuerte"
    if a >= 0.45:
        return "moderada"
    if a >= 0.25:
        return "débil"
    return "muy débil"


def _preview_pairs_from_spec(spec: dict[str, Any]) -> tuple[list[tuple[str, float]], str | None]:
    """Devuelve (puntos (fecha_iso, valor), etiqueta de serie) desde `primary_chart_spec`."""
    label: str | None = None
    series = spec.get("series")
    if isinstance(series, list) and series:
        s0 = series[0]
        if isinstance(s0, dict):
            raw_label = s0.get("label")
            if isinstance(raw_label, str) and raw_label.strip():
                label = raw_label.strip()
            pts: list[tuple[str, float]] = []
            for row in s0.get("points") or []:
                if not isinstance(row, dict):
                    continue
                x = row.get("x") or row.get("date")
                y = row.get("y") if row.get("y") is not None else row.get("value")
                if x is None or y is None:
                    continue
                try:
                    pts.append((str(x), float(y)))
                except (TypeError, ValueError):
                    continue
            if pts:
                return pts, label
    preview = spec.get("preview_points")
    out: list[tuple[str, float]] = []
    if isinstance(preview, list):
        for row in preview:
            if not isinstance(row, dict):
                continue
            d, v = row.get("date"), row.get("value")
            if d is None or v is None:
                continue
            try:
                out.append((str(d), float(v)))
            except (TypeError, ValueError):
                continue
    if not label and isinstance(spec.get("series_name"), str):
        label = spec["series_name"].strip() or None
    return out, label


def _primary_series_id(spec: dict[str, Any], candidate: StoryCandidate | None, db: Session) -> int | None:
    raw = spec.get("series_id")
    if raw is not None:
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    if candidate is None:
        return None
    rel = db.scalar(
        select(CandidateRelatedSeries)
        .where(CandidateRelatedSeries.candidate_id == candidate.id)
        .where(CandidateRelatedSeries.relation_type == "primary")
        .limit(1)
    )
    if rel is None:
        rel = db.scalar(
            select(CandidateRelatedSeries)
            .where(CandidateRelatedSeries.candidate_id == candidate.id)
            .order_by(CandidateRelatedSeries.id.asc())
            .limit(1)
        )
    return rel.series_id if rel else None


def _obs_map(db: Session, series_id: int, *, limit: int = 120) -> dict[date, float]:
    rows = list(
        db.scalars(
            select(SeriesObservation)
            .where(SeriesObservation.series_id == series_id)
            .order_by(SeriesObservation.obs_date.desc())
            .limit(limit)
        ).all()
    )
    rows.reverse()
    out: dict[date, float] = {}
    for o in rows:
        if o.obs_value is not None:
            try:
                out[o.obs_date] = float(o.obs_value)
            except (TypeError, ValueError):
                continue
    return out


def _correlation_items(
    db: Session,
    *,
    primary_id: int,
    candidate: StoryCandidate | None,
) -> list[dict[str, Any]]:
    if candidate is None:
        return []
    rels = list(
        db.scalars(
            select(CandidateRelatedSeries)
            .where(CandidateRelatedSeries.candidate_id == candidate.id)
            .where(CandidateRelatedSeries.series_id != primary_id)
            .order_by(CandidateRelatedSeries.id.asc())
            .limit(5)
        ).all()
    )
    if not rels:
        return []
    primary_map = _obs_map(db, primary_id, limit=120)
    if len(primary_map) < 6:
        return []
    items: list[dict[str, Any]] = []
    for rel in rels:
        other = db.get(Series, rel.series_id)
        if other is None:
            continue
        other_map = _obs_map(db, rel.series_id, limit=120)
        common = sorted(set(primary_map) & set(other_map))
        if len(common) < 6:
            items.append(
                {
                    "series_title": other.name,
                    "comparison_text": (
                        "Hay datos para esta serie relacionada, pero no bastan fechas comunes "
                        "con la principal para estimar una correlación automática con fiabilidad."
                    ),
                    "coefficient": None,
                }
            )
            continue
        xs = [primary_map[d] for d in common]
        ys = [other_map[d] for d in common]
        r = _pearson(xs, ys)
        if r is None:
            desc = (
                "No se obtuvo un coeficiente estable (posiblemente por poca variación en uno de los niveles). "
                "La comparación cualitativa sigue siendo útil en redacción."
            )
        else:
            direction = "positiva" if r > 0.08 else "negativa" if r < -0.08 else "casi nula"
            desc = (
                f"Con {len(common)} fechas alineadas, la correlación de Pearson es aproximadamente {r:+.2f} "
                f"({direction}, asociación {_corr_strength_es(r)}). "
                "La correlación no implica causalidad: puede haber variables omitidas o desfases entre series."
            )
        items.append({"series_title": other.name, "comparison_text": desc, "coefficient": r})
    return items[:4]


def compute_default_narrative_bundle(
    db: Session,
    *,
    candidate: StoryCandidate | None,
    primary_chart_spec: dict[str, Any],
    public_title: str,
    topic: str | None,
    tags: list[str] | None,
) -> dict[str, Any]:
    points, series_label = _preview_pairs_from_spec(primary_chart_spec)
    label = series_label or "el indicador publicado"
    topic_l = (topic or "").lower()
    tags_l = [t.lower() for t in (tags or []) if t]

    insight = (candidate.insight or "").strip() if candidate else ""
    exec_s = (candidate.executive_summary or "").strip() if candidate else ""
    why = (candidate.why_it_matters or "").strip() if candidate else ""

    if len(points) >= 1:
        d0, v0 = points[0]
        d1, v1 = points[-1]
        trend = "sube" if v1 > v0 + 1e-9 else "baja" if v1 < v0 - 1e-9 else "se mantiene estable"
        caption = (
            f"El gráfico muestra la evolución de {label} en el periodo disponible. "
            f"Entre {d0} y {d1} el nivel {trend}, pasando de aproximadamente {v0:,.2f} a {v1:,.2f} "
            f"(cifras según la fuente). Sirve para situar de un vistazo el ritmo del fenómeno sin leer tablas crudas."
        )
    else:
        caption = (
            f"La historia se centra en «{public_title}». "
            "Cuando la serie numérica esté disponible en la ficha, aquí aparecerá una lectura sencilla del gráfico."
        )

    if exec_s:
        caption = f"{caption} {exec_s}"

    econ_bits = []
    if topic_l in {"economy", "macro", "empleo", "labor"} or any(
        x in tags_l for x in ("macro", "ipc", "pib", "empleo", "economía", "economy")
    ):
        econ_bits.append(
            "En clave económica, este tipo de serie suele leerse junto a crecimiento, inflación, mercado laboral "
            "y expectativas de renta disponible."
        )
    else:
        econ_bits.append(
            "En clave económica, los cambios de nivel suelen conectar con decisiones de política presupuestaria, "
            "costes de servicios y planificación sectorial, aunque el vínculo dependa del indicador concreto."
        )
    if exec_s:
        econ_bits.append(exec_s)
    if why:
        econ_bits.append(f"Contexto editorial: {why}")
    analysis_economic = " ".join(econ_bits)

    social_bits = [
        "En clave social, conviene preguntar quién gana y quién pierde con el desplazamiento del indicador: "
        "territorios, cohortes de edad y hogares con distinta composición.",
    ]
    if insight:
        social_bits.append(insight)
    if why:
        social_bits.append(f"Por qué importa a la ciudadanía: {why}")
    if topic_l in {"housing", "vivienda", "demografia", "demografía", "poblacion", "población"} or any(
        x in tags_l for x in ("vivienda", "población", "demografía", "sanidad", "educación")
    ):
        social_bits.append(
            "Las lecturas habituales vinculan estas dinámicas con acceso a vivienda, dependencia, "
            "servicios públicos locales y desigualdad territorial."
        )
    analysis_social = " ".join(social_bits)

    primary_id = _primary_series_id(primary_chart_spec, candidate, db)
    correlations: list[dict[str, Any]] = []
    if primary_id is not None:
        correlations = _correlation_items(db, primary_id=primary_id, candidate=candidate)
    if not correlations:
        correlations = [
            {
                "series_title": "Otras fuentes del proyecto",
                "comparison_text": (
                    "Aún no hay series vinculadas adicionales para esta historia; cuando el equipo editorial "
                    "asocie indicadores complementarios, aquí aparecerán lecturas comparativas y correlaciones "
                    "sobre fechas comunes."
                ),
                "coefficient": None,
            }
        ]

    return {
        "chart_public_caption": caption.strip(),
        "analysis_economic": analysis_economic.strip(),
        "analysis_social": analysis_social.strip(),
        "correlations": correlations,
    }


def merge_narrative_bundle(
    stored: dict[str, Any] | None,
    computed: dict[str, Any],
) -> dict[str, Any]:
    """Las claves presentes en `stored` sustituyen a las generadas (permite revisión editorial)."""
    s = dict(stored or {})
    out = dict(computed)
    for key in ("chart_public_caption", "analysis_economic", "analysis_social"):
        if key in s and isinstance(s[key], str) and s[key].strip():
            out[key] = s[key].strip()
    if "correlations" in s and isinstance(s["correlations"], list) and len(s["correlations"]) > 0:
        normalized: list[dict[str, Any]] = []
        for row in s["correlations"]:
            if not isinstance(row, dict):
                continue
            title = str(row.get("series_title") or row.get("title") or "").strip()
            text = str(row.get("comparison_text") or row.get("narrative") or "").strip()
            if not title or not text:
                continue
            coef = row.get("coefficient")
            cf: float | None
            try:
                cf = float(coef) if coef is not None else None
            except (TypeError, ValueError):
                cf = None
            normalized.append({"series_title": title, "comparison_text": text, "coefficient": cf})
        if normalized:
            out["correlations"] = normalized
    return out
