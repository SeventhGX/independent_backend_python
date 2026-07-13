from app.utils.config import settings
from app.utils.database import engine
from openai import OpenAI, AsyncOpenAI
from volcenginesdkarkruntime import Ark, AsyncArk
import httpx
import json
from app.models.tables.databaseTables import Chat_Model_V2
from sqlmodel import Session, select, col

# ---------------------------------------------------------------------------
# 大模型客户端注册表
# ---------------------------------------------------------------------------

bots = {}

with Session(engine) as session:
    # 从数据库读取启用中的模型配置，并按 SDK 类型创建对应的异步客户端。
    models2 = session.exec(select(Chat_Model_V2).where(Chat_Model_V2.del_flag == False)).all()  # noqa: E712
    # print(models2)
    for model in models2:
        # key_name 对应 settings 中的 API Key 字段名，缺失时跳过该模型。
        api_key = getattr(settings, model.key_name, None)
        if not isinstance(api_key, str) or not api_key:
            continue
        if model.sdk_type == "openai":
            bots[model.model] = AsyncOpenAI(base_url=model.base_url, api_key=api_key)
        elif model.sdk_type == "volcengine":
            bots[model.model] = AsyncArk(api_key=api_key)
