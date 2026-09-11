import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _parse_origins(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]


@dataclass(frozen=True)
class Settings:
    allowed_origins: list[str]
    max_upload_size_mb: int
    openai_api_key: str | None
    openai_model: str
    database_url: str | None
    tesseract_cmd: str | None
    ocr_pdf_dpi: int
    ocr_max_pdf_pages: int

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


settings = Settings(
    allowed_origins=_parse_origins(
        os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    ),
    max_upload_size_mb=int(os.getenv("MAX_UPLOAD_SIZE_MB", "10")),
    openai_api_key=os.getenv("OPENAI_API_KEY") or None,
    openai_model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
    database_url=os.getenv("DATABASE_URL") or None,
    tesseract_cmd=os.getenv("TESSERACT_CMD") or None,
    ocr_pdf_dpi=int(os.getenv("OCR_PDF_DPI", "200")),
    ocr_max_pdf_pages=int(os.getenv("OCR_MAX_PDF_PAGES", "5")),
)
