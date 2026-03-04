from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from datetime import date
from app.services import articleServ
from app.models.article import ArticleBody, MailDataBody
from app.utils.crawler import Crawler

router = APIRouter(prefix="/articles/v1")


@router.post("/get_all")
async def get_all_articles():
    result = await articleServ.get_all_articles()
    result["message"] = "success"  # type: ignore
    result["code"] = 200  # type: ignore
    return result


@router.post("/get_by_mail_date")
async def get_articles_by_mail_date(mail_date: date):
    result = await articleServ.get_articles_by_mail_date(mail_date)
    result["message"] = "success"  # type: ignore
    result["code"] = 200  # type: ignore
    return result


@router.post("/md_to_html")
async def md_to_html(mail_date_body: MailDataBody):
    result = await articleServ.trans_md_to_html(mail_date_body.body)
    result["message"] = "success"  # type: ignore
    result["code"] = 200  # type: ignore
    return result


@router.post("/add_by_url")
async def add_article_by_url(url: str, crawler_type: str = "doubao"):
    article = await articleServ.add_article_by_url(url, crawler_type)
    return {
        "message": "success",
        "code": 200,
        "data": article,
    }


@router.post("/url_stream")
async def url_stream(url: str, crawler_type: str = "doubao"):
    crawler = Crawler(crawler_type=crawler_type)
    return StreamingResponse(
        crawler.craw_stream_generator(url),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/add_by_body")
async def add_article_by_body(article_body: ArticleBody):
    article = await articleServ.add_article_by_body(article_body)
    return {
        "message": "success",
        "code": 200,
        "data": article,
    }
