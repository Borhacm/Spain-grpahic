from __future__ import annotations

import csv
from copy import deepcopy
from datetime import date, datetime, timezone
from io import StringIO
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Series, SeriesObservation, Source


def _seed_payload() -> dict[str, Any]:
    return {
        "executive_kpis": [
            {
                "id": "gdp",
                "label": "PIB real",
                "value": "+2,4% interanual",
                "delta": "+0,3 pp trimestral",
                "trend": [1.6, 1.9, 2.0, 2.2, 2.4],
                "updated_at": "Q4 2025",
                "source": "BdE",
                "status": "Revisado",
            },
            {
                "id": "inflation",
                "label": "Inflación (IPC)",
                "value": "2,8%",
                "delta": "-0,4 pp interanual",
                "trend": [3.6, 3.4, 3.2, 3.0, 2.8],
                "updated_at": "Mar 2026",
                "source": "INE",
                "status": "Último disponible",
            },
            {
                "id": "unemployment",
                "label": "Tasa de paro",
                "value": "11,5%",
                "delta": "-0,7 pp interanual",
                "trend": [12.5, 12.2, 12.0, 11.8, 11.5],
                "updated_at": "Q1 2026",
                "source": "INE",
                "status": "Último disponible",
            },
            {
                "id": "population",
                "label": "Población total",
                "value": "49,2 M",
                "delta": "+1,1% interanual",
                "trend": [48.1, 48.4, 48.6, 48.9, 49.2],
                "updated_at": "2025",
                "source": "INE",
                "status": "Revisado",
            },
            {
                "id": "debt",
                "label": "Deuda pública",
                "value": "104,3% PIB",
                "delta": "-1,2 pp interanual",
                "trend": [111.6, 109.8, 108.2, 106.1, 104.3],
                "updated_at": "Q4 2025",
                "source": "BdE",
                "status": "Provisional",
            },
            {
                "id": "public-balance",
                "label": "Saldo público",
                "value": "-3,1% PIB",
                "delta": "+0,4 pp interanual",
                "trend": [-8.4, -6.9, -4.7, -3.5, -3.1],
                "updated_at": "2025",
                "source": "Eurostat",
                "status": "Último disponible",
            },
            {
                "id": "housing",
                "label": "Compraventas vivienda",
                "value": "636 mil",
                "delta": "+4,2% interanual",
                "trend": [564, 585, 602, 614, 636],
                "updated_at": "2025",
                "source": "INE",
                "status": "Revisado",
            },
            {
                "id": "companies",
                "label": "Empresas activas",
                "value": "3,45 M",
                "delta": "+0,9% interanual",
                "trend": [3.31, 3.34, 3.38, 3.42, 3.45],
                "updated_at": "2025",
                "source": "INE",
                "status": "Último disponible",
            },
            {
                "id": "wages",
                "label": "Coste laboral medio",
                "value": "3.062 EUR/mes",
                "delta": "+3,7% interanual",
                "trend": [2790, 2860, 2935, 3008, 3062],
                "updated_at": "Q4 2025",
                "source": "INE",
                "status": "Provisional",
            },
        ],
        "executive_narrative": [
            "La economía mantiene crecimiento moderado y una inflación más contenida que en 2023.",
            "El desempleo sigue bajando, aunque permanece en niveles altos frente a otras economías europeas.",
            "La presión demográfica por mayor población y hogares sostiene la demanda de vivienda.",
        ],
        "sections": [
            {
                "id": "resumen",
                "title": "Resumen país",
                "description": "Panorama macro de crecimiento, precios, empleo y posición fiscal.",
                "indicators": [
                    {
                        "id": "resumen-balance",
                        "label": "Saldo público (% PIB)",
                        "value": "-3,1%",
                        "change": "+0,4 pp interanual",
                        "period": "2025",
                        "source": "Eurostat",
                        "status": "Último disponible",
                        "note": "El déficit se reduce gradualmente, aunque sigue en terreno negativo.",
                        "series": [
                            {"period": "2021", "value": -8.4},
                            {"period": "2022", "value": -6.9},
                            {"period": "2023", "value": -4.7},
                            {"period": "2024", "value": -3.5},
                            {"period": "2025", "value": -3.1},
                        ],
                    },
                    {
                        "id": "resumen-gdp",
                        "label": "PIB real",
                        "value": "+2,4%",
                        "change": "+0,3 pp trimestral",
                        "period": "Q4 2025",
                        "source": "BdE",
                        "status": "Revisado",
                        "note": "Avance por encima de la media prevista para la eurozona.",
                        "series": [
                            {"period": "2021", "value": 5.5},
                            {"period": "2022", "value": 5.8},
                            {"period": "2023", "value": 2.7},
                            {"period": "2024", "value": 2.2},
                            {"period": "2025", "value": 2.4},
                        ],
                    }
                ],
            },
            {
                "id": "laboral",
                "title": "Mercado laboral",
                "description": "Evolución del empleo, desempleo, costes laborales y vacantes.",
                "indicators": [
                    {
                        "id": "laboral-employment",
                        "label": "Ocupación",
                        "value": "21,9 M",
                        "change": "+2,0% interanual",
                        "period": "Q1 2026",
                        "source": "INE",
                        "status": "Último disponible",
                        "note": "Máximos de ocupación, con servicios liderando la creación neta.",
                        "series": [
                            {"period": "2021", "value": 20.2},
                            {"period": "2022", "value": 20.5},
                            {"period": "2023", "value": 20.9},
                            {"period": "2024", "value": 21.4},
                            {"period": "2025", "value": 21.9},
                        ],
                    },
                    {
                        "id": "laboral-activity-rate",
                        "label": "Tasa de actividad",
                        "value": "58,9%",
                        "change": "+0,3 pp interanual",
                        "period": "Q3 2023",
                        "source": "INE",
                        "status": "Último disponible",
                        "note": "Mide la participación de la población activa y ayuda a interpretar el paro.",
                        "series": [
                            {"period": "2021", "value": 58.1},
                            {"period": "2022", "value": 58.4},
                            {"period": "2023", "value": 58.9},
                        ],
                    },
                    {
                        "id": "laboral-unemployment-harmonized",
                        "label": "Paro armonizado (FMI)",
                        "value": "10,8%",
                        "change": "-0,4 pp interanual",
                        "period": "2026",
                        "source": "FMI",
                        "status": "Último disponible",
                        "note": "Referencia internacional armonizada para comparar España con otras economías.",
                        "series": [
                            {"period": "2022", "value": 12.9},
                            {"period": "2023", "value": 12.2},
                            {"period": "2024", "value": 11.6},
                            {"period": "2025", "value": 11.2},
                            {"period": "2026", "value": 10.8},
                        ],
                    },
                ],
            },
            {
                "id": "digitalizacion-empleo",
                "title": "Digitalización y empleo digital",
                "description": "Adopción digital empresarial y disponibilidad de talento TIC en el mercado laboral.",
                "indicators": [
                    {
                        "id": "digital-ict-specialists",
                        "label": "Especialistas TIC sobre empleo total",
                        "value": "4,8%",
                        "change": "+0,2 pp interanual",
                        "period": "2025",
                        "source": "Eurostat",
                        "status": "Último disponible",
                        "note": "El peso del empleo tecnológico crece, aunque persiste brecha de talento en perfiles avanzados.",
                        "series": [
                            {"period": "2021", "value": 4.1},
                            {"period": "2022", "value": 4.2},
                            {"period": "2023", "value": 4.4},
                            {"period": "2024", "value": 4.6},
                            {"period": "2025", "value": 4.8},
                        ],
                    },
                    {
                        "id": "digital-firms-basic-intensity",
                        "label": "Empresas con intensidad digital básica",
                        "value": "68%",
                        "change": "+3,0 pp interanual",
                        "period": "2025",
                        "source": "Eurostat",
                        "status": "Último disponible",
                        "note": "Aumenta la base digital en pymes, impulsada por cloud y herramientas de colaboración.",
                        "series": [
                            {"period": "2021", "value": 57.0},
                            {"period": "2022", "value": 60.0},
                            {"period": "2023", "value": 63.0},
                            {"period": "2024", "value": 65.0},
                            {"period": "2025", "value": 68.0},
                        ],
                    },
                    {
                        "id": "digital-oecd-dgi",
                        "label": "OECD Digital Government Index",
                        "value": "7,4/10",
                        "change": "+0,3 puntos",
                        "period": "2025",
                        "source": "OECD",
                        "status": "Último disponible",
                        "note": "Índice comparativo internacional en escala 0-10 (mayor es mejor).",
                        "series": [
                            {"period": "2021", "value": 6.5},
                            {"period": "2022", "value": 6.7},
                            {"period": "2023", "value": 6.9},
                            {"period": "2024", "value": 7.1},
                            {"period": "2025", "value": 7.4},
                        ],
                    },
                    {
                        "id": "digital-oecd-ourdata",
                        "label": "OECD OURdata Index",
                        "value": "8,2/10",
                        "change": "+0,4 puntos",
                        "period": "2025",
                        "source": "OECD",
                        "status": "Último disponible",
                        "note": "Índice comparativo internacional en escala 0-10 (mayor es mejor).",
                        "series": [
                            {"period": "2021", "value": 7.0},
                            {"period": "2022", "value": 7.3},
                            {"period": "2023", "value": 7.6},
                            {"period": "2024", "value": 7.8},
                            {"period": "2025", "value": 8.2},
                        ],
                    },
                ],
            },
            {
                "id": "proyecciones-fmi",
                "title": "Proyecciones FMI",
                "description": "Escenario macro de crecimiento, precios y paro para España.",
                "indicators": [
                    {
                        "id": "fmi-gdp-growth",
                        "label": "FMI PIB real (variación anual)",
                        "value": "2,5%",
                        "change": "-0,3 pp interanual",
                        "period": "2026",
                        "source": "FMI",
                        "status": "Último disponible",
                        "note": "Serie del DataMapper del FMI para comparativa internacional homogénea.",
                        "series": [
                            {"period": "2022", "value": 5.8},
                            {"period": "2023", "value": 2.7},
                            {"period": "2024", "value": 2.5},
                            {"period": "2025", "value": 2.3},
                            {"period": "2026", "value": 2.0},
                        ],
                    },
                    {
                        "id": "fmi-inflation",
                        "label": "FMI inflación media",
                        "value": "2,9%",
                        "change": "-0,5 pp interanual",
                        "period": "2026",
                        "source": "FMI",
                        "status": "Último disponible",
                        "note": "Inflación media anual según metodología comparada del FMI.",
                        "series": [
                            {"period": "2022", "value": 8.3},
                            {"period": "2023", "value": 3.5},
                            {"period": "2024", "value": 3.0},
                            {"period": "2025", "value": 2.9},
                            {"period": "2026", "value": 2.6},
                        ],
                    },
                    {
                        "id": "fmi-unemployment",
                        "label": "FMI tasa de paro",
                        "value": "10,8%",
                        "change": "-0,4 pp interanual",
                        "period": "2026",
                        "source": "FMI",
                        "status": "Último disponible",
                        "note": "Tasa de desempleo armonizada para comparabilidad entre economías.",
                        "series": [
                            {"period": "2022", "value": 12.9},
                            {"period": "2023", "value": 12.2},
                            {"period": "2024", "value": 11.6},
                            {"period": "2025", "value": 11.2},
                            {"period": "2026", "value": 10.8},
                        ],
                    },
                ],
            },
            {
                "id": "demografia-vivienda",
                "title": "Demografía y vivienda",
                "description": "Cambio demográfico, hogares y presión sobre el mercado residencial.",
                "indicators": [
                    {
                        "id": "demo-population",
                        "label": "Población total",
                        "value": "49,2 M",
                        "change": "+1,1% interanual",
                        "period": "2025",
                        "source": "INE",
                        "status": "Revisado",
                        "note": "El crecimiento se apoya en migración neta positiva.",
                        "series": [
                            {"period": "2021", "value": 47.4},
                            {"period": "2022", "value": 47.8},
                            {"period": "2023", "value": 48.3},
                            {"period": "2024", "value": 48.9},
                            {"period": "2025", "value": 49.2},
                        ],
                    }
                ],
            },
            {
                "id": "empresa-actividad",
                "title": "Empresa y actividad",
                "description": "Tejido empresarial, negocio y avance de digitalización productiva.",
                "indicators": [
                    {
                        "id": "empresa-total",
                        "label": "Empresas activas",
                        "value": "3,45 M",
                        "change": "+0,9% interanual",
                        "period": "2025",
                        "source": "INE",
                        "status": "Último disponible",
                        "note": "Las microempresas siguen siendo el grueso del tejido empresarial.",
                        "series": [
                            {"period": "2021", "value": 3.27},
                            {"period": "2022", "value": 3.31},
                            {"period": "2023", "value": 3.34},
                            {"period": "2024", "value": 3.42},
                            {"period": "2025", "value": 3.45},
                        ],
                    },
                    {
                        "id": "empresa-digital",
                        "label": "Empresas con venta online",
                        "value": "31%",
                        "change": "+2,1 pp interanual",
                        "period": "2025",
                        "source": "INE",
                        "status": "Provisional",
                        "note": "Se acelera la adopción digital en pymes orientadas a consumo.",
                        "series": [
                            {"period": "2021", "value": 23.5},
                            {"period": "2022", "value": 25.1},
                            {"period": "2023", "value": 27.4},
                            {"period": "2024", "value": 28.9},
                            {"period": "2025", "value": 31},
                        ],
                    },
                    {
                        "id": "empresa-net-creation",
                        "label": "Creación neta de empresas",
                        "value": "58 mil",
                        "change": "+9,4% interanual",
                        "period": "2025",
                        "source": "INE",
                        "status": "Último disponible",
                        "note": "La diferencia entre altas y bajas acelera la expansión del tejido empresarial.",
                        "series": [
                            {"period": "2021", "value": 35},
                            {"period": "2022", "value": 41},
                            {"period": "2023", "value": 46},
                            {"period": "2024", "value": 53},
                            {"period": "2025", "value": 58},
                        ],
                    },
                    {
                        "id": "empresa-productivity",
                        "label": "Productividad por ocupado",
                        "value": "74,3 mil EUR",
                        "change": "+1,8% interanual",
                        "period": "2025",
                        "source": "Eurostat",
                        "status": "Provisional",
                        "note": "Mejora la eficiencia media, aunque con avances heterogéneos por sector.",
                        "series": [
                            {"period": "2021", "value": 69.8},
                            {"period": "2022", "value": 71.1},
                            {"period": "2023", "value": 72.2},
                            {"period": "2024", "value": 73.0},
                            {"period": "2025", "value": 74.3},
                        ],
                    },
                ],
            },
        ],
    }


