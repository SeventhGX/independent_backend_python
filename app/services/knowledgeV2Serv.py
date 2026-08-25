import hashlib
import json
import re
import unicodedata
import uuid
from collections import Counter
from math import ceil

from fastapi import HTTPException, UploadFile, status
from openai import AsyncOpenAI
from sqlalchemy.exc import IntegrityError

from app.models.knowledge import RetrievalMethod
from app.models.knowledge_v2 import (
    AutoTagKnowledgeV2Request,
    CreateKnowledgeV2RequirementRequest,
    DeleteKnowledgeV2Response,
    KnowledgeV2ChatRequest,
    KnowledgeV2ChatResponse,
    KnowledgeV2ChunkResponse,
    KnowledgeV2DatabaseDetailResponse,
    KnowledgeV2DatabaseResponse,
    KnowledgeV2FileResponse,
    KnowledgeV2PageResponse,
    KnowledgeV2RequirementPageResponse,
    KnowledgeV2RequirementResponse,
    KnowledgeV2RequirementStatus,
    KnowledgeV2RetrieveRequest,
    KnowledgeV2TagResponse,
    KnowledgeV2TagsResponse,
    QuestionFeedback,
    QuestionLogPageResponse,
    QuestionLogResponse,
    SetKnowledgeV2TagsRequest,
    SimilarQuestionRequest,
    SimilarQuestionResponse,
    UpdateKnowledgeV2RequirementStatusRequest,
)
from app.models.tables.databaseTables import (
    Database,
    KnowledgeChunkV2,
    KnowledgeTagV2,
    KnowledgeV2,
    KnowledgeV2Require,
    QuestionLog,
)
from app.repositories import knowledgeV2Repo
from app.services.knowledgeServ import _generate_tags_with_ai
from app.utils.config import settings
from app.utils.embedding import (
    chunk_markdown,
    extract_markdown,
    qwen_embedding_text,
    qwen_embedding_texts,
)

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
HYBRID_CANDIDATE_MULTIPLIER = 4
MAX_TAGS = 20


def parse_metadata_json(raw_metadata: str | None) -> dict[str, str]:
    if not raw_metadata:
        return {}
    try:
        value = json.loads(raw_metadata)
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="metadata_json 必须是有效的 JSON 对象",
        ) from error
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(item, str) for key, item in value.items()
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="metadata_json 必须是字符串键值组成的 JSON 对象",
        )
    return value


def _normalize_names(values: list[str], label: str, max_count: int | None = None):
    normalized_values: list[tuple[str, str]] = []
    seen_values = set()
    for value in values:
        name = unicodedata.normalize("NFKC", value).strip()
        if not name:
            raise HTTPException(status_code=422, detail=f"{label}不能为空")
        if len(name) > 50:
            raise HTTPException(status_code=422, detail=f"{label}不能超过 50 个字符")
        normalized_name = name.casefold()
        if normalized_name not in seen_values:
            seen_values.add(normalized_name)
            normalized_values.append((name, normalized_name))
    if max_count is not None and len(normalized_values) > max_count:
        raise HTTPException(status_code=422, detail=f"最多指定 {max_count} 个{label}")
    return normalized_values


def _normalize_optional_tags(values: list[str]):
    return _normalize_names(
        [value for value in values if value.strip()],
        "标签",
        MAX_TAGS,
    )


def _get_databases(database_names: list[str]) -> list[Database]:
    normalized_names = [name for name, _ in _normalize_names(database_names, "知识库名称")]
    if not normalized_names:
        raise HTTPException(status_code=422, detail="至少指定一个知识库")
    databases = knowledgeV2Repo.select_databases_by_names(normalized_names)
    found_names = {database.database_name for database in databases}
    missing_names = [name for name in normalized_names if name not in found_names]
    if missing_names:
        raise HTTPException(
            status_code=404,
            detail=f"知识库不存在: {', '.join(missing_names)}",
        )
    database_by_name = {database.database_name: database for database in databases}
    return [database_by_name[name] for name in normalized_names]


