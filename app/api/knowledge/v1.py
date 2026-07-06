from fastapi import APIRouter
from app.models.knowledge import FileAddRequest
from app.utils.auth import get_current_active_user
from fastapi import Depends

router = APIRouter(prefix="/knowledge/v1")


@router.post("/add_file")
async def add_file(file_add_request: FileAddRequest, current_user=Depends(get_current_active_user)):
    pass