def _merge_kpis(base: list[dict[str, Any]], updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {item.get("id"): item for item in updates if isinstance(item, dict)}
    merged: list[dict[str, Any]] = []
    for kpi in base:
        patch = by_id.get(kpi.get("id"))
        if not patch:
            merged.append(kpi)
            continue
        merged_item = dict(kpi)
        merged_item.update(patch)
        merged.append(merged_item)
    return merged


def _merge_sections(base: list[dict[str, Any]], updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    section_updates = {item.get("id"): item for item in updates if isinstance(item, dict)}
    merged_sections: list[dict[str, Any]] = []
    for section in base:
        patch = section_updates.get(section.get("id"))
        if not patch:
            merged_sections.append(section)
            continue
        merged = dict(section)
        for key in ("title", "description"):
            if key in patch:
                merged[key] = patch[key]
        if isinstance(patch.get("indicators"), list):
            indicator_updates = {
                item.get("id"): item for item in patch["indicators"] if isinstance(item, dict)
            }
            merged_indicators: list[dict[str, Any]] = []
            for indicator in section.get("indicators", []):
                indicator_patch = indicator_updates.get(indicator.get("id"))
                if not indicator_patch:
                    merged_indicators.append(indicator)
                    continue
                merged_indicator = dict(indicator)
                merged_indicator.update(indicator_patch)
                merged_indicators.append(merged_indicator)
            merged["indicators"] = merged_indicators
        merged_sections.append(merged)
    return merged_sections


def _merge_payload(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    if isinstance(update.get("executive_kpis"), list):
        merged["executive_kpis"] = _merge_kpis(merged["executive_kpis"], update["executive_kpis"])
    if isinstance(update.get("executive_narrative"), list) and update["executive_narrative"]:
        merged["executive_narrative"] = update["executive_narrative"]
    if isinstance(update.get("sections"), list):
        merged["sections"] = _merge_sections(merged["sections"], update["sections"])
    return merged


def _fetch_patch(url: str, timeout_seconds: float) -> dict[str, Any] | None:
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.get(url)
            response.raise_for_status()
            payload = response.json()
        if isinstance(payload, dict):
            return payload
        return None
    except Exception:
        return None


def _parse_series_map(raw: str | None) -> dict[str, tuple[str, str]]:
    """
    Formato esperado:
    "gdp=bde:PIB_CODE,inflation=ine:IPC_CODE,resumen-gdp=bde:PIB_CODE"
    """
    if not raw:
        return {}
    result: dict[str, tuple[str, str]] = {}
    for chunk in raw.split(","):
        item = chunk.strip()
        if not item or "=" not in item:
            continue
        indicator_id, target = item.split("=", 1)
        indicator_id = indicator_id.strip()
        target = target.strip()
        if ":" not in target:
            continue
        source_slug, external_code = target.split(":", 1)
        if indicator_id and source_slug and external_code:
            result[indicator_id] = (source_slug.strip().lower(), external_code.strip())
    return result


def _format_number(value: float, decimals: int = 2) -> str:
    safe_decimals = max(decimals, 0)
    return f"{value:,.{safe_decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _extract_decimal_places(template: Any, default: int = 2) -> int:
    if not isinstance(template, str):
        return default
    number_part: list[str] = []
    for char in template:
        if char.isdigit() or char in {",", ".", "-", "+"}:
            number_part.append(char)
        elif number_part:
            break
    token = "".join(number_part)
    if not token:
        return default
    if "," in token:
        return len(token.rsplit(",", 1)[-1])
    if "." in token:
        return len(token.rsplit(".", 1)[-1])
    return 0


def _format_value_like_template(value: float, template: Any, target_id: str, label: Any) -> str:
    decimals = _extract_decimal_places(template, default=2)
    scaled_value = value
    if not isinstance(template, str):
        return _format_number(scaled_value, decimals=decimals)
    normalized = template.lower()
    if " mil" in normalized:
        # If the series already comes in thousands (e.g., 636), keep it as-is.
        scaled_value = value if abs(value) < 10_000 else value / 1_000
    elif " m" in normalized:
        # - Headcount in persons (e.g. 49_600_000) → divide by 1e6.
        # - INE EPA "valor absoluto" is often in miles de personas (e.g. 22_463) → divide by 1e3.
        # - Already in millions on the card (e.g. 3.45, 21.9) → keep as-is.
        av = abs(value)
        if av >= 1_000_000:
            scaled_value = value / 1_000_000
        elif av >= 5_000:
            scaled_value = value / 1_000
        else:
            scaled_value = value
    formatted = _format_number(scaled_value, decimals=decimals)
    if "%" in template:
        return f"{formatted}%"
    if "/10" in normalized:
        return f"{formatted}/10"
    if " mil" in normalized and "eur" in normalized:
        return f"{formatted} mil EUR"
    if "eur" in normalized:
        return f"{formatted} EUR"
    if " mil" in normalized:
        return f"{formatted} mil"
    if " m" in normalized:
        return f"{formatted} M"
    return formatted


def _format_delta_like_template(current: float, previous: float | None, template: Any) -> str:
    if previous is None:
        return "n/d"
    decimals = _extract_decimal_places(template, default=2)
    delta_raw = current - previous
    if not isinstance(template, str):
        delta_value = f"{delta_raw:+.{max(decimals, 0)}f}".replace(".", ",")
        return delta_value
    normalized = template.lower()
    if "pp" in normalized:
        delta_value = f"{delta_raw:+.{max(decimals, 0)}f}".replace(".", ",")
        return f"{delta_value} pp"
    if "%" in template:
        if previous == 0:
            return "n/d"
        relative_change = (delta_raw / abs(previous)) * 100
        delta_value = f"{relative_change:+.{max(decimals, 0)}f}".replace(".", ",")
        return f"{delta_value}%"
    delta_value = f"{delta_raw:+.{max(decimals, 0)}f}".replace(".", ",")
    return delta_value


def _is_oecd_index_on_ten(target_id: str, source_slug: str) -> bool:
    return source_slug.lower() == "oecd" and target_id in {"digital-oecd-dgi", "digital-oecd-ourdata"}


def _format_period(obs_date: date) -> str:
    return obs_date.isoformat()


def _freshness_limit_days(frequency: str | None) -> int:
    normalized = (frequency or "").strip().lower()
    if normalized in {"m", "month", "monthly", "mensual"}:
        return 92
    if normalized in {"q", "quarter", "quarterly", "trimestral"}:
        return 183
    if normalized in {"a", "y", "year", "yearly", "annual", "anual"}:
        return 548
    return 548


def _staleness(latest_obs: date, frequency: str | None, source_slug: str | None = None) -> tuple[bool, int, int]:
    today = datetime.now(tz=timezone.utc).date()
    age_days = max((today - latest_obs).days, 0)
    max_age_days = _freshness_limit_days(frequency)
    source = (source_slug or "").lower()
    if source == "bde":
        max_age_days = max(max_age_days, 275)
    # INE Tempus: some EPA series (e.g. EPA87 total ocupados) stop updating in the public serie id
    # while new periods live under other table/serie ids; avoid false "stale" blocking strict mode.
    if source == "ine":
        max_age_days = max(max_age_days, 1200)
    # OECD composite governance indexes (e.g., DGI/OURdata) are edition-based and
    # often lag several years by design; use a wider freshness window to avoid false stale flags.
    if source == "oecd":
        max_age_days = max(max_age_days, 365 * 5)
    return age_days > max_age_days, age_days, max_age_days


def _load_series_points(db: Session, source_slug: str, external_code: str, limit: int = 600) -> list[SeriesObservation]:
    source_id = db.scalar(select(Source.id).where(Source.slug == source_slug))
    if source_id is None:
        return []
    series_id = db.scalar(
        select(Series.id).where(Series.source_id == source_id, Series.external_code == external_code).limit(1)
    )
    if series_id is None:
        return []
    points = list(
        db.scalars(
            select(SeriesObservation)
            .where(SeriesObservation.series_id == series_id, SeriesObservation.obs_value.is_not(None))
            .order_by(SeriesObservation.obs_date.desc())
            .limit(limit)
        ).all()
    )
    points.reverse()
    return points


def _resolve_series(db: Session, source_slug: str, external_code: str) -> tuple[Series | None, str | None]:
    source_id = db.scalar(select(Source.id).where(Source.slug == source_slug))
    if source_id is None:
        return None, "source_not_found"
    series = db.scalar(
        select(Series).where(Series.source_id == source_id, Series.external_code == external_code).limit(1)
    )
    if series is None:
        return None, "series_not_found"
    return series, None


def _source_label(slug: str) -> str:
    mapping = {
        "bde": "BdE",
        "ine": "INE",
        "eurostat": "Eurostat",
        "oecd": "OECD",
        "fmi": "FMI",
        "imf": "FMI",
    }
    return mapping.get(slug.lower(), slug.upper())


def _apply_mapped_series_data(db: Session, payload: dict[str, Any], series_map: dict[str, tuple[str, str]]) -> dict[str, Any]:
    if not series_map:
        return payload
    merged = deepcopy(payload)
    today = datetime.now(tz=timezone.utc).date()

    kpi_by_id = {item.get("id"): item for item in merged.get("executive_kpis", []) if isinstance(item, dict)}
    indicator_by_id: dict[str, dict[str, Any]] = {}
    for section in merged.get("sections", []):
        if not isinstance(section, dict):
            continue
        for indicator in section.get("indicators", []):
            if isinstance(indicator, dict) and indicator.get("id"):
                indicator_by_id[indicator["id"]] = indicator

    for target_id, (source_slug, external_code) in series_map.items():
        raw_observations = _load_series_points(db, source_slug=source_slug, external_code=external_code, limit=600)
        observations = [obs for obs in raw_observations if obs.obs_date <= today]
        if len(observations) < 1:
            continue
        values = [float(obs.obs_value) for obs in observations if obs.obs_value is not None]
        if not values:
            continue
        latest = values[-1]
        previous = values[-2] if len(values) > 1 else None
        if _is_oecd_index_on_ten(target_id, source_slug):
            values = [v * 10 for v in values]
            latest = latest * 10
            previous = previous * 10 if previous is not None else None
        kpi_template = kpi_by_id.get(target_id, {}).get("value")
        indicator_template = indicator_by_id.get(target_id, {}).get("value")
        value_template = kpi_template if isinstance(kpi_template, str) else indicator_template
        delta_template = kpi_by_id.get(target_id, {}).get("delta")
        if not isinstance(delta_template, str):
            delta_template = indicator_by_id.get(target_id, {}).get("change")
        label_template = kpi_by_id.get(target_id, {}).get("label")
        if not isinstance(label_template, str):
            label_template = indicator_by_id.get(target_id, {}).get("label")

        display_value = _format_value_like_template(latest, value_template, target_id=target_id, label=label_template)
        delta = _format_delta_like_template(latest, previous, delta_template)
        trend = [round(v, 4) for v in values]
        series = [
            {
                "period": _format_period(obs.obs_date),
                "value": float(obs.obs_value) * 10 if _is_oecd_index_on_ten(target_id, source_slug) else float(obs.obs_value),
            }
            for obs in observations
        ]

        series_obj, _ = _resolve_series(db, source_slug=source_slug, external_code=external_code)
        latest_obs_date = observations[-1].obs_date
        stale, age_days, max_age_days = _staleness(
            latest_obs_date,
            getattr(series_obj, "frequency", None),
            source_slug=source_slug,
        )
        status = "Desactualizado" if stale else "Último disponible"
        freshness_note = (
            f"Dato desactualizado: último {latest_obs_date.isoformat()} "
            f"({age_days} días, máximo esperado {max_age_days} días)."
        )

        if target_id in kpi_by_id:
            item = kpi_by_id[target_id]
            item["value"] = display_value
            item["delta"] = delta
            item["trend"] = trend
            item["updated_at"] = _format_period(latest_obs_date)
            item["source"] = _source_label(source_slug)
            item["status"] = status
        if target_id in indicator_by_id:
            item = indicator_by_id[target_id]
            item["value"] = display_value
            item["change"] = delta
            item["period"] = _format_period(latest_obs_date)
            item["series"] = series
            item["source"] = _source_label(source_slug)
            item["status"] = status
            if stale:
                base_note = item.get("note", "").strip()
                item["note"] = f"{base_note} {freshness_note}".strip()

    return merged


def _kpi_trend_stats(payload: dict[str, Any], kpi_id: str) -> tuple[float, float | None] | None:
    for item in payload.get("executive_kpis", []):
        if not isinstance(item, dict) or item.get("id") != kpi_id:
            continue
        trend = item.get("trend")
        if not isinstance(trend, list) or not trend:
            return None
        values = [float(value) for value in trend if isinstance(value, (int, float))]
        if not values:
            return None
        latest = values[-1]
        previous = values[-2] if len(values) > 1 else None
        return latest, previous
    return None


def _generate_executive_narrative(payload: dict[str, Any]) -> list[str]:
    base = payload.get("executive_narrative")
    fallback = base if isinstance(base, list) and all(isinstance(item, str) for item in base) else []

    gdp = _kpi_trend_stats(payload, "gdp")
    inflation = _kpi_trend_stats(payload, "inflation")
    unemployment = _kpi_trend_stats(payload, "unemployment")
    population = _kpi_trend_stats(payload, "population")
    debt = _kpi_trend_stats(payload, "debt")

    lines: list[str] = []

    if gdp or inflation:
        parts: list[str] = []
        if gdp:
            gdp_latest, gdp_prev = gdp
            gdp_dir = (
                "acelera"
                if gdp_prev is not None and gdp_latest > gdp_prev
                else "se modera"
                if gdp_prev is not None and gdp_latest < gdp_prev
                else "se mantiene"
            )
            parts.append(f"el crecimiento {gdp_dir} ({_format_number(gdp_latest, 1)}%)")
        if inflation:
            inf_latest, inf_prev = inflation
            inf_dir = (
                "baja"
                if inf_prev is not None and inf_latest < inf_prev
                else "sube"
                if inf_prev is not None and inf_latest > inf_prev
                else "se estabiliza"
            )
            parts.append(f"la inflación {inf_dir} ({_format_number(inf_latest, 1)}%)")
        lines.append("En el frente macro, " + " y ".join(parts) + ".")

    if unemployment or population:
        parts = []
        if unemployment:
            un_latest, un_prev = unemployment
            un_dir = (
                "desciende"
                if un_prev is not None and un_latest < un_prev
                else "aumenta"
                if un_prev is not None and un_latest > un_prev
                else "se mantiene"
            )
            parts.append(f"el paro {un_dir} ({_format_number(un_latest, 1)}%)")
        if population:
            pop_latest, pop_prev = population
            pop_dir = (
                "crece"
                if pop_prev is not None and pop_latest > pop_prev
                else "retrocede"
                if pop_prev is not None and pop_latest < pop_prev
                else "se mantiene estable"
            )
            pop_display = (
                f"{_format_number(pop_latest / 1_000_000, 1)} M"
                if abs(pop_latest) >= 1_000_000
                else _format_number(pop_latest, 1)
            )
            parts.append(f"la población {pop_dir} ({pop_display})")
        lines.append("En términos de empleo y demanda interna, " + " y ".join(parts) + ".")

    if debt:
        debt_latest, debt_prev = debt
        debt_dir = (
            "reduce"
            if debt_prev is not None and debt_latest < debt_prev
            else "aumenta"
            if debt_prev is not None and debt_latest > debt_prev
            else "se mantiene"
        )
        lines.append(
            f"En posición fiscal, la deuda pública {debt_dir} su ratio sobre PIB "
            f"hasta {_format_number(debt_latest, 1)}%."
        )

    if len(lines) >= 3:
        return lines[:3]
    if lines:
        return lines
    return fallback


def get_public_country_overview(db: Session) -> dict[str, Any]:
    settings = get_settings()
    payload = _seed_payload()
    series_map = _parse_series_map(settings.country_overview_series_map)
    payload = _apply_mapped_series_data(db, payload, series_map)

    for env_key in (
        "country_overview_bde_url",
        "country_overview_ine_url",
        "country_overview_eurostat_url",
        "country_overview_oecd_url",
        "country_overview_fmi_url",
    ):
        url = getattr(settings, env_key, None)
        if not url:
            continue
        patch = _fetch_patch(str(url), timeout_seconds=settings.request_timeout_seconds)
        if patch:
            payload = _merge_payload(payload, patch)

    payload["executive_narrative"] = _generate_executive_narrative(payload)
    return payload


def get_country_overview_mapping_status(db: Session) -> dict[str, Any]:
    settings = get_settings()
    series_map = _parse_series_map(settings.country_overview_series_map)
    items: list[dict[str, Any]] = []

    for indicator_id, (source_slug, external_code) in series_map.items():
        series, error_reason = _resolve_series(db, source_slug=source_slug, external_code=external_code)
        if series is None:
            items.append(
                {
                    "indicator_id": indicator_id,
                    "source_slug": source_slug,
                    "external_code": external_code,
                    "mapped": False,
                    "latest_date": None,
                    "points_loaded": 0,
                    "reason": error_reason,
                }
            )
            continue

        points = list(
            db.scalars(
                select(SeriesObservation)
                .where(SeriesObservation.series_id == series.id, SeriesObservation.obs_value.is_not(None))
                .order_by(SeriesObservation.obs_date.desc())
                .limit(12)
            ).all()
        )
        latest_date = points[0].obs_date.isoformat() if points else None
        is_stale = False
        age_days = 0
        max_age_days = _freshness_limit_days(series.frequency)
        if points:
            is_stale, age_days, max_age_days = _staleness(
                points[0].obs_date,
                series.frequency,
                source_slug=source_slug,
            )
        items.append(
            {
                "indicator_id": indicator_id,
                "source_slug": source_slug,
                "external_code": external_code,
                "mapped": len(points) > 0,
                "latest_date": latest_date,
                "points_loaded": len(points),
                "is_stale": is_stale,
                "age_days": age_days,
                "max_age_days": max_age_days,
                "reason": "stale_data" if points and is_stale else (None if points else "no_observations"),
            }
        )

    resolved = sum(1 for item in items if item["mapped"])
    return {
        "configured_mappings": len(series_map),
        "resolved_mappings": resolved,
        "items": items,
    }


def get_oecd_ranking_for_indicator(indicator_id: str, country_code: str = "ESP") -> dict[str, Any] | None:
    indicator_to_measure = {
        "digital-oecd-dgi": "DG",
        "digital-oecd-ourdata": "OUR",
    }
    measure = indicator_to_measure.get((indicator_id or "").strip().lower())
    if not measure:
        return None

    path = f"OECD.GOV.GIP,DSD_GOV@DF_GOV_DGOGD_2025,1.0/A..{measure}.IX._Z.2025.DGOGD"
    url = f"https://sdmx.oecd.org/public/rest/data/{path}"
    country = (country_code or "ESP").strip().upper()

    try:
        with httpx.Client(timeout=get_settings().request_timeout_seconds) as client:
            response = client.get(
                url,
                params={"format": "csvfilewithlabels"},
                headers={"User-Agent": "spain-graphic/1.0"},
            )
            response.raise_for_status()
        rows = list(csv.DictReader(StringIO(response.text)))
    except Exception:
        return None

    values_by_country: dict[str, float] = {}
    for row in rows:
        ref_area = (row.get("REF_AREA") or "").strip().upper()
        if not ref_area:
            continue
        value_raw = row.get("OBS_VALUE")
        if value_raw in (None, ""):
            continue
        try:
            values_by_country[ref_area] = float(value_raw) * 10
        except (TypeError, ValueError):
            continue

    if not values_by_country or country not in values_by_country:
        return None

    sorted_scores = sorted(values_by_country.items(), key=lambda item: item[1], reverse=True)
    rank = next((idx + 1 for idx, (code, _) in enumerate(sorted_scores) if code == country), None)
    year = None
    for row in rows:
        if (row.get("REF_AREA") or "").strip().upper() == country:
            year = row.get("TIME_PERIOD")
            if year:
                break

    if rank is None:
        return None

    return {
        "indicator_id": indicator_id,
        "country_code": country,
        "value": round(values_by_country[country], 2),
        "scale": "0-10",
        "rank": rank,
        "total_countries": len(values_by_country),
        "year": year,
    }
