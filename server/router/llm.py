from fastapi import APIRouter, HTTPException
from schemas.chat_schema import UserRequest, Result
from services.llm_service import LLMService

router = APIRouter(
    prefix="/api/v1/chat",
    tags=["Chat (LLM)"]
)

llm_service = LLMService()

@router.post("/", response_model=Result, summary="챗봇 대화 요청")
async def create_chat_response(request: UserRequest):
    result = await llm_service.ask(request.message)
    return result