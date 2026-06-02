from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.models.ai import ChatBodyV2
from app.services import aiServ
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
async def chat_stream(chat_body: ChatBodyV2, current_user=Depends(get_current_active_user)):
    stream_generator = aiServ.chat_stream(
        model=chat_body.model,
        messages=chat_body.content.get("messages", []),  # type: ignore
        **(chat_body.kwargs or {}),
    )
    await aiServ.update_user_model_cfg(current_user.id, chat_body)
    return StreamingResponse(
        stream_generator,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/image_generate", summary="图像生成")
async def image_generate(chat_body: ChatBodyV2, current_user=Depends(get_current_active_user)):
    result = await aiServ.image_generate(
        model=chat_body.model,
        prompt=chat_body.content.get("prompt", ""),  # type: ignore
        **(chat_body.kwargs or {}),
    )
    await aiServ.update_user_model_cfg(current_user.id, chat_body)
    return {
        "message": "success",
        "code": 200,
        "data": result,
    }