def _validate_metadata(metadata: dict[str, str], databases: list[Database]) -> None:
    supported_fields = {
        field_name
        for database in databases
        for field_name in database.meta_data_template
    }
    unsupported_fields = sorted(set(metadata) - supported_fields)
    if unsupported_fields:
        raise HTTPException(
            status_code=422,
            detail=f"知识库不支持以下元数据字段: {', '.join(unsupported_fields)}",
        )
    if not metadata:
        return

    options = knowledgeV2Repo.select_metadata_options(list(metadata))
    allowed_values: dict[str, set[str]] = {}
    for option in options:
        allowed_values.setdefault(option.field_name, set()).add(option.value)
    invalid_values = [
        f"{field_name}={value}"
        for field_name, value in metadata.items()
        if value not in allowed_values.get(field_name, set())
    ]
    if invalid_values:
        raise HTTPException(
            status_code=422,
            detail=f"元数据值不存在: {', '.join(invalid_values)}",
        )


def _calculate_md5(data: bytes) -> str:
    return hashlib.md5(data, usedforsecurity=False).hexdigest()


def _ensure_unique_md5(md5: str, exclude_id: uuid.UUID | None = None) -> None:
    duplicate = knowledgeV2Repo.select_file_by_md5(md5, exclude_id)
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"相同内容的知识文件已存在: {duplicate.filename}",
        )


def _validate_requirement_ids(
    requirement_ids: list[uuid.UUID] | None,
) -> list[uuid.UUID]:
    unique_ids = list(dict.fromkeys(requirement_ids or []))
    if not unique_ids:
        return []
    requirements = knowledgeV2Repo.select_open_requirements(unique_ids)
    if len(requirements) != len(unique_ids):
        raise HTTPException(
            status_code=404,
            detail="包含不存在或已关闭的知识库缺口请求",
        )
    return unique_ids


async def _build_chunks(
    knowledge_id: uuid.UUID,
    data: bytes,
    file_type: str,
    filename: str,
    metadata: dict[str, str],
) -> list[KnowledgeChunkV2]:
    try:
        content = extract_markdown(data, file_type, filename)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    documents = [
        document
        for document in chunk_markdown(
            content,
            metadata={"filename": filename, "file_type": file_type, **metadata},
            chunk_size=600,
            chunk_overlap=80,
        )
        if document.page_content.strip()
    ]
    embeddings = await qwen_embedding_texts(
        [document.page_content for document in documents]
    )
    return [
        KnowledgeChunkV2(
            knowledgev2_id=knowledge_id,
            chunk_index=chunk_index,
            meta_data=document.metadata,
            content=document.page_content,
            embedding=embedding,
        )
        for chunk_index, (document, embedding) in enumerate(
            zip(documents, embeddings, strict=True)
        )
    ]


def _file_response(
    knowledge: KnowledgeV2,
    uploader: str,
    databases: list[Database],
    tags: list[KnowledgeTagV2],
) -> KnowledgeV2FileResponse:
    return KnowledgeV2FileResponse(
        id=knowledge.id,
        filename=knowledge.filename,
        file_type=knowledge.file_type,
        md5=knowledge.md5,
        meta_data=knowledge.meta_data or {},
        is_embedded=knowledge.is_embedded,
        create_time=knowledge.create_time,
        uploader=uploader,
        databases=[
            KnowledgeV2DatabaseResponse(id=database.id, name=database.database_name)
            for database in databases
        ],
        tags=[KnowledgeV2TagResponse(id=tag.id, name=tag.name) for tag in tags],
    )


def _question_log_response(question_log: QuestionLog) -> QuestionLogResponse:
    return QuestionLogResponse(
        id=question_log.id,
        question=question_log.question,
        answer=question_log.answer,
        related_chunkv2_ids=[
            uuid.UUID(chunk_id) for chunk_id in question_log.related_chunkv2_ids or []
        ],
        user_feedback=(
            QuestionFeedback(question_log.user_feedback)
            if question_log.user_feedback
            else None
        ),
        create_time=question_log.create_time,
    )


