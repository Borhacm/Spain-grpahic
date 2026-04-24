from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.editorial.models import SignalRule
from app.models import CompanySnapshot, Filing, Geography, Series, SeriesObservation


@dataclass(slots=True)
class DetectedSignal:
    signal_type: str
    series_id: int | None
    company_id: int | None
    signal_key: str
    explanation: str
    strength: Decimal
    geography: str | None
    period_label: str
    title: str
    insight: str
    executive_summary: str
    why_it_matters: str
    dedupe_hash: str
    rule_id: int | None = None


def _hash_signal(signal_type: str, entity_id: int, geography: str | None, period_label: str) -> str:
    raw = f"{signal_type}|{entity_id}|{geography or 'NA'}|{period_label}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _pct(new: Decimal | None, old: Decimal | None) -> Decimal | None:
    if new is None or old is None or old == 0:
        return None
    return (new - old) / old * Decimal(100)


def _build_rule_map(db: Session) -> dict[str, dict[str, object]]:
    rows = list(
        db.scalars(select(SignalRule).where(SignalRule.enabled.is_(True)).order_by(SignalRule.id.asc())).all()
    )
    mapping: dict[str, dict[str, object]] = {}
    aliases = {"historical_extreme": ["historical_max", "historical_min"]}
    for row in rows:
        payload = dict(row.params_json or {})
        payload["weight"] = row.weight
        payload["_rule_id"] = row.id
        target_types = aliases.get(row.signal_type, [row.signal_type])
        for signal_type in target_types:
            current = dict(mapping.get(signal_type, {}))
            current.update(payload)
            mapping[signal_type] = current
    return mapping


def _rule_id(rule_map: dict[str, dict[str, object]], signal_type: str) -> int | None:
    value = rule_map.get(signal_type, {}).get("_rule_id")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_rule_map_with_overrides(
    db: Session,
    signal_type: str,
    override_params: dict[str, object] | None = None,
) -> dict[str, dict[str, object]]:
    rule_map = _build_rule_map(db)
    if override_params:
        current = dict(rule_map.get(signal_type, {}))
        current.update(override_params)
        rule_map[signal_type] = current
    return rule_map


def _rule_threshold(
    rule_map: dict[str, dict[str, object]], signal_type: str, key: str, default: Decimal
) -> Decimal:
    value = rule_map.get(signal_type, {}).get(key)
    if value is None:
        return default
    try:
        return Decimal(str(value))
    except Exception:
        return default


def _compact_series_label(raw_name: str, *, max_len: int = 72) -> str:
    """Acorta nombres técnicos largos (p. ej. INE) para titulares legibles."""
    full = " ".join(str(raw_name or "").split())
    name = full
    for prefix in (
        "Total Nacional. Total. Ambos sexos. ",
        "Total nacional. Total. Ambos sexos. ",
    ):
        if name.startswith(prefix):
            name = name[len(prefix) :].lstrip(". ")
            break
    for noise in ("Población. Número.", "Poblacion. Numero."):
        if name.startswith(noise):
            suffix = name[len(noise) :].lstrip(" .")
            name = "Población total" + (f" — {suffix}" if suffix else "")
            break
    if len(name) > max_len:
        name = name[: max_len - 1].rstrip(" ,.;") + "…"
    if not name.strip():
        if len(full) > max_len:
            return full[: max_len - 1].rstrip(" ,.;") + "…"
        return full or "Indicador estadístico"
    return name


