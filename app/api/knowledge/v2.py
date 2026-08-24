import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status

from app.models.knowledge_v2 import (
	AutoTagKnowledgeV2Request,
	KnowledgeV2ChatRequest,
	KnowledgeV2FileIdsRequest,
	KnowledgeV2RetrieveRequest,
	SetKnowledgeV2TagsRequest,
)
from app.services import knowledgeV2Serv
from app.utils.auth import UserDep, get_current_active_user

router = APIRouter(
	prefix="/knowledge/v2",
	dependencies=[Depends(get_current_active_user)],
)


@router.post("/files", summary="上传公开知识文件", status_code=status.HTTP_201_CREATED)
async def upload_file(
	file: Annotated[UploadFile, File()],
	database_names: Annotated[list[str], Form()],
	current_user: UserDep,
	metadata_json: Annotated[str | None, Form()] = None,
	tag_names: Annotated[list[str] | None, Form()] = None,
):
	data = await knowledgeV2Serv.upload_file(
		file,
		current_user.id,
		current_user.user_name,
		database_names,
		knowledgeV2Serv.parse_metadata_json(metadata_json),
		tag_names or [],
	)
	return {"message": "success", "code": 201, "data": data}


@router.get("/files/{knowledge_id}/download", summary="下载公开知识文件")
async def download_file(knowledge_id: uuid.UUID):
	knowledge = knowledgeV2Serv.download_file(knowledge_id)
	return Response(
		content=knowledge.data,
		media_type=knowledge.file_type or "application/octet-stream",
		headers={
			"Content-Disposition": (
				f"attachment; filename*=UTF-8''{quote(knowledge.filename)}"
			)
		},
	)


@router.put("/files/{knowledge_id}/content", summary="重新上传本人知识文件")
async def reupload_file(
	knowledge_id: uuid.UUID,
	file: Annotated[UploadFile, File()],
	database_names: Annotated[list[str], Form()],
	current_user: UserDep,
	metadata_json: Annotated[str | None, Form()] = None,
	tag_names: Annotated[list[str] | None, Form()] = None,
):
	data = await knowledgeV2Serv.reupload_file(
		knowledge_id,
		file,
		current_user.id,
		current_user.user_name,
		database_names,
		knowledgeV2Serv.parse_metadata_json(metadata_json),
		tag_names or [],
	)
	return {"message": "success", "code": 200, "data": data}


@router.delete("/files/{knowledge_id}", summary="删除本人上传的知识文件")
async def delete_file(knowledge_id: uuid.UUID, current_user: UserDep):
	data = knowledgeV2Serv.delete_file(knowledge_id, current_user.id)
	return {"message": "success", "code": 200, "data": data}


@router.get("/tags", summary="获取全部公开标签")
async def get_all_tags():
	data = knowledgeV2Serv.get_all_tags()
	return {"message": "success", "code": 200, "data": data}


@router.get("/databases", summary="获取全部公开知识库")
async def get_all_databases():
	data = knowledgeV2Serv.get_all_databases()
	return {"message": "success", "code": 200, "data": data}


@router.post("/set_tags", summary="设置本人知识文件的公开标签")
async def set_file_tags(request: SetKnowledgeV2TagsRequest, current_user: UserDep):
	data = knowledgeV2Serv.set_file_tags(request, current_user.id)
	return {"message": "success", "code": 200, "data": data}


@router.post("/auto_tag", summary="自动标注本人知识文件")
async def auto_tag_file(
	request: AutoTagKnowledgeV2Request,
	current_user: UserDep,
):
	data = await knowledgeV2Serv.auto_tag_file(request, current_user.id)
	return {"message": "success", "code": 200, "data": data}


@router.post("/embedding_files", summary="手动重建本人知识文件向量")
async def embedding_files(
	request: KnowledgeV2FileIdsRequest,
	current_user: UserDep,
):
	data = await knowledgeV2Serv.embedding_files(
		request.knowledge_ids,
		current_user.id,
	)
	return {"message": "success", "code": 200, "data": data}


@router.get("/files", summary="按知识库分页查询公开文件")
async def list_files(
	database_name: Annotated[str, Query(min_length=1)],
	page: Annotated[int, Query(ge=1)] = 1,
	page_size: Annotated[int, Query(ge=1, le=100)] = 20,
	metadata: Annotated[str | None, Query()] = None,
	tag_names: Annotated[list[str] | None, Query()] = None,
):
	data = knowledgeV2Serv.list_files(
		database_name,
		knowledgeV2Serv.parse_metadata_json(metadata),
		tag_names or [],
		page,
		page_size,
	)
	return {"message": "success", "code": 200, "data": data}


@router.post("/retrieve", summary="按知识库与标签检索知识片段")
async def retrieve_chunks(request: KnowledgeV2RetrieveRequest):
	data = await knowledgeV2Serv.retrieve_chunks(request)
	return {"message": "success", "code": 200, "data": data}


@router.post("/chat", summary="按知识库与标签生成知识问答")
async def rag_chat(request: KnowledgeV2ChatRequest):
	data = await knowledgeV2Serv.rag_chat(request)
	return {"message": "success", "code": 200, "data": data}