def _requirement_response(
    knowledge_requirement: KnowledgeV2Require,
    owner_name: str,
    question: str | None,
) -> KnowledgeV2RequirementResponse:
    return KnowledgeV2RequirementResponse(
        id=knowledge_requirement.id,
        owner_user_id=knowledge_requirement.user_id,
        owner_name=owner_name,
        requirement=knowledge_requirement.requirement,
        related_log_id=knowledge_requirement.related_log_id,
        question=question,
        status=(
            KnowledgeV2RequirementStatus.CLOSED
            if knowledge_requirement.is_resolved
            else KnowledgeV2RequirementStatus.OPEN
        ),
        is_resolved=knowledge_requirement.is_resolved,
        related_knowledgev2_ids=[
            uuid.UUID(knowledge_id)
            for knowledge_id in knowledge_requirement.related_knowledgev2_ids or []
        ],
        create_time=knowledge_requirement.create_time,
    )


def get_all_tags():
    return [
        KnowledgeV2TagResponse(id=tag.id, name=tag.name)
        for tag in knowledgeV2Repo.select_all_tags()
    ]


def get_all_databases():
    return [
        KnowledgeV2DatabaseDetailResponse(
            id=database.id,
            database_name=database.database_name,
            database_desc=database.database_desc,
            meta_data_template=database.meta_data_template,
        )
        for database in knowledgeV2Repo.select_all_databases()
    ]


def set_file_tags(request: SetKnowledgeV2TagsRequest, user_id: uuid.UUID):
    normalized_tags = _normalize_names(request.new_tags, "标签", MAX_TAGS)
    try:
        tags = knowledgeV2Repo.replace_file_tags(
            request.knowledge_id,
            user_id,
            request.tag_ids,
            normalized_tags,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if tags is None:
        raise HTTPException(status_code=404, detail="知识文件不存在或不属于当前用户")
    return KnowledgeV2TagsResponse(
        knowledge_id=request.knowledge_id,
        tags=[KnowledgeV2TagResponse(id=tag.id, name=tag.name) for tag in tags],
    )


async def auto_tag_file(request: AutoTagKnowledgeV2Request, user_id: uuid.UUID):
    knowledge = knowledgeV2Repo.select_owned_file(request.knowledge_id, user_id)
    if knowledge is None:
        raise HTTPException(status_code=404, detail="知识文件不存在或不属于当前用户")
    try:
        content = extract_markdown(
            knowledge.data,
            knowledge.file_type,
            knowledge.filename,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    public_tags = knowledgeV2Repo.select_all_tags()
    assigned_tags = knowledgeV2Repo.select_tag_map([knowledge.id]).get(knowledge.id, [])
    generated_names = await _generate_tags_with_ai(
        content,
        [tag.name for tag in public_tags],
        request.max_tags,
    )
    if not request.allow_new_tags:
        public_tag_names = {tag.normalized_name for tag in public_tags}
        generated_names = [
            name
            for name in generated_names
            if unicodedata.normalize("NFKC", name).strip().casefold()
            in public_tag_names
        ]

    tags = knowledgeV2Repo.replace_file_tags(
        knowledge.id,
        user_id,
        [tag.id for tag in assigned_tags],
        _normalize_names(generated_names, "标签", MAX_TAGS),
    )
    if tags is None:
        raise HTTPException(status_code=404, detail="知识文件不存在或不属于当前用户")
    return KnowledgeV2TagsResponse(
        knowledge_id=knowledge.id,
        tags=[KnowledgeV2TagResponse(id=tag.id, name=tag.name) for tag in tags],
    )


async def upload_file(
    upload: UploadFile,
    user_id: uuid.UUID,
    user_name: str,
    database_names: list[str],
    metadata: dict[str, str],
    tag_names: list[str],
    requirement_ids: list[uuid.UUID] | None = None,
):
    filename = (upload.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=422, detail="文件名不能为空")
    databases = _get_databases(database_names)
    _validate_metadata(metadata, databases)
    normalized_tags = _normalize_optional_tags(tag_names)
    validated_requirement_ids = _validate_requirement_ids(requirement_ids)
    data = await upload.read()
    if not data:
        raise HTTPException(status_code=422, detail="上传文件不能为空")
    md5 = _calculate_md5(data)
    _ensure_unique_md5(md5)

    knowledge = KnowledgeV2(
        user_id=user_id,
        filename=filename,
        file_type=(upload.content_type or "application/octet-stream").strip(),
        md5=md5,
        meta_data=metadata,
        data=data,
        is_embedded=True,
    )
    chunks = await _build_chunks(
        knowledge.id,
        data,
        knowledge.file_type,
        filename,
        metadata,
    )
    try:
        saved_knowledge, tags = knowledgeV2Repo.create_file(
            knowledge,
            [database.id for database in databases],
            normalized_tags,
            chunks,
            validated_requirement_ids,
        )
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail="相同内容的知识文件已存在") from error
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return _file_response(saved_knowledge, user_name, databases, tags)


def download_file(knowledge_id: uuid.UUID):
    knowledge = knowledgeV2Repo.select_active_file(knowledge_id)
    if knowledge is None:
        raise HTTPException(status_code=404, detail="知识文件不存在")
    return knowledge


async def reupload_file(
    knowledge_id: uuid.UUID,
    upload: UploadFile,
    user_id: uuid.UUID,
    user_name: str,
    database_names: list[str],
    metadata: dict[str, str],
    tag_names: list[str],
    requirement_ids: list[uuid.UUID] | None = None,
):
    existing = knowledgeV2Repo.select_owned_file(knowledge_id, user_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="知识文件不存在或不属于当前用户")
    data = await upload.read()
    if not data:
        raise HTTPException(status_code=422, detail="上传文件不能为空")
    databases = _get_databases(database_names)
    _validate_metadata(metadata, databases)
    normalized_tags = _normalize_optional_tags(tag_names)
    validated_requirement_ids = _validate_requirement_ids(requirement_ids)
    md5 = _calculate_md5(data)
    _ensure_unique_md5(md5, knowledge_id)
    file_type = (upload.content_type or existing.file_type).strip()
    chunks = await _build_chunks(
        knowledge_id,
        data,
        file_type,
        existing.filename,
        metadata,
    )
    try:
        result = knowledgeV2Repo.replace_file_content(
            knowledge_id,
            user_id,
            data,
            file_type,
            md5,
            metadata,
            [database.id for database in databases],
            normalized_tags,
            chunks,
            validated_requirement_ids,
        )
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail="相同内容的知识文件已存在") from error
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="知识文件不存在或不属于当前用户")
    knowledge, tags = result
    return _file_response(
        knowledge,
        user_name,
        databases,
        tags,
    )


