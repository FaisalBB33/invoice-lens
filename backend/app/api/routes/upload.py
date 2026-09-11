from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.models.upload import UploadResponse
from app.services.upload_service import UploadValidationError, process_upload

router = APIRouter(tags=["invoices"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Receive an invoice file",
)
async def upload_invoice(file: UploadFile = File(...)) -> UploadResponse:
    try:
        return await process_upload(file)
    except UploadValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

