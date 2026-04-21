from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.models.ai import ChatBody
from app.services import aiServ
from app.models.tables.databaseTables import Chat_Session
from app.utils.chatbot import Chatbot
from app.utils.auth import get_current_active_user
from fastapi import Depends
from datetime import datetime

router = APIRouter(prefix="/ai/v1")


@router.get("/sessions", summary="获取当前用户的会话列表")
async def get_user_sessions(current_user=Depends(get_current_active_user)):
    data = await aiServ.get_user_sessions(current_user.id)
    return {
        "message": "success",
        "code": 200,
        "data": data,
    }


@router.get("/session", summary="获取指定会话的内容")
async def get_session_content(session_id: str, current_user=Depends(get_current_active_user)):
    session = await aiServ.get_session_content(session_id)
    return {
        "message": "success",
        "code": 200,
        "data": session,
    }


@router.post("/add_session", summary="添加新的会话")
async def add_session(chat_body: ChatBody, current_user=Depends(get_current_active_user)):
    session = await aiServ.add_session(chat_body, current_user.id)
    return {
        "message": "success",
        "code": 200,
        "data": session,
    }


@router.post("/update_session", summary="更新会话信息")
async def update_session(chat: Chat_Session, current_user=Depends(get_current_active_user)):
    session = await aiServ.update_session(chat)
    return {
        "message": "success",
        "code": 200,
        "data": session,
    }


@router.get("/models", summary="获取可用的模型列表")
async def get_available_models(current_user=Depends(get_current_active_user)):
    # 这里应该调用数据库查询用户可用的模型，暂时返回一个示例数据
    return {
        "message": "success",
        "code": 200,
        "data": [
            {
                "modelType": "deepseek",
                "model": "deepseek-chat",
            },
            {
                "modelType": "doubao",
                "model": "doubao-chat",
            },
            {
                "modelType": "gpt",
                "model": "gpt-3.5-turbo",
            },
        ],
    }


@router.post("/chat_stream", summary="实时聊天流")
async def chat_stream(chat_body: ChatBody, current_user=Depends(get_current_active_user)):
    chatbot = Chatbot(modelType=chat_body.model_type or "deepseek")
    stream_generator = chatbot.async_chat_stream(
        model=chat_body.model or "deepseek-chat",
        messages=chat_body.content.get("messages", []),  # type: ignore
    )
    return StreamingResponse(
        stream_generator,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