async def embedding_files(knowledge_ids: list[uuid.UUID], user_id: uuid.UUID):
    knowledge_files = knowledgeV2Repo.select_owned_files(knowledge_ids, user_id)
    embedded_files = []
    for knowledge in knowledge_files:
        chunks = await _build_chunks(
            knowledge.id,
            knowledge.data,
            knowledge.file_type,
            knowledge.filename,
            knowledge.meta_data or {},
        )
        chunk_count = knowledgeV2Repo.replace_file_chunks(
            knowledge.id,
            user_id,
            chunks,
        )
        if chunk_count is not None:
            embedded_files.append(
                {"knowledge_id": knowledge.id, "chunk_count": chunk_count}
            )
    return embedded_files


def delete_file(knowledge_id: uuid.UUID, user_id: uuid.UUID):
    if not knowledgeV2Repo.delete_owned_file(knowledge_id, user_id):
        raise HTTPException(status_code=404, detail="知识文件不存在或不属于当前用户")
    return DeleteKnowledgeV2Response(id=knowledge_id, deleted=True)


def list_files(
    database_name: str,
    metadata_filters: dict[str, str],
    tag_names: list[str],
    page: int,
    page_size: int,
):
    databases = _get_databases([database_name])
    _validate_metadata(metadata_filters, databases)
    normalized_tags = [
        normalized_name
        for _, normalized_name in _normalize_names(tag_names, "标签", MAX_TAGS)
    ]
    rows, total = knowledgeV2Repo.select_files(
        databases[0].database_name,
        metadata_filters,
        normalized_tags,
        page,
        page_size,
    )
    knowledge_ids = [knowledge.id for knowledge, _ in rows]
    database_map = knowledgeV2Repo.select_database_map(knowledge_ids)
    tag_map = knowledgeV2Repo.select_tag_map(knowledge_ids)
    items = [
        _file_response(
            knowledge,
            user.user_name,
            database_map.get(knowledge.id, []),
            tag_map.get(knowledge.id, []),
        )
        for knowledge, user in rows
    ]
    return KnowledgeV2PageResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        pages=ceil(total / page_size) if total else 0,
    )


