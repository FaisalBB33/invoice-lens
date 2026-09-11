from pathlib import Path
from dataclasses import dataclass
from uuid import uuid4

from fastapi import UploadFile, status

from app.core.config import settings
from app.models.upload import UploadResponse

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
READ_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class ValidatedUpload:
    filename: str
    content_type: str
    size_bytes: int
    content: bytes


class UploadValidationError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


async def read_validated_upload(file: UploadFile) -> ValidatedUpload:
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()
    content_type = (file.content_type or "").lower()

    if not filename:
        raise UploadValidationError(
            "A file with a valid filename is required.",
            status.HTTP_400_BAD_REQUEST,
        )

    if extension not in ALLOWED_EXTENSIONS or content_type not in ALLOWED_CONTENT_TYPES:
        raise UploadValidationError(
            "Unsupported file type. Upload a PDF, PNG, JPEG, or WebP invoice.",
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )

    chunks: list[bytes] = []
    size_bytes = 0
    try:
        while chunk := await file.read(READ_CHUNK_SIZE):
            chunks.append(chunk)
            size_bytes += len(chunk)
            if size_bytes > settings.max_upload_size_bytes:
                raise UploadValidationError(
                    f"File is too large. Maximum size is "
                    f"{settings.max_upload_size_mb} MB.",
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )
    finally:
        await file.close()

    if size_bytes == 0:
        raise UploadValidationError(
            "The uploaded file is empty.",
            status.HTTP_400_BAD_REQUEST,
        )

    return ValidatedUpload(
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        content=b"".join(chunks),
    )


async def process_upload(file: UploadFile) -> UploadResponse:
    validated = await read_validated_upload(file)

    return UploadResponse(
        upload_id=str(uuid4()),
        status="received",
        filename=validated.filename,
        content_type=validated.content_type,
        size_bytes=validated.size_bytes,
        message="Invoice received successfully. Use /ocr to extract raw text in Phase 2.",
    )
