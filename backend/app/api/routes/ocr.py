from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.models.ocr import OcrResponse
from app.services.ocr_service import OcrProcessingError, extract_text_from_upload
from app.services.upload_service import UploadValidationError

router = APIRouter(tags=["invoices"])


@router.post(
    "/ocr",
    response_model=OcrResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract raw OCR text from an invoice file",
)
async def ocr_invoice(file: UploadFile = File(...)) -> OcrResponse:
    try:
        return await extract_text_from_upload(file)
    except (UploadValidationError, OcrProcessingError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