def detect_signals_for_series(
    db: Session, series: Series, rule_map: dict[str, dict[str, object]] | None = None
) -> list[DetectedSignal]:
    rule_map = rule_map or {}
    # Pull latest observations first, then restore chronological order.
    obs = list(
        db.scalars(
            select(SeriesObservation)
            .where(SeriesObservation.series_id == series.id)
            .order_by(SeriesObservation.obs_date.desc())
            .limit(60)
        ).all()
    )[::-1]
    if len(obs) < 3:
        return []
    latest = obs[-1]
    prev = obs[-2]
    first = obs[0]
    out: list[DetectedSignal] = []
    series_short = _compact_series_label(series.name)

    geography = None
    if series.geography_id:
        geo = db.get(Geography, series.geography_id)
        geography = geo.code if geo else None

    mom = _pct(latest.obs_value, prev.obs_value)
    strong_threshold = _rule_threshold(rule_map, "strong_period_change", "mom_threshold_pct", Decimal("5"))
    if mom is not None and abs(mom) >= strong_threshold:
        period = latest.obs_date.isoformat()
        out.append(
            DetectedSignal(
                signal_type="strong_period_change",
                series_id=series.id,
                company_id=None,
                signal_key=f"{series.external_code}:{period}:mom",
                explanation=f"Variación fuerte de {mom:+.2f}% frente al periodo anterior.",
                strength=abs(mom),
                geography=geography,
                period_label=period,
                title=f"{series_short}: giro del {mom:+.2f}% en el último dato",
                insight=f"El último registro muestra un cambio del {mom:+.2f}% respecto al periodo inmediatamente anterior.",
                executive_summary=(
                    f"Último valor {latest.obs_value} ({latest.obs_date}). "
                    f"Cambio respecto al periodo anterior: {mom:+.2f}%."
                ),
                why_it_matters="Puede indicar un cambio de ciclo a corto plazo.",
                dedupe_hash=_hash_signal("strong_period_change", series.id, geography, period),
                rule_id=_rule_id(rule_map, "strong_period_change"),
            )
        )

    if latest.obs_value is not None:
        values = [o.obs_value for o in obs if o.obs_value is not None]
        if values:
            if latest.obs_value == max(values):
                period = latest.obs_date.isoformat()
                out.append(
                    DetectedSignal(
                        signal_type="historical_max",
                        series_id=series.id,
                        company_id=None,
                        signal_key=f"{series.external_code}:{period}:max",
                        explanation="Nuevo máximo histórico en la ventana observada.",
                        strength=Decimal("8"),
                        geography=geography,
                        period_label=period,
                        title=f"{series_short}: máximo histórico reciente",
                        insight=(
                            f"El último valor ({latest.obs_value}) es el más alto "
                            f"entre los últimos {len(obs)} registros disponibles de esta serie."
                        ),
                        executive_summary=f"Máximo en {latest.obs_date} con valor {latest.obs_value}.",
                        why_it_matters="Señal de tension o impulso relevante para cobertura editorial.",
                        dedupe_hash=_hash_signal("historical_max", series.id, geography, period),
                        rule_id=_rule_id(rule_map, "historical_max"),
                    )
                )
            if latest.obs_value == min(values):
                period = latest.obs_date.isoformat()
                out.append(
                    DetectedSignal(
                        signal_type="historical_min",
                        series_id=series.id,
                        company_id=None,
                        signal_key=f"{series.external_code}:{period}:min",
                        explanation="Nuevo mínimo histórico en la ventana observada.",
                        strength=Decimal("8"),
                        geography=geography,
                        period_label=period,
                        title=f"{series_short}: mínimo histórico reciente",
                        insight=(
                            f"El último valor ({latest.obs_value}) es el más bajo "
                            f"entre los últimos {len(obs)} registros disponibles de esta serie."
                        ),
                        executive_summary=f"Mínimo en {latest.obs_date} con valor {latest.obs_value}.",
                        why_it_matters="Puede revelar deterioro o corrección estructural.",
                        dedupe_hash=_hash_signal("historical_min", series.id, geography, period),
                        rule_id=_rule_id(rule_map, "historical_min"),
                    )
                )

    yoy = None
    year_ago = date(latest.obs_date.year - 1, latest.obs_date.month, 1)
    prev_year = next((o for o in obs if o.obs_date >= year_ago), None)
    if prev_year:
        yoy = _pct(latest.obs_value, prev_year.obs_value)
    yoy_threshold = _rule_threshold(rule_map, "yoy_change", "yoy_threshold_pct", Decimal("10"))
    if yoy is not None and abs(yoy) >= yoy_threshold:
        period = latest.obs_date.isoformat()
        out.append(
            DetectedSignal(
                signal_type="yoy_change",
                series_id=series.id,
                company_id=None,
                signal_key=f"{series.external_code}:{period}:yoy",
                explanation=f"Variación interanual destacada de {yoy:+.2f}%.",
                strength=abs(yoy),
                geography=geography,
                period_label=period,
                title=f"{series_short}: variación interanual del {yoy:+.2f}%",
                insight=(
                    "La comparación con el mismo periodo del año anterior supera el umbral editorial; "
                    "conviene enlazar con el calendario de publicación del indicador."
                ),
                executive_summary=f"Variación interanual de {yoy:+.2f}% en la fecha {latest.obs_date}.",
                why_it_matters="Aporta contexto de tendencia anual para piezas de seguimiento.",
                dedupe_hash=_hash_signal("yoy_change", series.id, geography, period),
                rule_id=_rule_id(rule_map, "yoy_change"),
            )
        )
    if first and latest and first.obs_value and latest.obs_value:
        change = _pct(latest.obs_value, first.obs_value) or Decimal("0")
        trend_threshold = _rule_threshold(rule_map, "trend_break", "trend_threshold_pct", Decimal("15"))
        if abs(change) >= trend_threshold:
            period = f"{first.obs_date.isoformat()}_{latest.obs_date.isoformat()}"
            tendencia = "al alza" if change > 0 else "a la baja"
            out.append(
                DetectedSignal(
                    signal_type="trend_break",
                    series_id=series.id,
                    company_id=None,
                    signal_key=f"{series.external_code}:{period}:trend",
                    explanation=f"Cambio acumulado destacado ({change:+.2f}%) entre extremos de la ventana analizada.",
                    strength=abs(change),
                    geography=geography,
                    period_label=period,
                    title=(
                        f"{series_short}: {abs(change):.1f}% acumulado de {first.obs_date.year} "
                        f"a {latest.obs_date.year} ({tendencia})"
                    ),
                    insight=(
                        "Entre el primer y el último punto de la ventana el nivel se mueve con una magnitud "
                        "poco habitual; conviene contrastar con revisiones de la serie y el calendario del fenómeno "
                        "(p. ej. demografía o cambios metodológicos)."
                    ),
                    executive_summary=(
                        f"El indicador pasa de {first.obs_value} ({first.obs_date}) a {latest.obs_value} "
                        f"({latest.obs_date}), es decir un cambio acumulado de aproximadamente {change:+.2f}%."
                    ),
                    why_it_matters=(
                        "Sirve de ancla de contexto para explicar la dinámica del fenómeno o comparativas "
                        "territoriales."
                    ),
                    dedupe_hash=_hash_signal("trend_break", series.id, geography, period),
                    rule_id=_rule_id(rule_map, "trend_break"),
                )
            )
    values_for_stats = [float(o.obs_value) for o in obs if o.obs_value is not None]
    if len(values_for_stats) >= 8 and latest.obs_value is not None:
        s = pd.Series(values_for_stats)
        rolling_mean = s.rolling(window=6, min_periods=6).mean().iloc[-1]
        rolling_std = s.rolling(window=6, min_periods=6).std().iloc[-1]
        if pd.notna(rolling_mean) and pd.notna(rolling_std) and rolling_std > 0:
            z_score = (float(latest.obs_value) - float(rolling_mean)) / float(rolling_std)
            z_threshold = float(
                _rule_threshold(rule_map, "statistical_anomaly", "zscore_threshold", Decimal("2.5"))
            )
            if abs(z_score) >= z_threshold:
                period = latest.obs_date.isoformat()
                out.append(
                    DetectedSignal(
                        signal_type="statistical_anomaly",
                        series_id=series.id,
                        company_id=None,
                        signal_key=f"{series.external_code}:{period}:zscore",
                        explanation=f"Anomalía estadística (z-score={z_score:.2f}) frente a media móvil.",
                        strength=Decimal(str(abs(round(z_score, 4)))),
                        geography=geography,
                        period_label=period,
                        title=f"{series_short}: anomalía estadística respecto al tramo reciente",
                        insight=(
                            "El último dato se aleja de forma relevante de la media móvil reciente; "
                            "puede tratarse de un pico puntual o de un cambio de régimen."
                        ),
                        executive_summary=(
                            f"Valor {latest.obs_value} el {latest.obs_date} con z-score {z_score:.2f} "
                            "respecto a la ventana móvil."
                        ),
                        why_it_matters="Señal temprana para revisar un choque exógeno o un cambio metodológico.",
                        dedupe_hash=_hash_signal("statistical_anomaly", series.id, geography, period),
                        rule_id=_rule_id(rule_map, "statistical_anomaly"),
                    )
                )
    return out


