from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    upload_id: str
    status: str = Field(examples=["received"])
    filename: str
    content_type: str
    size_bytes: int = Field(ge=1)
    message: str

