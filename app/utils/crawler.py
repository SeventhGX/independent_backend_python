# 根据url获取新闻网页内容
import asyncio

from volcenginesdkarkruntime import Ark, AsyncArk
from app.utils.config import settings
from app.models.tables.databaseTables import Article
import json


class DouBaoCrawler:
    def __init__(
        self, api_key: str = settings.DOUBAO_API_KEY, craw_bot_id: str = settings.DOUBAO_CRAWLER_BOT_ID
    ) -> None:
        self.bot = Ark(api_key=api_key)
        self.async_bot = AsyncArk(api_key=api_key)
        self.craw_bot_id = craw_bot_id

    def crawl(self, url: str) -> Article:
        completion = self.bot.bot_chat.completions.create(
            model=self.craw_bot_id,
            messages=[
                {
                    "role": "user",  # 指定消息的角色为用户
                    "content": [  # 消息内容列表
                        {
                            "type": "text",
                            "text": url,
                        },  # 文本消息
                    ],
                }
            ],
            max_tokens=40960,
        )
        json_data = json.loads(completion.choices[0].message.content)  # type: ignore
        article = Article(**json_data)
        return article

    async def crawl_async(self, url: str) -> Article:
        completion = await self.async_bot.bot_chat.completions.create(
            model=self.craw_bot_id,
            messages=[
                {
                    "role": "user",  # 指定消息的角色为用户
                    "content": [  # 消息内容列表
                        {
                            "type": "text",
                            "text": url,
                        },  # 文本消息
                    ],
                }
            ],
            max_tokens=40960,
        )
        json_data = json.loads(completion.choices[0].message.content)  # type: ignore
        article = Article(**json_data)
        return article

    async def craw_stream(self, url: str):
        # 发起流式请求
        stream = await self.async_bot.bot_chat.completions.create(  # type: ignore
            model=self.craw_bot_id,  # 替换为实际Bot ID
            messages=[{"role": "user", "content": url}],
            max_tokens=40960,
            stream=True,
            stream_options={"include_usage": True},
        )

        # full_content = ""
        # reasoning_content = ""  # 深度思考模型的思考过程内容

        # async for chunk in stream:
        #     if not chunk.choices:
        #         # 最后一个块返回usage统计，无choices
        #         if hasattr(chunk, "bot_usage"):
        #             print(f"\n\nToken用量：{chunk.bot_usage.model_usage}")
        #         continue

        #     delta = chunk.choices[0].delta
        #     # 普通回答内容
        #     if delta.content:
        #         full_content += delta.content
        #         print(delta.content, end="", flush=True)
        #     # 深度思考过程（仅深度思考模型返回）
        #     if delta.reasoning_content:
        #         reasoning_content += delta.reasoning_content
        #         # 可选择打印思考过程：
        #         print(f"思考中：{delta.reasoning_content}", end="", flush=True)

        # await client.close()
        return stream

    async def craw_stream_generator(self, url: str):
        """异步生成器，逐块 yield SSE 格式的内容，供 StreamingResponse 使用"""
        stream = await self.async_bot.bot_chat.completions.create(  # type: ignore
            model=self.craw_bot_id,
            messages=[{"role": "user", "content": url}],
            max_tokens=40960,
            stream=True,
            stream_options={"include_usage": True},
        )
        async for chunk in stream:  # type: ignore
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
            reasoning = getattr(delta, "reasoning_content", None)
            if content:
                # print(content, end="", flush=True)
                yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
            if reasoning:
                # print(reasoning, end="", flush=True)
                yield f"data: {json.dumps({'reasoning_content': reasoning}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    async def chat_stream_generator(self, messages: list[dict]):
        """流式对话生成器，逐块 yield SSE 格式的内容，供 StreamingResponse 使用"""
        stream = await self.async_bot.chat.completions.create(  # type: ignore
            model='doubao-seed-1-8-251228',
            messages=messages, # type: ignore
            max_tokens=32000,
            stream=True,
            stream_options={"include_usage": True},
        )
        async for chunk in stream:  # type: ignore
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


crawler_dict = {
    "doubao": DouBaoCrawler,
}


class Crawler:
    """
    爬虫类，根据参数生成不同爬虫模型的实例，并提供统一的接口进行爬取
    """

    def __init__(self, crawler_type: str, **kwargs) -> None:
        if crawler_type not in crawler_dict:
            raise ValueError(f"Unsupported crawler model: {crawler_type}")
        self.crawler = crawler_dict[crawler_type](**kwargs)

    def crawl(self, url: str) -> Article:
        return self.crawler.crawl(url)

    async def crawl_async(self, url: str) -> Article:
        return await self.crawler.crawl_async(url)

    async def craw_stream(self, url: str):
        return await self.crawler.craw_stream(url)

    async def craw_stream_generator(self, url: str):
        async for chunk in self.crawler.craw_stream_generator(url):
            yield chunk

    async def chat_stream_generator(self, messages: list[dict]):
        async for chunk in self.crawler.chat_stream_generator(messages):
            yield chunk


if __name__ == "__main__":
    crawler = Crawler(crawler_type="doubao")
    # article = crawler.crawl("https://www.gkzhan.com/news/detail/189178.html")
    # logger.info(article)
    # article = asyncio.run(crawler.crawl_async("https://www.gkzhan.com/news/detail/189178.html"))
    asyncio.run(crawler.craw_stream("https://www.gkzhan.com/news/detail/189178.html"))