def detect_divergence_signals(
    db: Session, rule_map: dict[str, dict[str, object]] | None = None, limit_pairs: int = 50
) -> list[DetectedSignal]:
    rule_map = rule_map or {}
    rows = list(
        db.scalars(
            select(Series)
            .where(Series.category_id.is_not(None))
            .order_by(Series.updated_at.desc())
            .limit(120)
        ).all()
    )
    by_category: dict[int, list[Series]] = {}
    for series in rows:
        if series.category_id is None:
            continue
        by_category.setdefault(series.category_id, []).append(series)
    out: list[DetectedSignal] = []
    processed = 0
    for _, series_list in by_category.items():
        if len(series_list) < 2:
            continue
        for left in series_list:
            for right in series_list:
                if left.id >= right.id:
                    continue
                left_obs = db.scalars(
                    select(SeriesObservation)
                    .where(SeriesObservation.series_id == left.id)
                    .order_by(SeriesObservation.obs_date.asc())
                    .limit(24)
                ).all()
                right_obs = db.scalars(
                    select(SeriesObservation)
                    .where(SeriesObservation.series_id == right.id)
                    .order_by(SeriesObservation.obs_date.asc())
                    .limit(24)
                ).all()
                if len(left_obs) < 2 or len(right_obs) < 2:
                    continue
                left_change = _pct(left_obs[-1].obs_value, left_obs[-2].obs_value)
                right_change = _pct(right_obs[-1].obs_value, right_obs[-2].obs_value)
                if left_change is None or right_change is None:
                    continue
                divergence = abs(left_change - right_change)
                divergence_threshold = _rule_threshold(
                    rule_map, "series_divergence", "divergence_threshold_pct", Decimal("8")
                )
                if divergence >= divergence_threshold:
                    period = left_obs[-1].obs_date.isoformat()
                    signal_type = "series_divergence"
                    out.append(
                        DetectedSignal(
                            signal_type=signal_type,
                            series_id=left.id,
                            company_id=None,
                            signal_key=f"{left.external_code}:{right.external_code}:{period}",
                            explanation=(
                                f"Divergencia de {divergence:.2f}pp entre {left.name} y {right.name} en ultimo periodo."
                            ),
                            strength=divergence,
                            geography=None,
                            period_label=period,
                            title=f"Divergencia entre {left.name} y {right.name}",
                            insight="Dos series comparables muestran trayectorias desacopladas.",
                            executive_summary=(
                                f"{left.name} cambia {left_change:.2f}% y {right.name} {right_change:.2f}%."
                            ),
                            why_it_matters="Puede abrir angulo de explicacion sectorial o territorial.",
                            dedupe_hash=_hash_signal(signal_type, left.id, None, period),
                            rule_id=_rule_id(rule_map, signal_type),
                        )
                    )
                processed += 1
                if processed >= limit_pairs:
                    return out
    return out


