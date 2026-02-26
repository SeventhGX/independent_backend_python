# 根据url获取新闻网页内容
from volcenginesdkarkruntime import Ark, AsyncArk
from app.utils.config import settings
from app.models.tables.databaseTables import Article
import json
from app.utils.log import logger


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
        )
        json_data = json.loads(completion.choices[0].message.content)  # type: ignore
        article = Article(**json_data)
        return article


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


if __name__ == "__main__":
    crawler = Crawler(crawler_type="doubao")
    article = crawler.crawl("https://www.gkzhan.com/news/detail/189178.html")
    logger.info(article)
