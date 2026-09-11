from pydantic import BaseModel


class OcrResponse(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    raw_text: str
    message: str

