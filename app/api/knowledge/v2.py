import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse

from app.models.knowledge_v2 import (
	AutoTagKnowledgeV2Request,
	CreateKnowledgeV2RequirementRequest,
	KnowledgeV2ChatRequest,
	KnowledgeV2FileIdsRequest,
	KnowledgeV2RequirementStatus,
	KnowledgeV2RetrieveRequest,
	QuestionFeedbackRequest,
	SetKnowledgeV2TagsRequest,
	SimilarQuestionRequest,
	UpdateKnowledgeV2RequirementStatusRequest,
)
from app.models.tables.databaseTables import DEFAULT_ADMIN_USER_CODE
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
	requirement_ids: Annotated[list[uuid.UUID] | None, Form()] = None,
):
	data = await knowledgeV2Serv.upload_file(
		file,
		current_user.id,
		current_user.user_name,
		database_names,
		knowledgeV2Serv.parse_metadata_json(metadata_json),
		tag_names or [],
		requirement_ids,
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
	requirement_ids: Annotated[list[uuid.UUID] | None, Form()] = None,
):
	data = await knowledgeV2Serv.reupload_file(
		knowledge_id,
		file,
		current_user.id,
		current_user.user_name,
		database_names,
		knowledgeV2Serv.parse_metadata_json(metadata_json),
		tag_names or [],
		requirement_ids,
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


@router.get("/files/mine", summary="分页查询本人上传的全部知识文件")
async def list_owned_files(
	current_user: UserDep,
	page: Annotated[int, Query(ge=1)] = 1,
	page_size: Annotated[int, Query(ge=1, le=100)] = 20,
	filename: Annotated[str | None, Query(max_length=255)] = None,
):
	data = knowledgeV2Serv.list_owned_files(
		current_user.id,
		current_user.user_name,
		filename,
		page,
		page_size,
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
async def rag_chat(request: KnowledgeV2ChatRequest, current_user: UserDep):
	data = await knowledgeV2Serv.rag_chat(request, current_user.id)
	return {"message": "success", "code": 200, "data": data}


@router.post("/chat_stream", summary="流式生成知识问答")
async def rag_chat_stream(request: KnowledgeV2ChatRequest, current_user: UserDep):
	return StreamingResponse(
		knowledgeV2Serv.rag_chat_stream(request, current_user.id),
		media_type="text/event-stream",
		headers={
			"Cache-Control": "no-cache",
			"X-Accel-Buffering": "no",
		},
	)


@router.post("/questions/similar", summary="检索相似典型问答")
async def search_similar_questions(request: SimilarQuestionRequest):
	data = await knowledgeV2Serv.search_similar_questions(request)
	return {"message": "success", "code": 200, "data": data}


@router.patch("/questions/{question_log_id}/feedback", summary="更新本人问答反馈")
async def update_question_feedback(
	question_log_id: uuid.UUID,
	request: QuestionFeedbackRequest,
	current_user: UserDep,
):
	data = knowledgeV2Serv.update_question_feedback(
		question_log_id,
		request.feedback,
		current_user.id,
	)
	return {"message": "success", "code": 200, "data": data}


@router.delete("/questions/{question_log_id}", summary="删除本人历史问答")
async def delete_question_log(question_log_id: uuid.UUID, current_user: UserDep):
	data = knowledgeV2Serv.delete_question_log(question_log_id, current_user.id)
	return {"message": "success", "code": 200, "data": data}


@router.post(
	"/requirements",
	summary="根据未解决问答创建知识库缺口请求",
	status_code=status.HTTP_201_CREATED,
)
async def create_knowledge_requirement(
	request: CreateKnowledgeV2RequirementRequest,
	current_user: UserDep,
):
	data = knowledgeV2Serv.create_knowledge_requirement(
		request,
		current_user.id,
		current_user.user_name,
	)
	return {"message": "success", "code": 201, "data": data}


@router.get("/requirements", summary="分页查询全部知识库缺口")
async def list_requirements(
	page: Annotated[int, Query(ge=1)] = 1,
	page_size: Annotated[int, Query(ge=1, le=100)] = 20,
	status_filter: Annotated[
		KnowledgeV2RequirementStatus | None,
		Query(alias="status"),
	] = None,
	keyword: Annotated[str | None, Query(max_length=2000)] = None,
):
	data = knowledgeV2Serv.list_requirements(
		status_filter,
		keyword,
		page,
		page_size,
	)
	return {"message": "success", "code": 200, "data": data}


@router.patch(
	"/requirements/{requirement_id}/status",
	summary="由缺口所有者或管理员更新缺口状态",
)
async def update_requirement_status(
	requirement_id: uuid.UUID,
	request: UpdateKnowledgeV2RequirementStatusRequest,
	current_user: UserDep,
):
	data = knowledgeV2Serv.update_requirement_status(
		requirement_id,
		request,
		current_user.id,
		current_user.user_code == DEFAULT_ADMIN_USER_CODE,
	)
	return {"message": "success", "code": 200, "data": data}


@router.get("/questions/history", summary="分页查询本人历史问答")
async def list_question_history(
	current_user: UserDep,
	page: Annotated[int, Query(ge=1)] = 1,
	page_size: Annotated[int, Query(ge=1, le=100)] = 20,
	question: Annotated[str | None, Query(max_length=2000)] = None,
):
	data = knowledgeV2Serv.list_question_history(
		current_user.id,
		question,
		page,
		page_size,
	)
	return {"message": "success", "code": 200, "data": data}


@router.get("/questions/typical-cases", summary="分页查询典型案例问答")
async def list_typical_cases(
	page: Annotated[int, Query(ge=1)] = 1,
	page_size: Annotated[int, Query(ge=1, le=100)] = 20,
	question: Annotated[str | None, Query(max_length=2000)] = None,
):
	data = knowledgeV2Serv.list_typical_cases(question, page, page_size)
	return {"message": "success", "code": 200, "data": data}
