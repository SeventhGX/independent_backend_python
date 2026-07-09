import uuid

from fastapi import UploadFile

from app.models.tables.databaseTables import Chunks, File, Knowledge
from app.models.knowledge import KnowledgeResponse
from app.repositories import knowledgeRepo, fileRepo
from app.utils.embedding import qwen_embedding_texts, extract_markdown, chunk_markdown


KNOWLEDGE_FILE_TYPE_PREFIX = "knowledge"


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
        embeddings = await qwen_embedding_texts([chunk.page_content for chunk in valid_chunks]) if valid_chunks else []
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
