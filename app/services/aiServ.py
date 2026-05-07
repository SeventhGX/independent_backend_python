from app.repositories import aiRepo
from app.models.ai import ChatBody, ChatBodyV2
from app.models.tables.databaseTables import Chat_Session, User_Model_Cfg
from datetime import datetime
from app.utils.chatbot import Chatbot
from app.utils.chatbotv2 import bots
import uuid
import json


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


async def chat_stream(model: str, messages: dict, **kwargs):
    model_data = aiRepo.select_model_v2_by_model(model)
    if model not in bots or model_data is None:
        raise ValueError(f"Model '{model}' not found in database.")
    bot = bots[model]
    if model_data.sdk_type == "openai" or model_data.sdk_type == "volcengine":
        response = await bot.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            **kwargs,
        )
        async for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
            reasoning = getattr(delta, "reasoning_content", None)
            if content:
                yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
            if reasoning:
                yield f"data: {json.dumps({'reasoning_content': reasoning}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"


async def update_user_model_cfg(user_id: uuid.UUID, chat_body: ChatBodyV2):
    modelv2 = aiRepo.select_model_v2_by_model(chat_body.model)
    if modelv2 is None:
        raise ValueError(f"Model '{chat_body.model}' not found in database.")
    if chat_body.kwargs is None or chat_body.kwargs == {}:
        return
    cfg_row = aiRepo.select_user_model_cfg(user_id, modelv2.id)

    cfg_payload = cfg_row.cfg if cfg_row else {}
    existing_items = _extract_cfg_items(cfg_payload)

    value_map = {}
    for item in existing_items:
        if isinstance(item, dict) and "name" in item:
            value_map[item["name"]] = item.get("value")

    for key, value in chat_body.kwargs.items():
        value_map[key] = value

    merged_cfg = {
        "data": [{"name": key, "value": value} for key, value in value_map.items()]
    }

    if cfg_row:
        return aiRepo.update_user_model_cfg_cfg(cfg_row.id, merged_cfg)

    new_cfg = aiRepo.insert_user_model_cfg(
        user_model_cfg=User_Model_Cfg(
            user_id=user_id,
            model_v2_id=modelv2.id,
            cfg=merged_cfg,
        )
    )
    return new_cfg
    
