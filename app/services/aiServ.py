from app.repositories import aiRepo
from app.models.ai import ChatBody
from app.models.tables.databaseTables import Chat_Session
from datetime import datetime
from app.utils.chatbot import Chatbot
import uuid


def _extract_cfg_items(payload):
    if isinstance(payload, dict):
        data = payload.get("data", [])
        return data if isinstance(data, list) else []
    if isinstance(payload, list):
        return payload
    return []


def _merge_user_cfg(kwargs_items, user_cfg_items):
    value_map = {}
    for cfg_item in user_cfg_items:
        if isinstance(cfg_item, dict) and "name" in cfg_item:
            value_map[cfg_item["name"]] = cfg_item.get("value")

    merged_items = []
    for kwargs_item in kwargs_items:
        if not isinstance(kwargs_item, dict):
            continue

        merged_item = dict(kwargs_item)
        item_name = merged_item.get("name")
        if item_name in value_map:
            merged_item["default"] = value_map[item_name]
        merged_items.append(merged_item)

    return merged_items


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


async def get_models_v2(user_id: uuid.UUID):
    models = aiRepo.select_models_v2()
    user_cfg_map = aiRepo.select_user_model_cfg_map(user_id, [model.id for model in models])

    model_list = []
    for model in models:
        kwargs_items = _extract_cfg_items(model.kwargs)
        user_cfg_items = _extract_cfg_items(user_cfg_map.get(model.id))
        merged_kwargs = _merge_user_cfg(kwargs_items, user_cfg_items)

        model_list.append(
            {
                "modelType": model.model_type,
                "model": model.model,
                "kwargs": merged_kwargs,
            }
        )

    return model_list
