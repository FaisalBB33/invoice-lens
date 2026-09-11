from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class SqlPlan(BaseModel):
    sql: str = Field(description="A single read-only SELECT query against the invoices table.")


class ChatAnswer(BaseModel):
    answer: str = Field(description="A concise answer based only on the provided database rows.")


class ChatResponse(BaseModel):
    answer: str
    sql: str
    rows: list[dict[str, Any]]

