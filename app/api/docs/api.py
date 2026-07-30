import mimetypes
import uuid
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.models.docs import (
    DocsCreateRequest,
    DocsImageCreateRequest,
    DocsImageUpdateRequest,
    DocsUpdateRequest,
)
from app.services import docsServ
from app.utils.auth import UserDep

router = APIRouter(prefix="/docs", tags=["docs"])


@router.get("/list", summary="获取文档列表")
async def get_docs_list(current_user: UserDep):
    return {"message": "success", "code": 200, "data": await docsServ.get_docs_list()}


@router.get("/docs", summary="获取文档")
async def get_docs(doc_id: uuid.UUID, current_user: UserDep):
    docs = await docsServ.get_docs(doc_id)
    if docs is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Docs not found")
    return {"message": "success", "code": 200, "data": docs}


@router.post("/docs", summary="新增文档", status_code=status.HTTP_201_CREATED)
async def create_docs(request: DocsCreateRequest, current_user: UserDep):
    docs = await docsServ.create_docs(request)
    return {"message": "success", "code": 201, "data": docs}


@router.patch("/docs", summary="更新文档")
async def update_docs(
    doc_id: uuid.UUID,
    request: DocsUpdateRequest,
    current_user: UserDep,
):
    docs = await docsServ.update_docs(doc_id, request)
    if docs is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Docs not found")
    return {"message": "success", "code": 200, "data": docs}


@router.delete("/docs", summary="删除文档")
async def delete_docs(doc_id: uuid.UUID, current_user: UserDep):
    if not await docsServ.delete_docs(doc_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Docs not found")
    return {"message": "success", "code": 200, "data": None}


@router.get("/images", summary="获取文档图片列表")
async def get_docs_image_list(
    current_user: UserDep,
    doc_id: uuid.UUID | None = None,
):
    images = await docsServ.get_image_list(doc_id)
    return {"message": "success", "code": 200, "data": images}


@router.get("/docs_image", summary="获取文档图片信息")
async def get_docs_image(image_id: uuid.UUID, current_user: UserDep):
    image = await _get_image_or_404(image_id)
    images = await docsServ.get_image_list(image.docs_id)
    image_info = next(item for item in images if item.id == image_id)
    return {"message": "success", "code": 200, "data": image_info}


@router.post("/docs_image", summary="新增文档图片", status_code=status.HTTP_201_CREATED)
async def create_docs_image(
    request: DocsImageCreateRequest,
    current_user: UserDep,
):
    try:
        image = await docsServ.create_image(request, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"message": "success", "code": 201, "data": {"id": image.id}}


@router.patch("/docs_image", summary="更新文档图片")
async def update_docs_image(
    image_id: uuid.UUID,
    request: DocsImageUpdateRequest,
    current_user: UserDep,
):
    try:
        image = await docsServ.update_image(image_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return {"message": "success", "code": 200, "data": {"id": image.id}}


@router.delete("/docs_image", summary="删除文档图片")
async def delete_docs_image(image_id: uuid.UUID, current_user: UserDep):
    if not await docsServ.delete_image(image_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return {"message": "success", "code": 200, "data": None}


@router.get("/docs_image/download", summary="下载文档完整图片")
async def download_docs_image(image_id: uuid.UUID, current_user: UserDep):
    image = await _get_image_or_404(image_id)
    media_type = mimetypes.guess_type(image.image_name)[0] or "application/octet-stream"
    quoted_filename = quote(image.image_name)
    return Response(
        content=image.image_data,
        media_type=media_type,
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quoted_filename}"},
    )


@router.get("/docs_image/thumbnail", summary="获取文档图片缩略图")
async def get_docs_image_thumbnail(
    image_id: uuid.UUID,
    current_user: UserDep,
    max_size: int = Query(default=320, ge=64, le=2048),
):
    image = await _get_image_or_404(image_id)
    try:
        thumbnail = await docsServ.create_thumbnail(image.image_data, max_size)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return Response(
        content=thumbnail,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=86400"},
    )


async def _get_image_or_404(image_id: uuid.UUID):
    image = await docsServ.get_image(image_id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return image