def detect_filing_signals(
    db: Session, rule_map: dict[str, dict[str, object]] | None = None, limit: int = 100
) -> list[DetectedSignal]:
    rule_map = rule_map or {}
    filings = list(db.scalars(select(Filing).order_by(Filing.id.desc()).limit(limit)).all())
    out: list[DetectedSignal] = []
    for filing in filings:
        if filing.filing_date is None:
            continue
        period = filing.filing_date.isoformat()
        out.append(
            DetectedSignal(
                signal_type="new_filing",
                series_id=None,
                company_id=filing.company_id,
                signal_key=f"filing:{filing.company_id}:{filing.id}",
                explanation=f"Nuevo filing '{filing.filing_type}' para company_id={filing.company_id}.",
                strength=Decimal("6"),
                geography=None,
                period_label=period,
                title="Nueva publicacion regulatoria detectada",
                insight="Se ha detectado un nuevo documento publico de empresa.",
                executive_summary=f"Filing {filing.filing_type} con fecha {filing.filing_date}.",
                why_it_matters="Puede detonar seguimiento de resultados, gobierno corporativo o riesgos.",
                dedupe_hash=_hash_signal("new_filing", filing.company_id, None, period),
                rule_id=_rule_id(rule_map, "new_filing"),
            )
        )
    return out


