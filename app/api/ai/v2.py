from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.models.ai import ChatBody
from app.services import aiServ
from app.utils.chatbot import Chatbot
from app.utils.auth import get_current_active_user
from fastapi import Depends

router = APIRouter(prefix="/ai/v2")


@router.get("/models", summary="获取可用的模型列表")
async def get_available_models(current_user=Depends(get_current_active_user)):
    models = await aiServ.get_models_v2(current_user.id)
    return {
        "message": "success",
        "code": 200,
        "data": models,
    }


@router.post("/chat_stream", summary="实时聊天流")
async def chat_stream(chat_body: ChatBody, current_user=Depends(get_current_active_user)):
    chatbot = Chatbot(modelType=chat_body.model_type or "DeepSeek")
    stream_generator = chatbot.async_chat_stream(
        model=chat_body.model or "deepseek-chat",
        messages=chat_body.content.get("messages", []),  # type: ignore
    )
    return StreamingResponse(
        stream_generator,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
