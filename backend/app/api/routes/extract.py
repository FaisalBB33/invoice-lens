from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.extract import ExtractResponse
from app.services.ai_service import AiExtractionError, extract_invoice_data
from app.services.invoice_repository import create_invoice
from app.services.ocr_service import OcrProcessingError, extract_text_from_upload
from app.services.upload_service import UploadValidationError

router = APIRouter(tags=["invoices"])


@router.post(
    "/extract",
    response_model=ExtractResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract structured invoice JSON from an invoice file",
)
async def extract_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ExtractResponse:
    try:
        ocr_result = await extract_text_from_upload(file)
        invoice_data = extract_invoice_data(ocr_result.raw_text)
        saved_invoice = create_invoice(
            db,
            data=invoice_data,
            raw_text=ocr_result.raw_text,
        )
    except (UploadValidationError, OcrProcessingError, AiExtractionError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not save invoice data. Check the PostgreSQL connection and invoices table.",
        ) from exc

    return ExtractResponse(
        invoice_id=saved_invoice.id,
        filename=ocr_result.filename,
        content_type=ocr_result.content_type,
        size_bytes=ocr_result.size_bytes,
        raw_text=ocr_result.raw_text,
        data=invoice_data,
        message="Structured invoice data extracted and saved successfully.",
    )
