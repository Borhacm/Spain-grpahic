from app.db.session import SessionLocal
from app.editorial.models import PublicationTarget, SignalRule
from app.models import Source


def main() -> None:
    db = SessionLocal()
    try:
        for slug, name, url in [
            ("datosgob", "datos.gob.es", "https://datos.gob.es"),
            ("ine", "Instituto Nacional de Estadistica", "https://ine.es"),
            ("bde", "Banco de Espana", "https://www.bde.es"),
            ("oecd", "OECD", "https://sdmx.oecd.org"),
            ("fmi", "Fondo Monetario Internacional", "https://www.imf.org/external/datamapper/api/v2"),
            ("aemet", "AEMET", "https://www.aemet.es"),
            ("cnmv", "CNMV", "https://www.cnmv.es"),
            ("registradores", "Registradores", "https://www.registradores.org"),
            ("bme", "BME", "https://www.bolsasymercados.es"),
        ]:
            existing = db.query(Source).filter(Source.slug == slug).first()
            if not existing:
                db.add(Source(slug=slug, name=name, base_url=url, source_type="mixed"))

        if not db.query(PublicationTarget).filter(PublicationTarget.slug == "internal").first():
            db.add(
                PublicationTarget(
                    slug="internal",
                    name="Internal Frontend",
                    adapter_type="dry_run",
                    config_json={"destination": "internal"},
                    enabled=True,
                )
            )

        default_rules = [
            (
                "strong-period-change",
                "Strong period change",
                "strong_period_change",
                1.5,
                {"mom_threshold_pct": 5},
            ),
            ("yoy-change", "Year-over-year change", "yoy_change", 1.2, {"yoy_threshold_pct": 10}),
            (
                "historical-max",
                "Historical maximum",
                "historical_max",
                1.3,
                {"window": 60},
            ),
            (
                "historical-min",
                "Historical minimum",
                "historical_min",
                1.3,
                {"window": 60},
            ),
            (
                "statistical-anomaly",
                "Statistical anomaly",
                "statistical_anomaly",
                1.4,
                {"zscore_threshold": 2.5},
            ),
            (
                "series-divergence",
                "Series divergence",
                "series_divergence",
                1.1,
                {"divergence_threshold_pct": 8},
            ),
            ("trend-break", "Trend break", "trend_break", 1.0, {"trend_threshold_pct": 15}),
        ]
        for slug, name, signal_type, weight, params in default_rules:
            exists_rule = db.query(SignalRule).filter(SignalRule.slug == slug).first()
            if not exists_rule:
                db.add(
                    SignalRule(
                        slug=slug,
                        name=name,
                        signal_type=signal_type,
                        params_json=params,
                        weight=weight,
                        enabled=True,
                        description=f"Default rule for {signal_type}",
                    )
                )
        db.commit()
        print("Seed completed")
    finally:
        db.close()


if __name__ == "__main__":
    main()
