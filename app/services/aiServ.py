from app.repositories import aiRepo
from app.models.ai import ChatBody
from app.models.tables.databaseTables import Chat_Session
from datetime import datetime
from app.utils.chatbot import Chatbot


async def get_user_sessions(user_id):
    return aiRepo.select_sessions_by_user_id(user_id)


async def get_session_content(session_id):
    sessions = aiRepo.select_sessions_by_session_id(session_id)
    if sessions:
        return sessions
    else:
        return None


async def generate_session_name(user_input: str) -> str:
    return await Chatbot().generate_session_name(user_input)


async def add_session(chat_body: ChatBody, user_id):
    session_name = await generate_session_name(
        "user:"
        + chat_body.content.get("messages", [{}])[0].get("content", "新会话")  # type: ignore
        + "\n assistant:"
        + chat_body.content.get("messages", [{}])[1].get("content", "")[:1000]  # type: ignore
    )
    session = Chat_Session(
        user_id=user_id,
        session_name=session_name,
        create_time=chat_body.create_time or datetime.now(),
        content=chat_body.content or {},
    )
    return aiRepo.insert_chat_session(session)


async def update_session(chat: Chat_Session):
    return aiRepo.update_chat_session_content(chat.id, chat.content)


async def get_models():
    return aiRepo.select_models()