def _tokenize(text: str) -> list[str]:
    tokens = []
    for segment in re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", text.lower()):
        if "\u4e00" <= segment[0] <= "\u9fff" and len(segment) > 1:
            tokens.extend(segment[index : index + 2] for index in range(len(segment) - 1))
        else:
            tokens.append(segment)
    return tokens


def _keyword_score(query: str, content: str) -> float:
    query_tokens = Counter(_tokenize(query))
    if not query_tokens:
        return 0.0
    content_tokens = Counter(_tokenize(content))
    matched = sum(
        min(count, content_tokens[token]) for token, count in query_tokens.items()
    )
    return matched / sum(query_tokens.values())


async def retrieve_chunks(request: KnowledgeV2RetrieveRequest):
    database = _get_databases([request.database_name])[0]
    normalized_tags = [
        normalized_name
        for _, normalized_name in _normalize_names(request.tag_names, "标签", MAX_TAGS)
    ]
    query_embedding = await qwen_embedding_text(request.query)
    candidate_count = (
        request.top_k * HYBRID_CANDIDATE_MULTIPLIER
        if request.retrieval_method == RetrievalMethod.HYBRID
        else request.top_k
    )
    rows = knowledgeV2Repo.search_similar_chunks(
        query_embedding,
        database.database_name,
        normalized_tags,
        candidate_count,
    )
    ranked_rows = []
    for chunk, filename, distance in rows:
        semantic_score = 1 - float(distance)
        keyword_score = (
            _keyword_score(request.query, chunk.content)
            if request.retrieval_method == RetrievalMethod.HYBRID
            else None
        )
        score = (
            request.semantic_weight * max(0.0, min(1.0, semantic_score))
            + request.keyword_weight * (keyword_score or 0.0)
            if keyword_score is not None
            else semantic_score
        )
        ranked_rows.append((chunk, filename, semantic_score, keyword_score, score))
    if request.retrieval_method == RetrievalMethod.HYBRID:
        ranked_rows.sort(key=lambda row: row[4], reverse=True)

    return [
        KnowledgeV2ChunkResponse(
            chunk_id=chunk.id,
            knowledge_id=chunk.knowledgev2_id,
            filename=filename,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            meta_data=chunk.meta_data,
            score=score,
            semantic_score=semantic_score,
            keyword_score=keyword_score,
            retrieval_method=request.retrieval_method,
        )
        for chunk, filename, semantic_score, keyword_score, score in ranked_rows[
            : request.top_k
        ]
    ]


async def rag_chat(request: KnowledgeV2ChatRequest, user_id: uuid.UUID):
    chunks = await retrieve_chunks(request)
    context = "\n\n".join(
        f"[片段 {index}]\n文件: {chunk.filename}\n内容:\n{chunk.content}"
        for index, chunk in enumerate(chunks, start=1)
    )
    messages = [
        {
            "role": "system",
            "content": "你是一个严谨的公开知识库问答助手。只依据给定片段回答；片段不足时请明确说明无法从知识库中确定。",
        },
        {
            "role": "user",
            "content": f"知识库片段：\n{context or '无匹配片段'}\n\n用户问题：\n{request.query}",
        },
    ]
    async with AsyncOpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    ) as client:
        completion = await client.chat.completions.create(
            model="deepseek-v4-pro",
            messages=messages,  # type: ignore
            temperature=request.temperature,
        )
    answer = completion.choices[0].message.content or ""
    question_log = QuestionLog(
        user_id=user_id,
        question=request.query,
        answer=answer,
        related_chunkv2_ids=[str(chunk.chunk_id) for chunk in chunks],
        embedding=await qwen_embedding_text(
            f"问题：{request.query}\n回答：{answer}"
        ),
    )
    saved_log = knowledgeV2Repo.create_question_log(question_log)
    return KnowledgeV2ChatResponse(
        question_log_id=saved_log.id,
        answer=answer,
        chunks=chunks,
    )


