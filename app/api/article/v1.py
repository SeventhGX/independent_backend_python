import uuid
from datetime import date

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.models.article import (
    ArticleBody,
    ArticleConclusionBody,
    ArticleDateRangeBody,
    ArticleQueryBody,
    MailDataBody,
    SearchBody,
    SearchPromptTemplateCreateBody,
)
from app.services import articleServ
from app.utils.auth import UserDep
from app.utils.crawler import Crawler

router = APIRouter(prefix="/articles/v1")


@router.post("/get_all")
async def get_all_articles(current_user: UserDep):
    result = await articleServ.get_all_articles()
    result["message"] = "success"  # type: ignore
    result["code"] = 200  # type: ignore
    return result


@router.post("/get_by_mail_body")
async def get_articles_by_mail_body(
    mail_body: ArticleQueryBody, current_user: UserDep
):
    return {
        "message": "success",
        "code": 200,
        "data": await articleServ.get_articles_by_mail_body(mail_body),
    }


@router.post("/get_by_date_range")
async def get_articles_by_date_range(
    date_range: ArticleDateRangeBody, current_user: UserDep
):
    return {
        "message": "success",
        "code": 200,
        "data": await articleServ.get_articles_by_date_range(date_range),
    }


@router.post("/get_by_mail_date")
async def get_articles_by_mail_date(mail_date: date, current_user: UserDep):
    result = await articleServ.get_articles_by_mail_date(mail_date)
    result["message"] = "success"  # type: ignore
    result["code"] = 200  # type: ignore
    return result


@router.post("/md_to_html")
async def md_to_html(mail_date_body: MailDataBody, current_user: UserDep):
    result = await articleServ.trans_md_to_html(mail_date_body.body)
    result["message"] = "success"  # type: ignore
    result["code"] = 200  # type: ignore
    return result


@router.post("/send_mail")
async def send_mail(mail_data_body: MailDataBody, current_user: UserDep):
    try:
        result = await articleServ.send_mail(mail_data_body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"邮件发送失败: {e}")
    result["message"] = "success"  # type: ignore
    result["code"] = 200  # type: ignore
    return result


@router.post("/add_by_url")
async def add_article_by_url(
    url: str, current_user: UserDep, crawler_type: str = "doubao"
):
    article = await articleServ.add_article_by_url(url, crawler_type)
    return {
        "message": "success",
        "code": 200,
        "data": article,
    }


@router.post("/url_stream")
async def url_stream(url: str, current_user: UserDep, crawler_type: str = "doubao"):
    crawler = Crawler(crawler_type=crawler_type)
    return StreamingResponse(
        crawler.craw_stream_generator(url),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat_stream")
async def chat_stream(
    body: ArticleConclusionBody, current_user: UserDep, crawler_type: str = "doubao"
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


@router.post("/search_stream")
async def search(
    body: SearchBody, current_user: UserDep, crawler_type: str = "doubao"
):
    crawler = Crawler(crawler_type=crawler_type, system_prompt=body.system_prompt)
    return StreamingResponse(
        crawler.search_stream_generator(body.content),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/search_prompt_template", summary="获取搜索提示词模版列表")
async def get_search_prompt_templates(current_user: UserDep, template_name: str | None = None):
    return {
        "message": "success",
        "code": 200,
        "data": await articleServ.get_search_prompt_templates(current_user.id, template_name),
    }


@router.post("/search_prompt_template", summary="新增搜索提示词模版", status_code=status.HTTP_201_CREATED)
async def create_search_prompt_template(body: SearchPromptTemplateCreateBody, current_user: UserDep):
    return {
        "message": "success",
        "code": 201,
        "data": await articleServ.create_search_prompt_template(body, current_user.id, current_user.user_name),
    }


@router.delete("/search_prompt_template", summary="删除搜索提示词模版")
async def delete_search_prompt_template(template_id: uuid.UUID, current_user: UserDep):
    try:
        deleted = await articleServ.delete_search_prompt_template(template_id, current_user.id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提示词模版不存在")
    return {"message": "success", "code": 200, "data": None}


@router.post("/add_by_body")
async def add_article_by_body(article_body: ArticleBody, current_user: UserDep):
    article = await articleServ.add_article_by_body(article_body)
    return {
        "message": "success",
        "code": 200,
        "data": article,
    }
