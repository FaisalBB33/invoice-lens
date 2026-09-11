import json
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import status
from openai import APIError, OpenAI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chat import ChatAnswer, ChatResponse, SqlPlan

INVOICE_SCHEMA = """
Table: invoices
Columns:
- id INTEGER PRIMARY KEY
- invoice_number TEXT
- vendor_name TEXT
- date DATE
- total_amount FLOAT
- vat FLOAT
- currency TEXT
- raw_text TEXT
- created_at TIMESTAMP
"""

DANGEROUS_SQL_WORDS = (
    "alter",
    "call",
    "copy",
    "create",
    "delete",
    "drop",
    "execute",
    "grant",
    "insert",
    "merge",
    "replace",
    "revoke",
    "truncate",
    "update",
    "vacuum",
)


class ChatServiceError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _get_client() -> OpenAI:
    api_key = settings.openai_api_key
    if not api_key or api_key == "your_api_key_here":
        raise ChatServiceError(
            "OPENAI_API_KEY is not configured. Add it to backend/.env before using /chat.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return OpenAI(api_key=api_key)


def _strip_optional_trailing_semicolon(sql: str) -> str:
    stripped = sql.strip()
    if stripped.endswith(";"):
        stripped = stripped[:-1].strip()
    return stripped


def validate_readonly_invoice_sql(sql: str) -> str:
    cleaned = _strip_optional_trailing_semicolon(sql)
    lowered = cleaned.lower()

    if not cleaned:
        raise ChatServiceError(
            "The generated SQL query was empty.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    if ";" in cleaned or "--" in cleaned or "/*" in cleaned or "*/" in cleaned:
        raise ChatServiceError(
            "The generated SQL query contains unsupported SQL syntax.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    if not re.match(r"^\s*select\b", lowered):
        raise ChatServiceError(
            "Only read-only SELECT queries are allowed.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    dangerous_pattern = r"\b(" + "|".join(DANGEROUS_SQL_WORDS) + r")\b"
    if re.search(dangerous_pattern, lowered):
        raise ChatServiceError(
            "The generated SQL query is not read-only.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    referenced_tables = re.findall(r"\b(?:from|join)\s+([a-zA-Z_][\w.]*)", lowered)
    if not referenced_tables:
        raise ChatServiceError(
            "The generated SQL query must read from the invoices table.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    allowed_tables = {"invoices", "public.invoices"}
    if any(table not in allowed_tables for table in referenced_tables):
        raise ChatServiceError(
            "Only the invoices table can be queried.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    _validate_total_amount_currency_handling(cleaned)

    if not re.search(r"\blimit\s+\d+\b", lowered):
        cleaned = f"SELECT * FROM ({cleaned}) AS invoice_chat_results LIMIT 50"

    return cleaned


def _json_safe(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _rows_to_dicts(rows: list[Any]) -> list[dict[str, Any]]:
    return [
        {key: _json_safe(value) for key, value in dict(row).items()}
        for row in rows
    ]


def _is_total_amount_across_all_invoices_question(question: str) -> bool:
    normalized = question.lower()
    return (
        "total" in normalized
        and "amount" in normalized
        and "invoice" in normalized
        and any(phrase in normalized for phrase in ("across all", "all invoices"))
    )


def _deterministic_total_amount_plan(question: str) -> SqlPlan | None:
    if not _is_total_amount_across_all_invoices_question(question):
        return None

    return SqlPlan(
        sql=(
            "SELECT currency, SUM(total_amount) AS total_amount "
            "FROM invoices "
            "GROUP BY currency "
            "ORDER BY currency"
        )
    )


def _select_clause(sql: str) -> str:
    match = re.match(r"^\s*select\s+(.*?)\s+from\s+", sql, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).lower() if match else ""


def _validate_total_amount_currency_handling(sql: str) -> None:
    lowered = sql.lower()
    if not re.search(r"\bsum\s*\(\s*total_amount\s*\)", lowered):
        return

    select_clause = _select_clause(sql)
    if "currency" not in select_clause and not (
        select_clause.strip() == "*" and "currency" in lowered
    ):
        raise ChatServiceError(
            "Total amount queries must include the currency column in the SQL result.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


def _find_total_amount_key(row: dict[str, Any]) -> str | None:
    preferred_keys = ("total_amount", "total", "sum", "sum_total_amount")
    for key in preferred_keys:
        if key in row and isinstance(row[key], (int, float)):
            return key

    for key, value in row.items():
        if key == "currency":
            continue
        if isinstance(value, (int, float)) and "total" in key.lower():
            return key

    return None


def _format_money_without_guessing_currency(currency: Any, amount: float) -> str:
    formatted_amount = f"{amount:.2f}"
    if currency is None or str(currency).strip() == "":
        return f"{formatted_amount} (currency missing)"

    return f"{str(currency).strip()} {formatted_amount}"


def _format_currency_total_answer(
    question: str,
    rows: list[dict[str, Any]],
) -> str | None:
    if not _is_total_amount_across_all_invoices_question(question):
        return None

    totals: list[str] = []
    for row in rows:
        total_key = _find_total_amount_key(row)
        if total_key is None:
            return None

        totals.append(
            _format_money_without_guessing_currency(
                row.get("currency"),
                float(row[total_key]),
            )
        )

    if not totals:
        return "I could not find matching saved invoice data for that question."

    if len(totals) == 1:
        if totals[0].endswith("(currency missing)"):
            return (
                f"The total amount across all invoices is {totals[0]}. "
                "Currency is missing, so I will not guess one."
            )
        return f"The total amount across all invoices is {totals[0]}."

    return (
        "The matching invoices contain multiple currencies, so I will not combine "
        f"them into one total. Totals by currency: {'; '.join(totals)}."
    )


def create_sql_plan(question: str) -> SqlPlan:
    deterministic_plan = _deterministic_total_amount_plan(question)
    if deterministic_plan is not None:
        return deterministic_plan

    client = _get_client()

    try:
        response = client.responses.parse(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You convert invoice questions into PostgreSQL SELECT queries. "
                        "Use only the invoices table and only the columns in the schema. "
                        "Never write INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or other "
                        "mutating SQL. Return one SELECT query. Include LIMIT 50 unless "
                        "the query is a single aggregate result. When summing total_amount, "
                        "the SQL result must include currency. If matching invoices may have "
                        "multiple currencies, group totals by currency instead of combining "
                        "currencies into one number. Do not use or invent currency symbols."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"{INVOICE_SCHEMA}\n\n"
                        f"Question: {question}\n\n"
                        "Return SQL that can answer the question from saved invoices."
                    ),
                },
            ],
            text_format=SqlPlan,
        )
    except APIError as exc:
        raise ChatServiceError(
            "OpenAI could not create a database query for this question. Try again later.",
            status.HTTP_502_BAD_GATEWAY,
        ) from exc
    except Exception as exc:
        raise ChatServiceError(
            "Chat query planning failed. Check the OpenAI key, model, and response schema.",
            status.HTTP_502_BAD_GATEWAY,
        ) from exc

    plan = response.output_parsed
    if plan is None:
        raise ChatServiceError(
            "OpenAI returned no SQL plan for this question.",
            status.HTTP_502_BAD_GATEWAY,
        )

    return plan


def execute_invoice_query(db: Session, sql: str) -> list[dict[str, Any]]:
    safe_sql = validate_readonly_invoice_sql(sql)

    try:
        result = db.execute(text(safe_sql))
    except SQLAlchemyError as exc:
        raise ChatServiceError(
            "Could not run the generated invoice query.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc

    return _rows_to_dicts(result.mappings().all())


def create_answer(question: str, sql: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "I could not find matching saved invoice data for that question."

    deterministic_answer = _format_currency_total_answer(question, rows)
    if deterministic_answer is not None:
        return deterministic_answer

    client = _get_client()

    try:
        response = client.responses.parse(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Answer invoice questions using only the provided SQL result rows. "
                        "Do not invent vendors, amounts, dates, invoice numbers, or totals. "
                        "Never assume or invent currency symbols like $. Use the currency "
                        "column exactly as returned by the SQL rows. If currency is null or "
                        "missing, say the currency is missing and do not guess. If totals are "
                        "returned for multiple currencies, keep totals separate by currency. "
                        "If the rows do not contain enough information, say that the saved "
                        "invoice data does not contain the answer."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "question": question,
                            "sql": sql,
                            "rows": rows,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            text_format=ChatAnswer,
        )
    except APIError as exc:
        raise ChatServiceError(
            "OpenAI could not summarize the invoice query results. Try again later.",
            status.HTTP_502_BAD_GATEWAY,
        ) from exc
    except Exception as exc:
        raise ChatServiceError(
            "Chat answer generation failed. Check the OpenAI key, model, and response schema.",
            status.HTTP_502_BAD_GATEWAY,
        ) from exc

    parsed = response.output_parsed
    if parsed is None:
        raise ChatServiceError(
            "OpenAI returned no chat answer.",
            status.HTTP_502_BAD_GATEWAY,
        )

    return parsed.answer


def chat_with_invoices(db: Session, question: str) -> ChatResponse:
    normalized_question = question.strip()
    if not normalized_question:
        raise ChatServiceError(
            "A question is required.",
            status.HTTP_400_BAD_REQUEST,
        )

    plan = create_sql_plan(normalized_question)
    safe_sql = validate_readonly_invoice_sql(plan.sql)
    rows = execute_invoice_query(db, safe_sql)
    answer = create_answer(normalized_question, safe_sql, rows)

    return ChatResponse(answer=answer, sql=safe_sql, rows=rows)
