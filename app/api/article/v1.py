from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from datetime import date
from app.services import articleServ
from app.models.article import (
    ArticleBody,
    MailDataBody,
    ArticleQueryBody,
    ArticleDateRangeBody,
    ArticleConclusionBody,
)
from app.utils.crawler import Crawler
from app.utils.auth import get_current_active_user
from fastapi import Depends

router = APIRouter(prefix="/articles/v1")


@router.post("/get_all")
async def get_all_articles(current_user=Depends(get_current_active_user)):
    result = await articleServ.get_all_articles()
    result["message"] = "success"  # type: ignore
    result["code"] = 200  # type: ignore
    return result


@router.post("/get_by_mail_body")
async def get_articles_by_mail_body(
    mail_body: ArticleQueryBody, current_user=Depends(get_current_active_user)
):
    return {
        "message": "success",
        "code": 200,
        "data": await articleServ.get_articles_by_mail_body(mail_body),
    }


@router.post("/get_by_date_range")
async def get_articles_by_date_range(
    date_range: ArticleDateRangeBody, current_user=Depends(get_current_active_user)
):
    return {
        "message": "success",
        "code": 200,
        "data": await articleServ.get_articles_by_date_range(date_range),
    }


@router.post("/get_by_mail_date")
async def get_articles_by_mail_date(mail_date: date, current_user=Depends(get_current_active_user)):
    result = await articleServ.get_articles_by_mail_date(mail_date)
    result["message"] = "success"  # type: ignore
    result["code"] = 200  # type: ignore
    return result


@router.post("/md_to_html")
async def md_to_html(mail_date_body: MailDataBody, current_user=Depends(get_current_active_user)):
    result = await articleServ.trans_md_to_html(mail_date_body.body)
    result["message"] = "success"  # type: ignore
    result["code"] = 200  # type: ignore
    return result


@router.post("/send_mail")
async def send_mail(mail_data_body: MailDataBody, current_user=Depends(get_current_active_user)):
    pass  # TODO: 实现邮件发送功能


@router.post("/add_by_url")
async def add_article_by_url(
    url: str, crawler_type: str = "doubao", current_user=Depends(get_current_active_user)
):
    article = await articleServ.add_article_by_url(url, crawler_type)
    return {
        "message": "success",
        "code": 200,
        "data": article,
    }


@router.post("/url_stream")
async def url_stream(url: str, crawler_type: str = "doubao", current_user=Depends(get_current_active_user)):
    crawler = Crawler(crawler_type=crawler_type)
    return StreamingResponse(
        crawler.craw_stream_generator(url),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat_stream")
async def chat_stream(
    body: ArticleConclusionBody, crawler_type: str = "doubao", current_user=Depends(get_current_active_user)
):
    crawler = Crawler(crawler_type=crawler_type)
    messages = [
        {"role": "system", "content": body.role_cfg},
        {"role": "user", "content": body.content},
    ]
    return StreamingResponse(
        crawler.chat_stream_generator(messages),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/add_by_body")
async def add_article_by_body(article_body: ArticleBody, current_user=Depends(get_current_active_user)):
    article = await articleServ.add_article_by_body(article_body)
    return {
        "message": "success",
        "code": 200,
        "data": article,
    }