def update_question_feedback(
    question_log_id: uuid.UUID,
    feedback: QuestionFeedback,
    user_id: uuid.UUID,
):
    question_log = knowledgeV2Repo.update_question_feedback(
        question_log_id,
        user_id,
        feedback.value,
    )
    if question_log is None:
        raise HTTPException(status_code=404, detail="问答记录不存在或不属于当前用户")
    return _question_log_response(question_log)


def create_knowledge_requirement(
    request: CreateKnowledgeV2RequirementRequest,
    user_id: uuid.UUID,
    user_name: str,
):
    try:
        result = knowledgeV2Repo.create_requirement(
            user_id,
            request.related_log_id,
            request.requirement,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="问答记录不存在或不属于当前用户")
    knowledge_requirement, question = result
    return _requirement_response(knowledge_requirement, user_name, question)


def list_requirements(
    status_filter: KnowledgeV2RequirementStatus | None,
    keyword: str | None,
    page: int,
    page_size: int,
):
    normalized_keyword = keyword.strip() if keyword else None
    is_resolved = (
        status_filter == KnowledgeV2RequirementStatus.CLOSED
        if status_filter is not None
        else None
    )
    rows, total = knowledgeV2Repo.select_requirements(
        is_resolved,
        normalized_keyword or None,
        page,
        page_size,
    )
    return KnowledgeV2RequirementPageResponse(
        items=[
            _requirement_response(requirement, owner.user_name, question)
            for requirement, owner, question in rows
        ],
        page=page,
        page_size=page_size,
        total=total,
        pages=ceil(total / page_size) if total else 0,
    )


def update_requirement_status(
    requirement_id: uuid.UUID,
    request: UpdateKnowledgeV2RequirementStatusRequest,
    user_id: uuid.UUID,
    is_admin: bool,
):
    try:
        result = knowledgeV2Repo.update_requirement_status(
            requirement_id,
            user_id,
            is_admin,
            request.status == KnowledgeV2RequirementStatus.CLOSED,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="知识库缺口请求不存在")
    requirement, owner, question = result
    return _requirement_response(requirement, owner.user_name, question)


def list_owned_files(
    user_id: uuid.UUID,
    user_name: str,
    filename: str | None,
    page: int,
    page_size: int,
):
    normalized_filename = filename.strip() if filename else None
    files, total = knowledgeV2Repo.select_owned_file_page(
        user_id,
        normalized_filename or None,
        page,
        page_size,
    )
    file_ids = [knowledge.id for knowledge in files]
    database_map = knowledgeV2Repo.select_database_map(file_ids)
    tag_map = knowledgeV2Repo.select_tag_map(file_ids)
    return KnowledgeV2PageResponse(
        items=[
            _file_response(
                knowledge,
                user_name,
                database_map.get(knowledge.id, []),
                tag_map.get(knowledge.id, []),
            )
            for knowledge in files
        ],
        page=page,
        page_size=page_size,
        total=total,
        pages=ceil(total / page_size) if total else 0,
    )


def _list_question_logs(
    user_id: uuid.UUID | None,
    feedback: QuestionFeedback | None,
    keyword: str | None,
    page: int,
    page_size: int,
):
    normalized_keyword = keyword.strip() if keyword else None
    rows, total = knowledgeV2Repo.select_question_logs(
        user_id,
        feedback.value if feedback else None,
        normalized_keyword or None,
        page,
        page_size,
    )
    return QuestionLogPageResponse(
        items=[_question_log_response(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
        pages=ceil(total / page_size) if total else 0,
    )


def list_question_history(
    user_id: uuid.UUID,
    keyword: str | None,
    page: int,
    page_size: int,
):
    return _list_question_logs(user_id, None, keyword, page, page_size)


def list_typical_cases(keyword: str | None, page: int, page_size: int):
    return _list_question_logs(
        None,
        QuestionFeedback.COLLECT,
        keyword,
        page,
        page_size,
    )


async def search_similar_questions(request: SimilarQuestionRequest):
    query_embedding = await qwen_embedding_text(request.query)
    rows = knowledgeV2Repo.search_similar_questions(
        query_embedding,
        request.top_k,
    )
    return [
        SimilarQuestionResponse(
            **_question_log_response(question_log).model_dump(),
            score=1 - float(distance),
        )
        for question_log, distance in rows
    ]