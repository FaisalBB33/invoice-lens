from pydantic import BaseModel, Field


class InvoiceData(BaseModel):
    invoice_number: str = Field(description="Invoice number exactly as shown, or empty string.")
    vendor_name: str = Field(description="Vendor or supplier name, or empty string.")
    date: str = Field(description="Invoice date in YYYY-MM-DD format when possible, or empty string.")
    total_amount: float = Field(description="Invoice total amount as a number, or 0.")
    vat: float = Field(description="VAT or tax amount as a number, or 0.")
    currency: str = Field(description="Three-letter currency code when possible, or empty string.")


class ExtractResponse(BaseModel):
    invoice_id: int
    filename: str
    content_type: str
    size_bytes: int
    raw_text: str
    data: InvoiceData
    message: str
