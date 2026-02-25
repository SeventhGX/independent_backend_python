from fastapi import APIRouter
from datetime import date
from app.services import articleServ
from app.models.article import MailDataBody

router = APIRouter(prefix="/v1")


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
