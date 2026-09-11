from io import BytesIO

import fitz
import pytesseract
from fastapi import UploadFile, status
from PIL import Image, UnidentifiedImageError
from pytesseract import TesseractNotFoundError

from app.core.config import settings
from app.models.ocr import OcrResponse
from app.services.upload_service import (
    UploadValidationError,
    ValidatedUpload,
    read_validated_upload,
)


class OcrProcessingError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _configure_tesseract() -> None:
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


def _ocr_image(image: Image.Image) -> str:
    _configure_tesseract()
    try:
        return pytesseract.image_to_string(image)
    except TesseractNotFoundError as exc:
        raise OcrProcessingError(
            "Tesseract OCR is not installed or is not on PATH. Install Tesseract "
            "or set TESSERACT_CMD in backend/.env.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc


def _extract_text_from_image(content: bytes) -> str:
    try:
        with Image.open(BytesIO(content)) as image:
            return _ocr_image(image.convert("RGB"))
    except UnidentifiedImageError as exc:
        raise OcrProcessingError(
            "The uploaded image could not be opened for OCR.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from exc


def _extract_text_from_pdf(content: bytes) -> str:
    try:
        document = fitz.open(stream=content, filetype="pdf")
    except fitz.FileDataError as exc:
        raise OcrProcessingError(
            "The uploaded PDF could not be opened for OCR.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from exc

    if document.page_count == 0:
        document.close()
        raise OcrProcessingError(
            "The uploaded PDF does not contain any pages.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    zoom = settings.ocr_pdf_dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    page_text: list[str] = []

    try:
        for page_index in range(min(document.page_count, settings.ocr_max_pdf_pages)):
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.frombytes(
                "RGB",
                (pixmap.width, pixmap.height),
                pixmap.samples,
            )
            page_text.append(_ocr_image(image))
    finally:
        document.close()

    return "\n\n".join(text.strip() for text in page_text if text.strip())


def extract_text_from_file_bytes(content: bytes, content_type: str) -> str:
    if content_type == "application/pdf":
        return _extract_text_from_pdf(content)

    return _extract_text_from_image(content)


async def extract_text_from_upload(file: UploadFile) -> OcrResponse:
    validated: ValidatedUpload = await read_validated_upload(file)

    raw_text = extract_text_from_file_bytes(
        validated.content,
        validated.content_type,
    ).strip()

    if not raw_text:
        raise OcrProcessingError(
            "OCR completed, but no text was detected in this invoice.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    return OcrResponse(
        filename=validated.filename,
        content_type=validated.content_type,
        size_bytes=validated.size_bytes,
        raw_text=raw_text,
        message="OCR text extracted successfully. Structured AI extraction is not enabled in Phase 2.",
    )

