from app.utils.config import settings
from app.utils.database import engine
from openai import OpenAI, AsyncOpenAI
from volcenginesdkarkruntime import Ark, AsyncArk
import httpx
import json
from app.models.tables.databaseTables import Chat_Model_V2
from sqlmodel import Session, select, col

bots = {}

with Session(engine) as session:
    models2 = session.exec(select(Chat_Model_V2).where(Chat_Model_V2.del_flag == False)).all()  # noqa: E712
    # print(models2)
    for model in models2:
        api_key = getattr(settings, model.key_name, None)
        if not isinstance(api_key, str) or not api_key:
            continue
        if model.sdk_type == "openai":
            bots[model.model] = AsyncOpenAI(base_url=model.base_url, api_key=api_key)
        elif model.sdk_type == "volcengine":
            bots[model.model] = AsyncArk(api_key=api_key)
