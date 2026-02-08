from fastapi import APIRouter
from app.services import recipientServ

from app.models.article import recipientBody
from app.models.tables.databaseTables import Recipient


router = APIRouter(prefix="/v1")


@router.post("/get_all")
async def get_all_recipients():
    result = await recipientServ.get_all_recipients()
    result["message"] = "success"  # type: ignore
    result["code"] = 200  # type: ignore
    return result


@router.post("/add")
async def add_recipient(recipient_body: recipientBody):
    recipient = Recipient(email=recipient_body.email, name=recipient_body.name)
    result = await recipientServ.add_recipient(recipient)
    result["message"] = "success"  # type: ignore
    result["code"] = 200  # type: ignore
    return result
