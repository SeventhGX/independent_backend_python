import asyncio
from app.repositories import articleRepo
from app.models.article import ArticleBody, ArticleQueryBody, ArticleDateRangeBody
from app.models.tables.databaseTables import Article
from datetime import date
import markdown
from app.utils.crawler import Crawler


async def get_all_articles():
    articles = articleRepo.select_all_articles()
    return {"data": articles}


async def get_articles_by_mail_body(mail_body: ArticleQueryBody):
    return articleRepo.select_article_by_args(**mail_body.model_dump())


async def get_articles_by_date_range(date_range: ArticleDateRangeBody):
    return articleRepo.select_article_by_range_args(**date_range.model_dump())


async def get_articles_by_mail_date(mail_date: date):
    articles = articleRepo.select_articles_by_mail_date(mail_date)
    return {"data": articles}


async def get_distinct_mail_dates():
    mail_dates = articleRepo.select_distinct_mail_dates()
    mail_date_str = [str(md) if md is not None else None for md in mail_dates]
    return {"data": mail_date_str}


async def trans_md_to_html(md_content: str):
    # 将 Markdown 转换为 HTML
    html_body = markdown.markdown(
        md_content,
        extensions=[
            "extra",  # 支持表格、脚注等扩展语法
            "codehilite",  # 代码高亮
            "nl2br",  # 换行符转换
            "sane_lists",  # 更好的列表处理
        ],
    )

    # 添加 CSS 样式使邮件更美观
    styled_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            h1, h2, h3, h4, h5, h6 {{
                margin-top: 24px;
                margin-bottom: 2px;
                font-weight: 600;
                line-height: 1.25;
            }}
            h1 {{ font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
            h2 {{ font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
            h3 {{ font-size: 1.25em; }}
            h4 {{ font-size: 1em; }}
            code {{
                background-color: #f6f8fa;
                padding: 0.2em 0.4em;
                border-radius: 3px;
                font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
                font-size: 85%;
            }}
            pre {{
                background-color: #f6f8fa;
                padding: 16px;
                overflow: auto;
                border-radius: 6px;
                line-height: 1.45;
            }}
            pre code {{
                background-color: transparent;
                padding: 0;
            }}
            blockquote {{
                padding: 0 1em;
                color: #6a737d;
                border-left: 0.25em solid #dfe2e5;
                margin: 0;
            }}
            a {{
                color: #0366d6;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            ul, ol {{
                padding-left: 2em;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 16px 0;
            }}
            table th, table td {{
                padding: 6px 13px;
                border: 1px solid #dfe2e5;
            }}
            table tr {{
                background-color: #fff;
                border-top: 1px solid #c6cbd1;
            }}
            table tr:nth-child(2n) {{
                background-color: #f6f8fa;
            }}
            strong {{
                font-weight: 600;
            }}
            hr {{
                height: 0.25em;
                padding: 0;
                margin: 24px 0;
                background-color: #e1e4e8;
                border: 0;
            }}
        </style>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """

    return {"data": styled_html}


async def add_article_by_url(url: str, crawler_type: str = "doubao", **kwargs):
    crawler = Crawler(crawler_type=crawler_type, **kwargs)
    article = await crawler.crawl_async(url)
    return articleRepo.insert_article(article)


async def add_article_by_body(article_body: ArticleBody):
    article = Article(
        title=article_body.title,
        url=article_body.url,
        publish_time=article_body.publish_time,
        key_words=article_body.key_words,
        summary=article_body.summary,
        content=article_body.content,
        mail_date=article_body.mail_date,
    )
    return articleRepo.insert_article(article)


if __name__ == "__main__":
    print(asyncio.run(get_distinct_mail_dates()))
