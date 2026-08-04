import re
import uuid
from collections import Counter

from fastapi import UploadFile
from openai import AsyncOpenAI

from app.models.knowledge import (
    DeleteKnowledgeFilesResponse,
    KnowledgeResponse,
    RagChatRequest,
    RagChatResponse,
    RagChunkResponse,
    RagRetrieveRequest,
    RetrievalMethod,
)
from app.models.tables.databaseTables import Chunks, File, Knowledge
from app.repositories import fileRepo, knowledgeRepo
from app.utils.config import settings
from app.utils.embedding import chunk_markdown, extract_markdown, qwen_embedding_text, qwen_embedding_texts

KNOWLEDGE_FILE_TYPE_PREFIX = "knowledge"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
HYBRID_CANDIDATE_MULTIPLIER = 4


def _build_knowledge_file_type(content_type: str | None):
    file_type = (content_type or "unknown").strip() or "unknown"
    if file_type.startswith(f"{KNOWLEDGE_FILE_TYPE_PREFIX}/"):
        return file_type
    return f"{KNOWLEDGE_FILE_TYPE_PREFIX}/{file_type}"


async def upload_files(files: list[UploadFile], user_id: uuid.UUID):
    uploaded_files = []
    for upload in files:
        file = File(
            filename=upload.filename,
            file_type=_build_knowledge_file_type(upload.content_type),
            data=await upload.read(),
        )
        knowledge = Knowledge(user_id=user_id, file_id=file.id)
        saved_file, saved_knowledge = knowledgeRepo.insert_knowledge_file(file, knowledge)
        uploaded_files.append(
            KnowledgeResponse(
                file_id=saved_file.id,
                knowledge_id=saved_knowledge.id,
                filename=saved_file.filename,
                file_type=saved_file.file_type.replace(f"{KNOWLEDGE_FILE_TYPE_PREFIX}/", "")
                if saved_file.file_type
                else None,
                is_embedded=saved_knowledge.is_embedded,
                create_time=saved_knowledge.create_time,
            )
        )
    return uploaded_files


async def get_all_knowledge(user_id: uuid.UUID):
    knowledge_files = knowledgeRepo.select_knowledge_by_user_id(user_id)
    return [
        KnowledgeResponse(
            file_id=file.id,
            knowledge_id=knowledge.id,
            filename=file.filename,
            file_type=file.file_type.replace(f"{KNOWLEDGE_FILE_TYPE_PREFIX}/", "")
            if file.file_type
            else None,
            is_embedded=knowledge.is_embedded,
            create_time=knowledge.create_time,
        )
        for knowledge, file in knowledge_files
    ]


async def delete_files(file_ids: list[uuid.UUID], user_id: uuid.UUID):
    deleted_file_ids = list(knowledgeRepo.delete_knowledge_files(file_ids, user_id))
    return DeleteKnowledgeFilesResponse(
        deleted_file_ids=deleted_file_ids,
        deleted_count=len(deleted_file_ids),
    )


def chunk_files(file_ids: list[uuid.UUID]):
    files = fileRepo.select_files_by_ids(file_ids)
    chunked_files = []
    for file in files:
        if not file or not file.data:
            continue
        # text_content = file.data.decode("utf-8", errors="ignore")
        extracted_text = extract_markdown(file.data, file.file_type, file.filename)
        chunks = chunk_markdown(
            extracted_text,
            metadata={
                "filename": file.filename,
                "file_type": file.file_type.replace(f"{KNOWLEDGE_FILE_TYPE_PREFIX}/", "")
                if file.file_type
                else None,
            },
            chunk_size=600,
            chunk_overlap=80,
        )
        chunked_files.append((file.id, chunks))
    return chunked_files


async def embedding_files(file_ids: list[uuid.UUID], user_id: uuid.UUID):
    knowledge_files = knowledgeRepo.select_knowledge_by_file_ids(file_ids, user_id)
    file_ids_to_embed = [knowledge.file_id for knowledge in knowledge_files if not knowledge.is_embedded]
    chunked_files = chunk_files(file_ids_to_embed)

    embedded_files = []
    for file_id, chunks in chunked_files:
        valid_chunks = [chunk for chunk in chunks if chunk.page_content.strip()]
        embeddings = (
            await qwen_embedding_texts([chunk.page_content for chunk in valid_chunks]) if valid_chunks else []
        )
        chunk_rows = [
            Chunks(
                file_id=file_id,
                chunk_index=chunk_index,
                meta_data=chunk.metadata,
                content=chunk.page_content,
                embedding=embedding,
            )
            for chunk_index, (chunk, embedding) in enumerate(zip(valid_chunks, embeddings))
        ]
        chunk_count = knowledgeRepo.replace_file_chunks(file_id, chunk_rows)
        embedded_files.append({"file_id": file_id, "chunk_count": chunk_count})

    return embedded_files


