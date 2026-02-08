from fastapi import APIRouter
from datetime import date
from app.services import articleServ
from app.models.article import MailDateBody

router = APIRouter(
    prefix="/v1"
)


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
async def md_to_html(mail_date_body: MailDateBody):
    result = await articleServ.trans_md_to_html(mail_date_body.body)
    result["message"] = "success"  # type: ignore
    result["code"] = 200  # type: ignore
    return result