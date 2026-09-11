from openai import APIError, OpenAI
from fastapi import status

from app.core.config import settings
from app.models.extract import InvoiceData


class AiExtractionError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _get_client() -> OpenAI:
    api_key = settings.openai_api_key
    if not api_key or api_key == "your_api_key_here":
        raise AiExtractionError(
            "OPENAI_API_KEY is not configured. Add it to backend/.env before using /extract.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return OpenAI(api_key=api_key)


def extract_invoice_data(raw_text: str) -> InvoiceData:
    text = raw_text.strip()
    if not text:
        raise AiExtractionError(
            "Cannot extract structured invoice data because OCR returned no text.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    client = _get_client()

    try:
        response = client.responses.parse(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You extract invoice fields from OCR text. "
                        "Use only the provided text. Do not guess values. "
                        "If a value is missing, return an empty string for text fields "
                        "or 0 for numeric fields. Return dates as YYYY-MM-DD when possible."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Extract invoice data from this OCR text:\n\n{text}",
                },
            ],
            text_format=InvoiceData,
        )
    except APIError as exc:
        raise AiExtractionError(
            "OpenAI could not extract invoice data from the OCR text. Try again later.",
            status.HTTP_502_BAD_GATEWAY,
        ) from exc
    except Exception as exc:
        raise AiExtractionError(
            "OpenAI extraction failed. Check the API key, model, and response schema.",
            status.HTTP_502_BAD_GATEWAY,
        ) from exc

    parsed = response.output_parsed
    if parsed is None:
        raise AiExtractionError(
            "OpenAI returned no structured invoice data.",
            status.HTTP_502_BAD_GATEWAY,
        )

    return parsed

