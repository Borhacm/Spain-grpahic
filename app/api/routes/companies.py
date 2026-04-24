from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Company, CompanySnapshot, Filing
from app.schemas import CompanyOut, CompanySnapshotOut, FilingOut

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyOut])
def list_companies(db: Session = Depends(get_db), limit: int = 100) -> list[Company]:
    return list(db.scalars(select(Company).order_by(Company.id.desc()).limit(limit)).all())


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: int, db: Session = Depends(get_db)) -> Company:
    row = db.get(Company, company_id)
    if not row:
        raise HTTPException(status_code=404, detail="Company not found")
    return row


@router.get("/{company_id}/snapshots", response_model=list[CompanySnapshotOut])
def list_snapshots(company_id: int, db: Session = Depends(get_db), limit: int = 50) -> list[CompanySnapshot]:
    return list(
        db.scalars(
            select(CompanySnapshot)
            .where(CompanySnapshot.company_id == company_id)
            .order_by(CompanySnapshot.snapshot_date.desc())
            .limit(limit)
        ).all()
    )


@router.get("/{company_id}/filings", response_model=list[FilingOut])
def list_filings(company_id: int, db: Session = Depends(get_db), limit: int = 100) -> list[Filing]:
    return list(
        db.scalars(
            select(Filing)
            .where(Filing.company_id == company_id)
            .order_by(Filing.filing_date.desc())
            .limit(limit)
        ).all()
    )


@router.get("/search", response_model=list[CompanyOut])
def search_companies(q: str = Query(min_length=2), db: Session = Depends(get_db)) -> list[Company]:
    return list(
        db.scalars(select(Company).where(Company.canonical_name.ilike(f"%{q}%")).limit(50)).all()
    )
