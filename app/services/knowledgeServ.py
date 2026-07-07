import uuid

from fastapi import UploadFile

from app.models.tables.databaseTables import File, Knowledge
from app.models.knowledge import KnowledgeResponse
from app.repositories import knowledgeRepo


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
        )
        for knowledge, file in knowledge_files
    ]
