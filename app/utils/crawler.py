# 根据url获取新闻网页内容
import asyncio

from volcenginesdkarkruntime import Ark, AsyncArk
from app.utils.config import settings
from app.models.tables.databaseTables import Article
import json


class DouBaoCrawler:
    def __init__(
        self,
        api_key: str = settings.DOUBAO_API_KEY,
        craw_bot_id: str = settings.DOUBAO_CRAWLER_BOT_ID,
        **kwargs,
    ) -> None:
        self.bot = Ark(api_key=api_key)
        self.async_bot = AsyncArk(api_key=api_key)
        self.craw_bot_id = craw_bot_id
        self.kwargs = kwargs

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
            model="doubao-seed-1-8-251228",
            messages=messages,  # type: ignore
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

    async def search_stream_generator(self, content: str):
        """流式搜索生成器，逐块 yield SSE 格式的内容，供 StreamingResponse 使用"""
        if self.kwargs.get("system_prompt", "") != "":
            system_prompt = self.kwargs["system_prompt"]
        else:
            system_prompt = """
你是AI个人助手，你的主要职责是根据用户的需求进行搜索和信息筛选：
1. **信息准确性守护者**：确保提供的信息准确无误，严禁编造虚假信息。
2. **搜索成本优化师**：在信息准确性和搜索成本之间找到最佳平衡。
3. **用户需求分析师**：确保理解用户的真实需求，并保证提供的答案符合用户的需求。
# 任务说明
## 1. 搜索关键词提取
当接收到用户的查询请求时，首先分析并提取出搜索关键词。关键词应尽可能具体，以提高搜索结果的相关性。
## 2. 联网搜索
- 使用提取的关键词通过 `web_search` 进行联网搜索，获取相关资料。
- 搜索时注意关键词的分组和组合，通过合理的关键词组合进行多轮搜索，确保每轮搜索时使用的关键词具有较高相关性，以获取更全面的信息。
## 3. 搜索结果校验
- 对搜索结果进行校验，确保信息的准确性和相关性。
- 确保搜索结果能够满足用户的需求，尤其是时效性与数量，必要时进行补充搜索。
- 对于搜索结果中存在明显错误或不相关的信息或不满足用户需求的，也返回给用户，但进行标注，具体方式见后续的输出样例。
- 如果搜索结果与用户需求偏差过大，或者结果数量过少，或者结果时效性过差，则需要进行补充搜索，或者重新进行关键词的提取，直到满足用户需求或重试次数达到上限。
- 在搜索时，可以不必拘泥于提取出的关键词，而是可以根据已有的搜索结果进行扩充、调整和优化，只需要最终结果满足用户需求即可。
- 若重新搜索次数达到上限时，仍无法完全满足用户需求，则返回当前结果，严禁编造虚假信息。
## 4. 按指定格式进行输出
- 将最终的搜索结果按照json格式进行输出。
- 注意特殊字符的转义，确保输出的json格式正确，且不要包含除json格式外的内容。
- 输出的json格式如下：
{
    "data" : [
        {
            "title": "网页标题",
            "url": "网页链接",
            "positive": 1, // 该搜索结果是否满足用户需求，1表示满足，0表示不满足
        },
    ...
    ]
}
"""
        tools = [{"type": "web_search", "max_keyword": 7, "limit": 20}]
        stream = await self.async_bot.responses.create(
            model="doubao-seed-2-0-lite-260215",
            input=[{"role": "system", "content": system_prompt}, {"role": "user", "content": content}],
            tools=tools,  # type: ignore
            max_tool_calls=10,
            stream=True,
            max_output_tokens=40960,
        )
        async for chunk in stream:  # type: ignore
            if not chunk.type:
                continue
            if chunk.type == "response.output_text.delta":
                yield f"data: {json.dumps({'content': chunk.delta}, ensure_ascii=False)}\n\n"
            if chunk.type == "response.reasoning_summary_text.delta":
                yield f"data: {json.dumps({'reasoning_content': chunk.delta}, ensure_ascii=False)}\n\n"
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

    async def search_stream_generator(self, query: str):
        async for chunk in self.crawler.search_stream_generator(query):
            yield chunk


if __name__ == "__main__":
    crawler = Crawler(crawler_type="doubao")
    # article = crawler.crawl("https://www.gkzhan.com/news/detail/189178.html")
    # logger.info(article)
    # article = asyncio.run(crawler.crawl_async("https://www.gkzhan.com/news/detail/189178.html"))
    asyncio.run(crawler.craw_stream("https://www.gkzhan.com/news/detail/189178.html"))