def _tokenize_for_keyword_search(text: str) -> list[str]:
    tokens = []
    for segment in re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", text.lower()):
        if "\u4e00" <= segment[0] <= "\u9fff" and len(segment) > 1:
            tokens.extend(segment[index : index + 2] for index in range(len(segment) - 1))
        else:
            tokens.append(segment)
    return tokens


def _keyword_score(query: str, content: str) -> float:
    query_tokens = Counter(_tokenize_for_keyword_search(query))
    if not query_tokens:
        return 0.0
    content_tokens = Counter(_tokenize_for_keyword_search(content))
    matched_tokens = sum(
        min(count, content_tokens[token]) for token, count in query_tokens.items()
    )
    return matched_tokens / sum(query_tokens.values())


def _rerank_hybrid(
    rows,
    query: str,
    top_k: int,
    semantic_weight: float,
    keyword_weight: float,
):
    if not rows:
        return []

    semantic_scores = [1 - float(distance) for _, distance in rows]
    reranked_rows = []
    for (chunk, _), semantic_score in zip(rows, semantic_scores):
        normalized_semantic_score = max(0.0, min(1.0, semantic_score))
        keyword_score = _keyword_score(query, chunk.content)
        combined_score = (
            semantic_weight * normalized_semantic_score
            + keyword_weight * keyword_score
        )
        reranked_rows.append(
            (chunk, semantic_score, keyword_score, combined_score)
        )

    return sorted(reranked_rows, key=lambda row: row[3], reverse=True)[:top_k]


async def retrieve_chunks(request: RagRetrieveRequest, user_id: uuid.UUID):
    query_embedding = await qwen_embedding_text(request.query)
    candidate_count = (
        request.top_k * HYBRID_CANDIDATE_MULTIPLIER
        if request.retrieval_method == RetrievalMethod.HYBRID
        else request.top_k
    )
    rows = knowledgeRepo.search_similar_chunks(
        query_embedding=query_embedding,
        user_id=user_id,
        file_ids=request.file_ids,
        top_k=candidate_count,
    )
    if request.retrieval_method == RetrievalMethod.HYBRID:
        reranked_rows = _rerank_hybrid(
            rows,
            request.query,
            request.top_k,
            request.semantic_weight,
            request.keyword_weight,
        )
    else:
        reranked_rows = [
            (chunk, 1 - float(distance), None, 1 - float(distance))
            for chunk, distance in rows
        ]
    return [
        RagChunkResponse(
            chunk_id=chunk.id,
            file_id=chunk.file_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            meta_data=chunk.meta_data,
            score=score,
            semantic_score=semantic_score,
            keyword_score=keyword_score,
            retrieval_method=request.retrieval_method,
        )
        for chunk, semantic_score, keyword_score, score in reranked_rows
    ]


def _build_rag_context(chunks: list[RagChunkResponse]) -> str:
    return "\n\n".join(
        f"[片段 {index}]\n文件: {chunk.meta_data.get('filename') if chunk.meta_data else chunk.file_id}\n内容:\n{chunk.content}"
        for index, chunk in enumerate(chunks, start=1)
    )


async def rag_chat(request: RagChatRequest, user_id: uuid.UUID):
    chunks = await retrieve_chunks(request, user_id)
    context = _build_rag_context(chunks)
    messages = [
        {
            "role": "system",
            "content": "你是一个严谨的知识库问答助手。请只依据给定的知识库片段回答；如果片段不足以回答，请明确说明无法从知识库中确定。",
        },
        {
            "role": "user",
            "content": f"知识库片段：\n{context or '无匹配片段'}\n\n用户问题：\n{request.query}",
        },
    ]
    async with AsyncOpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL) as client:
        completion = await client.chat.completions.create(
            # model=request.model,
            model="deepseek-v4-pro",
            messages=messages,  # type: ignore
            temperature=request.temperature,
        )
    answer = completion.choices[0].message.content or ""
    return RagChatResponse(answer=answer, chunks=chunks)
