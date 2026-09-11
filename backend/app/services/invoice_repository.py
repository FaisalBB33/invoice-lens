from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Invoice
from app.models.extract import InvoiceData
from app.models.invoice import InvoiceUpdate


def _parse_invoice_date(value: str) -> date | None:
    if not value:
        return None

    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def create_invoice(
    db: Session,
    *,
    data: InvoiceData,
    raw_text: str,
) -> Invoice:
    invoice = Invoice(
        invoice_number=data.invoice_number or None,
        vendor_name=data.vendor_name or None,
        date=_parse_invoice_date(data.date),
        total_amount=data.total_amount,
        vat=data.vat,
        currency=data.currency or None,
        raw_text=raw_text,
    )

    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    return invoice


def list_invoices(db: Session) -> list[Invoice]:
    statement = select(Invoice).order_by(Invoice.created_at.desc(), Invoice.id.desc())
    return list(db.scalars(statement).all())


def get_invoice(db: Session, invoice_id: int) -> Invoice | None:
    return db.get(Invoice, invoice_id)


def update_invoice(
    db: Session,
    *,
    invoice_id: int,
    data: InvoiceUpdate,
) -> Invoice | None:
    invoice = get_invoice(db, invoice_id)
    if invoice is None:
        return None

    invoice.invoice_number = data.invoice_number
    invoice.vendor_name = data.vendor_name
    invoice.date = data.date
    invoice.total_amount = data.total_amount
    invoice.vat = data.vat
    invoice.currency = data.currency

    db.commit()
    db.refresh(invoice)

    return invoice
