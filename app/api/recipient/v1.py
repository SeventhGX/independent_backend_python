from fastapi import APIRouter
from app.services import recipientServ

from app.models.article import RecipientBody
from app.models.tables.databaseTables import Recipient
from app.utils.log import logger

from app.utils.auth import get_current_active_user
from fastapi import Depends


router = APIRouter(prefix="/recipients/v1")


@router.post("/get_all")
async def get_all_recipients(current_user=Depends(get_current_active_user)):
    logger.info("[/recipients/v1/get_all]: 开始处理 ")
    result = await recipientServ.get_all_recipients()
    result["message"] = "success"  # type: ignore
    result["code"] = 200  # type: ignore
    return result


@router.post("/add")
async def add_recipient(recipient_body: RecipientBody, current_user=Depends(get_current_active_user)):
    recipient = Recipient(email=recipient_body.email, name=recipient_body.name)
    result = await recipientServ.add_recipient(recipient)
    result["message"] = "success"  # type: ignore
    result["code"] = 200  # type: ignore
    return result
