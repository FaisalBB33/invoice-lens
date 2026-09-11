from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatServiceError, chat_with_invoices

router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask questions about saved invoices",
)
def chat_with_saved_invoices(
    request: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    try:
        return chat_with_invoices(db, request.question)
    except ChatServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

