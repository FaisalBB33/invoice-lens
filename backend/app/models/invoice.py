from datetime import date as Date
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InvoiceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_number: str | None = None
    vendor_name: str | None = None
    date: Date | None = None
    total_amount: float | None = Field(default=None)
    vat: float | None = Field(default=None)
    currency: str | None = None

    @field_validator("invoice_number", "vendor_name", "currency", mode="before")
    @classmethod
    def empty_text_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = str(value).strip()
        return stripped or None

    @field_validator("date", mode="before")
    @classmethod
    def empty_date_to_none(cls, value: str | Date | None) -> str | Date | None:
        if value == "":
            return None
        return value


class InvoiceRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_number: str | None
    vendor_name: str | None
    date: Date | None
    total_amount: float | None
    vat: float | None
    currency: str | None
    raw_text: str | None
    created_at: datetime
