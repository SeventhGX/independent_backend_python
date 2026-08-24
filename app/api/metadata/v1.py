from fastapi import APIRouter

router = APIRouter(prefix="/metadata/v1")


@router.get("/all", summary="获取所有元数据")
async def get_all_metadata():
    pass
