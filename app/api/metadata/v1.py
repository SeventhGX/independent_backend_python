from fastapi import APIRouter

from app.repositories import metadataRepo

router = APIRouter(prefix="/metadata/v1")


@router.get("/all", summary="获取所有元数据")
async def get_all_metadata():
    return {
        "message": "success",
        "code": 200,
        "data": metadataRepo.select_all_metadata(),
    }
