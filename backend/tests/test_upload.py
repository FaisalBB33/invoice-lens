from datetime import date, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.db.database import get_db
from app.main import app
from app.models.chat import ChatResponse
from app.models.extract import InvoiceData
from app.models.ocr import OcrResponse
from app.services.chat_service import (
    ChatServiceError,
    create_answer,
    create_sql_plan,
    validate_readonly_invoice_sql,
)

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "phase": "5"}


def test_cors_allows_patch_invoice_preflight_from_frontend_origins() -> None:
    for origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
        response = client.options(
            "/invoice/7",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "PATCH",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
        assert "PATCH" in response.headers["access-control-allow-methods"]


def test_upload_pdf_returns_receipt() -> None:
    file_content = b"%PDF-1.4 fake invoice content"

    response = client.post(
        "/upload",
        files={"file": ("invoice.pdf", file_content, "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "received"
    assert body["filename"] == "invoice.pdf"
    assert body["content_type"] == "application/pdf"
    assert body["size_bytes"] == len(file_content)
    assert body["upload_id"]


def test_ocr_returns_raw_text(monkeypatch) -> None:
    async def fake_extract_text_from_upload(file):
        return OcrResponse(
            filename=file.filename,
            content_type=file.content_type,
            size_bytes=28,
            raw_text="Invoice Number: INV-2026-0042\nTotal: $1,220.15",
            message="OCR text extracted successfully. Structured AI extraction is not enabled in Phase 2.",
        )

    monkeypatch.setattr(
        "app.api.routes.ocr.extract_text_from_upload",
        fake_extract_text_from_upload,
    )

    response = client.post(
        "/ocr",
        files={"file": ("invoice.pdf", b"%PDF-1.4 fake invoice content", "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "invoice.pdf"
    assert body["raw_text"] == "Invoice Number: INV-2026-0042\nTotal: $1,220.15"


def test_ocr_rejects_unsupported_file() -> None:
    response = client.post(
        "/ocr",
        files={"file": ("invoice.txt", b"not an invoice", "text/plain")},
    )

    assert response.status_code == 415
    assert "Unsupported file type" in response.json()["detail"]


def test_extract_returns_structured_invoice_data(monkeypatch) -> None:
    async def fake_extract_text_from_upload(file):
        return OcrResponse(
            filename=file.filename,
            content_type=file.content_type,
            size_bytes=28,
            raw_text="Invoice Number: INV-2026-0042\nTotal: $1,220.15",
            message="OCR text extracted successfully.",
        )

    def fake_extract_invoice_data(raw_text):
        assert "INV-2026-0042" in raw_text
        return InvoiceData(
            invoice_number="INV-2026-0042",
            vendor_name="Northstar Supplies",
            date="2026-06-21",
            total_amount=1220.15,
            vat=159.15,
            currency="USD",
        )

    def fake_create_invoice(db, *, data, raw_text):
        assert data.invoice_number == "INV-2026-0042"
        assert "Total" in raw_text
        return SimpleNamespace(id=42)

    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(
        "app.api.routes.extract.extract_text_from_upload",
        fake_extract_text_from_upload,
    )
    monkeypatch.setattr(
        "app.api.routes.extract.extract_invoice_data",
        fake_extract_invoice_data,
    )
    monkeypatch.setattr(
        "app.api.routes.extract.create_invoice",
        fake_create_invoice,
    )

    try:
        response = client.post(
            "/extract",
            files={"file": ("invoice.pdf", b"%PDF-1.4 fake invoice content", "application/pdf")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["invoice_id"] == 42
    assert body["filename"] == "invoice.pdf"
    assert body["raw_text"] == "Invoice Number: INV-2026-0042\nTotal: $1,220.15"
    assert body["data"] == {
        "invoice_number": "INV-2026-0042",
        "vendor_name": "Northstar Supplies",
        "date": "2026-06-21",
        "total_amount": 1220.15,
        "vat": 159.15,
        "currency": "USD",
    }


def test_extract_rejects_unsupported_file() -> None:
    app.dependency_overrides[get_db] = lambda: object()
    response = client.post(
        "/extract",
        files={"file": ("invoice.txt", b"not an invoice", "text/plain")},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 415
    assert "Unsupported file type" in response.json()["detail"]


def test_list_invoices_returns_saved_records(monkeypatch) -> None:
    fake_invoice = SimpleNamespace(
        id=42,
        invoice_number="INV-2026-0042",
        vendor_name="Northstar Supplies",
        date=date(2026, 6, 21),
        total_amount=1220.15,
        vat=159.15,
        currency="USD",
        raw_text="Invoice Number: INV-2026-0042",
        created_at=datetime(2026, 6, 21, 12, 30, 0),
    )

    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(
        "app.api.routes.invoices.list_invoices",
        lambda db: [fake_invoice],
    )

    try:
        response = client.get("/invoices")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["id"] == 42
    assert response.json()[0]["invoice_number"] == "INV-2026-0042"


def test_get_invoice_returns_404_when_missing(monkeypatch) -> None:
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(
        "app.api.routes.invoices.get_invoice",
        lambda db, invoice_id: None,
    )

    try:
        response = client.get("/invoice/999")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Invoice not found."


def test_update_invoice_returns_updated_record(monkeypatch) -> None:
    def fake_update_invoice(db, *, invoice_id, data):
        assert invoice_id == 42
        assert data.invoice_number == "INV-UPDATED"
        assert data.vendor_name == "Updated Vendor"
        assert data.date == date(2026, 8, 16)
        assert data.total_amount == 88.02
        assert data.vat == 4.2
        assert data.currency == "SAR"
        assert not hasattr(data, "raw_text")
        return SimpleNamespace(
            id=42,
            invoice_number=data.invoice_number,
            vendor_name=data.vendor_name,
            date=data.date,
            total_amount=data.total_amount,
            vat=data.vat,
            currency=data.currency,
            raw_text="Original OCR text stays unchanged.",
            created_at=datetime(2026, 8, 16, 10, 30, 0),
        )

    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(
        "app.api.routes.invoices.update_invoice",
        fake_update_invoice,
    )

    try:
        response = client.patch(
            "/invoice/42",
            json={
                "invoice_number": "INV-UPDATED",
                "vendor_name": "Updated Vendor",
                "date": "2026-08-16",
                "total_amount": 88.02,
                "vat": 4.2,
                "currency": "SAR",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 42
    assert body["invoice_number"] == "INV-UPDATED"
    assert body["vendor_name"] == "Updated Vendor"
    assert body["date"] == "2026-08-16"
    assert body["total_amount"] == 88.02
    assert body["vat"] == 4.2
    assert body["currency"] == "SAR"
    assert body["raw_text"] == "Original OCR text stays unchanged."


def test_update_invoice_returns_404_when_missing(monkeypatch) -> None:
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(
        "app.api.routes.invoices.update_invoice",
        lambda db, *, invoice_id, data: None,
    )

    try:
        response = client.patch(
            "/invoice/999",
            json={
                "invoice_number": "INV-UPDATED",
                "vendor_name": "Updated Vendor",
                "date": "2026-08-16",
                "total_amount": 88.02,
                "vat": 4.2,
                "currency": "SAR",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Invoice not found."


def test_update_invoice_rejects_invalid_date() -> None:
    app.dependency_overrides[get_db] = lambda: object()
    try:
        response = client.patch(
            "/invoice/42",
            json={
                "invoice_number": "INV-UPDATED",
                "vendor_name": "Updated Vendor",
                "date": "not-a-date",
                "total_amount": 88.02,
                "vat": 4.2,
                "currency": "SAR",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_update_invoice_rejects_raw_text_changes() -> None:
    app.dependency_overrides[get_db] = lambda: object()
    try:
        response = client.patch(
            "/invoice/42",
            json={
                "invoice_number": "INV-UPDATED",
                "vendor_name": "Updated Vendor",
                "date": "2026-08-16",
                "total_amount": 88.02,
                "vat": 4.2,
                "currency": "SAR",
                "raw_text": "Do not change this.",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_chat_returns_answer_from_saved_invoice_rows(monkeypatch) -> None:
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(
        "app.api.routes.chat.chat_with_invoices",
        lambda db, question: ChatResponse(
            answer="The total across saved invoices is USD 1,220.15.",
            sql="SELECT currency, SUM(total_amount) AS total_amount FROM invoices GROUP BY currency",
            rows=[{"currency": "USD", "total_amount": 1220.15}],
        ),
    )

    try:
        response = client.post(
            "/chat",
            json={"question": "What is the total amount across all invoices?"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "The total across saved invoices is USD 1,220.15."
    assert body["sql"] == "SELECT currency, SUM(total_amount) AS total_amount FROM invoices GROUP BY currency"
    assert body["rows"] == [{"currency": "USD", "total_amount": 1220.15}]


def test_chat_validates_question_required() -> None:
    response = client.post("/chat", json={"question": ""})

    assert response.status_code == 422


def test_chat_sql_guard_allows_created_at() -> None:
    sql = validate_readonly_invoice_sql(
        "SELECT id, created_at FROM invoices ORDER BY created_at DESC LIMIT 5"
    )

    assert "created_at" in sql


def test_chat_sql_guard_blocks_mutating_sql() -> None:
    try:
        validate_readonly_invoice_sql("CREATE TABLE nope (id int)")
    except ChatServiceError as exc:
        assert exc.status_code == 422
        assert "read-only" in exc.message
    else:
        raise AssertionError("Expected mutating SQL to be rejected.")


def test_chat_total_amount_plan_groups_by_currency() -> None:
    plan = create_sql_plan("What is the total amount across all invoices?")

    assert "currency" in plan.sql.lower()
    assert "sum(total_amount)" in plan.sql.lower()
    assert "group by currency" in plan.sql.lower()
    assert "currency" in validate_readonly_invoice_sql(plan.sql).lower()


def test_chat_total_amount_answer_uses_sar_code_not_symbol() -> None:
    answer = create_answer(
        "What is the total amount across all invoices?",
        "SELECT currency, SUM(total_amount) AS total_amount FROM invoices GROUP BY currency",
        [{"currency": "SAR", "total_amount": 88.02}],
    )

    assert answer == "The total amount across all invoices is SAR 88.02."
    assert "$" not in answer


def test_chat_total_amount_answer_separates_multiple_currencies() -> None:
    answer = create_answer(
        "What is the total amount across all invoices?",
        "SELECT currency, SUM(total_amount) AS total_amount FROM invoices GROUP BY currency",
        [
            {"currency": "SAR", "total_amount": 88.02},
            {"currency": "USD", "total_amount": 10.5},
        ],
    )

    assert "will not combine" in answer
    assert "SAR 88.02" in answer
    assert "USD 10.50" in answer
    assert "$" not in answer


def test_chat_total_amount_answer_does_not_guess_missing_currency() -> None:
    answer = create_answer(
        "What is the total amount across all invoices?",
        "SELECT currency, SUM(total_amount) AS total_amount FROM invoices GROUP BY currency",
        [{"currency": None, "total_amount": 88.02}],
    )

    assert "88.02 (currency missing)" in answer
    assert "will not guess" in answer
    assert "$" not in answer


def test_chat_sql_guard_requires_currency_for_total_amount_sum() -> None:
    try:
        validate_readonly_invoice_sql("SELECT SUM(total_amount) AS total FROM invoices")
    except ChatServiceError as exc:
        assert exc.status_code == 422
        assert "currency" in exc.message
    else:
        raise AssertionError("Expected total amount aggregate without currency to be rejected.")


def test_upload_rejects_unsupported_file() -> None:
    response = client.post(
        "/upload",
        files={"file": ("invoice.txt", b"not an invoice", "text/plain")},
    )

    assert response.status_code == 415
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_rejects_empty_file() -> None:
    response = client.post(
        "/upload",
        files={"file": ("invoice.pdf", b"", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded file is empty."
