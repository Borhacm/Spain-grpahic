from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.connectors.cnmv.connector import CNMVConnector
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Company, CompanyIdentifier
from app.services.ingest import ensure_source, finish_run, start_run


def _pick(item: dict[str, object], keys: list[str], default: str = "") -> str:
    lowered = {str(k).lower(): v for k, v in item.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


async def run(dry_run: bool = False) -> dict[str, object]:
    db = SessionLocal()
    connector = CNMVConnector()
    fetched = inserted = updated = failed = 0
    try:
        settings = get_settings()
        source = ensure_source(db, "cnmv", "CNMV", connector.base_url)
        source_run = start_run(db, source.id, "ingest_cnmv_issuers", dry_run)
        rows = await connector.fetch(registry_url=settings.cnmv_registry_url)
        for item in rows:
            fetched += 1
            try:
                if not isinstance(item, dict):
                    failed += 1
                    continue
                isin = _pick(item, ["isin", "codigo_isin", "cod_isin"])
                tax_id = _pick(item, ["nif", "cif", "tax_id"])
                legal_name = _pick(item, ["legal_name", "razon_social", "issuer_name", "name"])
                canonical_name = legal_name or _pick(item, ["name", "issuer"], default=f"CNMV issuer {fetched}")

                company = None
                if isin:
                    company = db.scalar(
                        select(Company)
                        .join(CompanyIdentifier, CompanyIdentifier.company_id == Company.id)
                        .where(
                            CompanyIdentifier.identifier_type == "isin",
                            CompanyIdentifier.identifier_value == isin,
                        )
                    )
                if company is None and tax_id:
                    company = db.scalar(
                        select(Company)
                        .join(CompanyIdentifier, CompanyIdentifier.company_id == Company.id)
                        .where(
                            CompanyIdentifier.identifier_type == "nif",
                            CompanyIdentifier.identifier_value == tax_id,
                        )
                    )
                if company is None:
                    company = Company(
                        canonical_name=canonical_name,
                        legal_name=legal_name or canonical_name,
                        company_type="issuer",
                        is_listed=True,
                        source_confidence=Decimal("0.900"),
                    )
                    db.add(company)
                    db.flush()
                    inserted += 1
                else:
                    company.canonical_name = canonical_name or company.canonical_name
                    if legal_name:
                        company.legal_name = legal_name
                    company.is_listed = True
                    updated += 1

                if isin and not db.scalar(
                    select(CompanyIdentifier).where(
                        CompanyIdentifier.identifier_type == "isin",
                        CompanyIdentifier.identifier_value == isin,
                    )
                ):
                    db.add(
                        CompanyIdentifier(
                            company_id=company.id,
                            identifier_type="isin",
                            identifier_value=isin,
                            source_id=source.id,
                        )
                    )
                if tax_id and not db.scalar(
                    select(CompanyIdentifier).where(
                        CompanyIdentifier.identifier_type == "nif",
                        CompanyIdentifier.identifier_value == tax_id,
                    )
                ):
                    db.add(
                        CompanyIdentifier(
                            company_id=company.id,
                            identifier_type="nif",
                            identifier_value=tax_id,
                            source_id=source.id,
                        )
                    )
            except Exception:
                failed += 1
        if not dry_run:
            db.commit()
        finish_run(db, source_run, "partial" if failed else "success", fetched, inserted, updated, failed)
        db.commit()
        return {
            "pipeline": "ingest_cnmv_issuers",
            "fetched": fetched,
            "inserted": inserted,
            "updated": updated,
            "failed": failed,
            "configured_registry_url": bool(get_settings().cnmv_registry_url),
        }
    except Exception as exc:
        db.rollback()
        return {"status": "failed", "error": str(exc)}
    finally:
        await connector.close()
        db.close()
