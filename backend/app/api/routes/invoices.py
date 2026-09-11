from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.invoice import InvoiceRecord, InvoiceUpdate
from app.services.invoice_repository import get_invoice, list_invoices, update_invoice

router = APIRouter(tags=["invoices"])


@router.get(
    "/invoices",
    response_model=list[InvoiceRecord],
    status_code=status.HTTP_200_OK,
    summary="List saved invoices",
)
def read_invoices(db: Session = Depends(get_db)) -> list[InvoiceRecord]:
    try:
        return list_invoices(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load invoices. Check the PostgreSQL connection and invoices table.",
        ) from exc


@router.get(
    "/invoice/{invoice_id}",
    response_model=InvoiceRecord,
    status_code=status.HTTP_200_OK,
    summary="Get one saved invoice",
)
def read_invoice(invoice_id: int, db: Session = Depends(get_db)) -> InvoiceRecord:
    try:
        invoice = get_invoice(db, invoice_id)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load invoice. Check the PostgreSQL connection and invoices table.",
        ) from exc

    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found.",
        )

    return invoice


@router.patch(
    "/invoice/{invoice_id}",
    response_model=InvoiceRecord,
    status_code=status.HTTP_200_OK,
    summary="Update editable invoice fields",
)
def update_saved_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
) -> InvoiceRecord:
    try:
        invoice = update_invoice(db, invoice_id=invoice_id, data=payload)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not update invoice. Check the PostgreSQL connection and invoices table.",
        ) from exc

    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found.",
        )

    return invoice
