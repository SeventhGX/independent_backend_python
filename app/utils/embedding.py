from app.utils.config import settings
from openai import AsyncOpenAI


async def qwen_embedding_text(input_text: str):
    async with AsyncOpenAI(
        api_key=settings.QWEN_EMBEDDING_API_KEY,
        base_url="https://llm-ch7hgluabv286ib6.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
    ) as client:
        completion = await client.embeddings.create(
            model="text-embedding-v4", input=input_text, dimensions=1024
        )
        return completion.data[0].embedding
