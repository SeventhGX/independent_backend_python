from fastapi import APIRouter
from fastapi.responses import StreamingResponse, Response
from app.models.ai import ChatBody
from app.models.file import NewFileRequest, FileResponse
from app.services import aiServ
from app.models.tables.databaseTables import Chat_Session
from app.utils.chatbot import Chatbot
from app.utils.auth import get_current_active_user
from fastapi import Depends, HTTPException
import uuid
from urllib.parse import quote
import base64

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
    models = await aiServ.get_models()
    return {
        "message": "success",
        "code": 200,
        "data": [
            {
                "modelType": model.model_type,
                "model": model.model,
            }
            for model in models
        ],
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


@router.post("/save_file", summary="保存文件")
async def save_file(file_req: NewFileRequest, current_user=Depends(get_current_active_user)):
    file = await aiServ.save_file(file_req)
    return {
        "message": "success",
        "code": 200,
        "data": {"id": file.id},
    }


@router.get("/file", summary="根据id获取文件", response_model=None)
async def get_file(file_id: uuid.UUID, current_user=Depends(get_current_active_user)):
    file = await aiServ.get_file_by_id(file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found")
    return {
        "message": "success",
        "code": 200,
        "data": FileResponse(
            id=file.id,
            source_url=file.source_url,
            filename=file.filename,
            file_type=file.file_type,
            data=file.data,
        ),
    }


@router.get("/file_compression", summary="根据id获取文件并压缩", response_model=None)
async def get_file_compression(file_id: uuid.UUID, current_user=Depends(get_current_active_user)):
    file = await aiServ.get_file_by_id(file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found")
    compressed_data = await aiServ.compress_file_data(file.data)
    return {
        "message": "success",
        "code": 200,
        "data": FileResponse(
            id=file.id,
            source_url=file.source_url,
            filename=file.filename,
            file_type=file.file_type,
            data=compressed_data,
        ),
    }


@router.get("/file_download", summary="根据id获取文件blob下载")
async def get_file_download(file_id: uuid.UUID, current_user=Depends(get_current_active_user)):
    file = await aiServ.get_file_by_id(file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found")
    filename = file.filename or f"{file.id}"
    media_type = file.file_type or "application/octet-stream"
    quoted_filename = quote(filename)

    return Response(
        content=base64.b64decode(file.data),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quoted_filename}",
        },
    )