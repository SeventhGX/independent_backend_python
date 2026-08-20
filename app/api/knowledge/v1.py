import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.models.knowledge import (
    AutoTagKnowledgeRequest,
    DeleteKnowledgeFilesRequest,
    KnowledgeFileIdsRequest,
    RagChatRequest,
    RagRetrieveRequest,
    SetKnowledgeTagsRequest,
)
from app.services import knowledgeServ
from app.utils.auth import get_current_active_user

router = APIRouter(prefix="/knowledge/v1")


@router.post("/upload_file")
async def upload_file(
    file: Annotated[list[UploadFile], File()],
    tag_names: Annotated[list[str] | None, Form()] = None,
    current_user=Depends(get_current_active_user),
):
    uploaded_files = await knowledgeServ.upload_files(
        file,
        current_user.id,
        current_user.user_name,
        tag_names,
    )
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


@router.get("/tags")
async def get_all_tags(current_user=Depends(get_current_active_user)):
    tags = await knowledgeServ.get_all_tags(current_user.id)
    return {
        "message": "success",
        "code": 200,
        "data": tags,
    }


@router.post("/set_tags")
async def set_file_tags(
    request: SetKnowledgeTagsRequest,
    current_user=Depends(get_current_active_user),
):
    tags = knowledgeServ.set_file_tags(request, current_user.id)
    return {
        "message": "success",
        "code": 200,
        "data": tags,
    }


@router.post("/auto_tag")
async def auto_tag_file(
    request: AutoTagKnowledgeRequest,
    current_user=Depends(get_current_active_user),
):
    tags = await knowledgeServ.auto_tag_file(request, current_user.id)
    return {
        "message": "success",
        "code": 200,
        "data": tags,
    }


@router.post("/delete_files")
async def delete_files(request: DeleteKnowledgeFilesRequest, current_user=Depends(get_current_active_user)):
    deleted_files = await knowledgeServ.delete_files(request.file_ids, current_user.id)
    return {
        "message": "success",
        "code": 200,
        "data": deleted_files,
    }


@router.post("/publish_files")
async def publish_files(
    request: KnowledgeFileIdsRequest,
    current_user=Depends(get_current_active_user),
):
    published_files = knowledgeServ.publish_files(request.file_ids, current_user.id)
    return {
        "message": "success",
        "code": 200,
        "data": published_files,
    }


@router.post("/unpublish_files")
async def unpublish_files(
    request: KnowledgeFileIdsRequest,
    current_user=Depends(get_current_active_user),
):
    unpublished_files = knowledgeServ.unpublish_files(request.file_ids, current_user.id)
    return {
        "message": "success",
        "code": 200,
        "data": unpublished_files,
    }


@router.post("/embedding_files")
async def embedding_files(fileids: list[uuid.UUID], current_user=Depends(get_current_active_user)):
    embedded_files = await knowledgeServ.embedding_files(fileids, current_user.id)
    return {
        "message": "success",
        "code": 200,
        "data": embedded_files,
    }


@router.post("/retrieve")
async def retrieve_chunks(request: RagRetrieveRequest, current_user=Depends(get_current_active_user)):
    chunks = await knowledgeServ.retrieve_chunks(request, current_user.id)
    return {
        "message": "success",
        "code": 200,
        "data": chunks,
    }


@router.post("/chat")
async def rag_chat(request: RagChatRequest, current_user=Depends(get_current_active_user)):
    answer = await knowledgeServ.rag_chat(request, current_user.id)
    return {
        "message": "success",
        "code": 200,
        "data": answer,
    }