def detect_company_snapshot_changes(
    db: Session, rule_map: dict[str, dict[str, object]] | None = None, limit: int = 200
) -> list[DetectedSignal]:
    rule_map = rule_map or {}
    rows = list(
        db.scalars(select(CompanySnapshot).order_by(CompanySnapshot.snapshot_date.desc()).limit(limit)).all()
    )
    by_company: dict[int, list[CompanySnapshot]] = {}
    for row in rows:
        by_company.setdefault(row.company_id, []).append(row)
    out: list[DetectedSignal] = []
    for company_id, snaps in by_company.items():
        if len(snaps) < 2:
            continue
        latest, prev = snaps[0], snaps[1]
        changes = []
        if latest.status != prev.status:
            changes.append("status")
        if latest.legal_form != prev.legal_form:
            changes.append("legal_form")
        if latest.province != prev.province or latest.municipality != prev.municipality:
            changes.append("location")
        if not changes:
            continue
        period = latest.snapshot_date.isoformat()
        out.append(
            DetectedSignal(
                signal_type="business_fabric_change",
                series_id=None,
                company_id=company_id,
                signal_key=f"snapshot:{company_id}:{period}",
                explanation=f"Cambio societario detectado: {', '.join(changes)}.",
                strength=Decimal(str(min(10, 4 + len(changes) * 2))),
                geography=latest.province,
                period_label=period,
                title="Cambio relevante en tejido empresarial",
                insight="La ficha mercantil muestra variaciones relevantes respecto al snapshot previo.",
                executive_summary=f"Cambios detectados ({', '.join(changes)}) en {period}.",
                why_it_matters="Puede anticipar reestructuraciones, movimientos de sede o cambios de estatus.",
                dedupe_hash=_hash_signal("business_fabric_change", company_id, latest.province, period),
                rule_id=_rule_id(rule_map, "business_fabric_change"),
            )
        )
    return out


def run_signal_detection(db: Session, limit_series: int = 200) -> list[DetectedSignal]:
    rule_map = _build_rule_map(db)
    rows = db.scalars(select(Series).order_by(Series.updated_at.desc()).limit(limit_series)).all()
    signals: list[DetectedSignal] = []
    for series in rows:
        signals.extend(detect_signals_for_series(db, series, rule_map=rule_map))
    signals.extend(detect_divergence_signals(db, rule_map=rule_map))
    signals.extend(detect_filing_signals(db, rule_map=rule_map))
    signals.extend(detect_company_snapshot_changes(db, rule_map=rule_map))
    return signals


def run_signal_detection_with_rule_map(
    db: Session,
    rule_map: dict[str, dict[str, object]],
    limit_series: int = 200,
) -> list[DetectedSignal]:
    rows = db.scalars(select(Series).order_by(Series.updated_at.desc()).limit(limit_series)).all()
    signals: list[DetectedSignal] = []
    for series in rows:
        signals.extend(detect_signals_for_series(db, series, rule_map=rule_map))
    signals.extend(detect_divergence_signals(db, rule_map=rule_map))
    signals.extend(detect_filing_signals(db, rule_map=rule_map))
    signals.extend(detect_company_snapshot_changes(db, rule_map=rule_map))
    return signals


def simulate_signals_for_series(
    db: Session,
    series_id: int,
    overrides: dict[str, object] | None = None,
) -> list[DetectedSignal]:
    series = db.get(Series, series_id)
    if not series:
        raise ValueError("Series not found")
    rule_map = _build_rule_map(db)
    if overrides:
        for signal_type, params in overrides.items():
            if not isinstance(params, dict):
                continue
            current = dict(rule_map.get(signal_type, {}))
            current.update(params)
            rule_map[signal_type] = current
    return detect_signals_for_series(db, series, rule_map=rule_map)
