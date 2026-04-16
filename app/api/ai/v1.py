from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from datetime import date
from app.utils.chatbot import Chatbot
from app.utils.auth import get_current_active_user
from fastapi import Depends

router = APIRouter(prefix="/ai/v1")


@router.get("/sessions")
def get_user_sessions(current_user=Depends(get_current_active_user)):
    # 这里应该调用数据库查询用户的聊天会话记录，暂时返回一个示例数据
    return {
        "message": "success",
        "code": 200,
        "data": [
            {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "session_name": "示例会话",
                "create_time": "2024-01-01T12:00:00",
            }
        ],
    }


@router.get("/models")
def get_available_models(current_user=Depends(get_current_active_user)):
    # 这里应该调用数据库查询用户可用的模型，暂时返回一个示例数据
    return {
        "message": "success",
        "code": 200,
        "data": [
            {
                "modelType": "deepseek",
                "model": "deepseek-chat",
            }
        ],
    }
