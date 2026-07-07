from fastapi import APIRouter
from app.services import knowledgeServ
from app.utils.auth import get_current_active_user
from fastapi import Depends
from fastapi import UploadFile, File

router = APIRouter(prefix="/knowledge/v1")


@router.post("/upload_file")
async def upload_file(file: list[UploadFile] = File(...), current_user=Depends(get_current_active_user)):
    uploaded_files = await knowledgeServ.upload_files(file, current_user.id)
    return {
        "message": "success",
        "code": 200,
        "data": uploaded_files,
    }


@router.post("/get_all")
async def get_all_knowledge(current_user=Depends(get_current_active_user)):
    knowledge_list = await knowledgeServ.get_all_knowledge(current_user.id)
    return {
        "message": "success",
        "code": 200,
        "data": knowledge_list,
    }
