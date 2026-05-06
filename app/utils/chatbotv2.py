from app.utils.config import settings
from app.utils.database import engine
from openai import OpenAI, AsyncOpenAI
import httpx
import json
from app.models.tables.databaseTables import Chat_Model_V2
from sqlmodel import Session, select, col


def get_chat_model(model: str) -> Chat_Model_V2 | None:
    with Session(engine) as session:
        result = session.exec(
            select(Chat_Model_V2).where(
                Chat_Model_V2.model == model,
                Chat_Model_V2.del_flag == False,  # noqa: E712
            )
        ).first()
        if result is not None:
            return result
    return None


class ChatBotV2:
    def __init__(self):
        pass
