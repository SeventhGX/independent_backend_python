import unicodedata
import uuid
from typing import Any, cast

from sqlalchemy import and_, delete, or_
from sqlmodel import Session, col, select

from app.models.knowledge import PUBLIC_KNOWLEDGE_SOURCE_PREFIX
from app.models.tables.databaseTables import (
    DEFAULT_ADMIN_USER_CODE,
    Chunks,
    File,
    Knowledge,
    KnowledgeTag,
    KnowledgeTagLink,
    Sys_User,
)
from app.utils.database import engine


def _default_admin_id_subquery():
    return (
        select(Sys_User.id)
        .where(Sys_User.user_code == DEFAULT_ADMIN_USER_CODE)
        .limit(1)
        .scalar_subquery()
    )


def insert_knowledge_file(file: File, knowledge: Knowledge):
    with Session(engine) as session:
        session.add(file)
        session.flush()

        knowledge.file_id = file.id
        session.add(knowledge)
        session.commit()
        session.refresh(file)
        session.refresh(knowledge)
        return file, knowledge


def select_knowledge_by_user_id(user_id: uuid.UUID):
    with Session(engine) as session:
        admin_user_id = _default_admin_id_subquery()
        statement = (
            select(Knowledge, File)
            .join(File, col(Knowledge.file_id) == File.id)
            .where(
                or_(
                    col(Knowledge.user_id) == user_id,
                    and_(
                        col(Knowledge.user_id) == admin_user_id,
                        col(Knowledge.is_embedded).is_(True),
                    ),
                )
            )
            .order_by(col(Knowledge.create_time).desc())
        )
        return session.exec(statement).all()


def select_user_names_by_ids(user_ids: list[uuid.UUID]):
    unique_user_ids = list(dict.fromkeys(user_ids))
    if not unique_user_ids:
        return {}

    with Session(engine) as session:
        statement = select(Sys_User.id, Sys_User.user_name).where(
            col(Sys_User.id).in_(unique_user_ids)
        )
        return dict(session.exec(statement).all())


def select_default_admin_user_id():
    with Session(engine) as session:
        return session.exec(
            select(Sys_User.id).where(Sys_User.user_code == DEFAULT_ADMIN_USER_CODE)
        ).first()


def select_knowledge_file(file_id: uuid.UUID, user_id: uuid.UUID):
    with Session(engine) as session:
        statement = (
            select(Knowledge, File)
            .join(File, col(Knowledge.file_id) == File.id)
            .where(Knowledge.file_id == file_id)
            .where(Knowledge.user_id == user_id)
        )
        return session.exec(statement).first()


def select_knowledge_tags_by_user_id(user_id: uuid.UUID):
    with Session(engine) as session:
        statement = (
            select(KnowledgeTag)
            .where(KnowledgeTag.user_id == user_id)
            .order_by(col(KnowledgeTag.normalized_name))
        )
        return session.exec(statement).all()


def select_tags_by_knowledge_ids(knowledge_ids: list[uuid.UUID]):
    if not knowledge_ids:
        return {}

    with Session(engine) as session:
        statement = (
            select(KnowledgeTagLink.knowledge_id, KnowledgeTag)
            .join(KnowledgeTag, col(KnowledgeTagLink.tag_id) == KnowledgeTag.id)
            .where(col(KnowledgeTagLink.knowledge_id).in_(knowledge_ids))
            .order_by(col(KnowledgeTag.normalized_name))
        )
        tag_map: dict[uuid.UUID, list[KnowledgeTag]] = {}
        for knowledge_id, tag in session.exec(statement).all():
            tag_map.setdefault(knowledge_id, []).append(tag)
        return tag_map


def _normalize_tag_name(name: str) -> str:
    return unicodedata.normalize("NFKC", name).strip().casefold()


def replace_knowledge_tags(
    file_id: uuid.UUID,
    user_id: uuid.UUID,
    tag_ids: list[uuid.UUID],
    new_tag_names: list[str],
):
    with Session(engine) as session:
        knowledge = session.exec(
            select(Knowledge)
            .where(Knowledge.file_id == file_id)
            .where(Knowledge.user_id == user_id)
        ).first()
        if knowledge is None:
            return None

        unique_tag_ids = list(dict.fromkeys(tag_ids))
        selected_tags = session.exec(
            select(KnowledgeTag)
            .where(KnowledgeTag.user_id == user_id)
            .where(col(KnowledgeTag.id).in_(unique_tag_ids))
        ).all() if unique_tag_ids else []
        if len(selected_tags) != len(unique_tag_ids):
            raise ValueError("包含不存在或不属于当前用户的标签")

        tags_by_name = {tag.normalized_name: tag for tag in selected_tags}
        for name in new_tag_names:
            normalized_name = _normalize_tag_name(name)
            if not normalized_name or normalized_name in tags_by_name:
                continue
            tag = session.exec(
                select(KnowledgeTag)
                .where(KnowledgeTag.user_id == user_id)
                .where(KnowledgeTag.normalized_name == normalized_name)
            ).first()
            if tag is None:
                tag = KnowledgeTag(
                    user_id=user_id,
                    name=unicodedata.normalize("NFKC", name).strip(),
                    normalized_name=normalized_name,
                )
                session.add(tag)
                session.flush()
            tags_by_name[normalized_name] = tag

        session.exec(
            delete(KnowledgeTagLink).where(col(KnowledgeTagLink.knowledge_id) == knowledge.id)
        )
        tags = sorted(tags_by_name.values(), key=lambda tag: tag.normalized_name)
        session.add_all(
            [KnowledgeTagLink(knowledge_id=knowledge.id, tag_id=tag.id) for tag in tags]
        )
        session.commit()
        for tag in tags:
            session.refresh(tag)
        return tags


def select_knowledge_by_file_ids(file_ids: list[uuid.UUID], user_id: uuid.UUID | None = None):
    if not file_ids:
        return []
    with Session(engine) as session:
        statement = select(Knowledge).where(col(Knowledge.file_id).in_(file_ids))
        if user_id is not None:
            statement = statement.where(Knowledge.user_id == user_id)
        statement = statement.order_by(col(Knowledge.create_time).desc())
        return session.exec(statement).all()


def replace_file_chunks(file_id: uuid.UUID, chunks: list[Chunks]):
    with Session(engine) as session:
        session.exec(delete(Chunks).where(col(Chunks.file_id) == file_id))
        session.add_all(chunks)
        knowledge = session.exec(select(Knowledge).where(col(Knowledge.file_id) == file_id)).first()
        if knowledge:
            knowledge.is_embedded = True
            session.add(knowledge)
        session.commit()
        return len(chunks)


def search_similar_chunks(
    query_embedding: list[float],
    user_id: uuid.UUID,
    file_ids: list[uuid.UUID] | None = None,
    top_k: int = 5,
):
    with Session(engine) as session:
        admin_user_id = _default_admin_id_subquery()
        distance = cast(Any, Chunks.embedding).cosine_distance(query_embedding).label("distance")
        statement = (
            select(Chunks, distance)
            .join(Knowledge, col(Chunks.file_id) == col(Knowledge.file_id))
            .where(
                or_(
                    col(Knowledge.user_id) == user_id,
                    and_(
                        col(Knowledge.user_id) == admin_user_id,
                        col(Knowledge.is_embedded).is_(True),
                    ),
                )
            )
            .where(col(Chunks.embedding).is_not(None))
            .order_by(distance)
            .limit(top_k)
        )
        if file_ids:
            statement = statement.where(col(Chunks.file_id).in_(file_ids))
        return session.exec(statement).all()


def publish_knowledge_files(file_ids: list[uuid.UUID], user_id: uuid.UUID):
    unique_file_ids = list(dict.fromkeys(file_ids))
    if not unique_file_ids:
        return []

    with Session(engine) as session:
        admin_user_id = session.exec(
            select(Sys_User.id).where(Sys_User.user_code == DEFAULT_ADMIN_USER_CODE)
        ).first()
        if admin_user_id is None:
            raise RuntimeError("系统管理员账号不存在")

        rows = session.exec(
            select(Knowledge, File)
            .join(File, col(Knowledge.file_id) == File.id)
            .where(Knowledge.user_id == user_id)
            .where(col(Knowledge.file_id).in_(unique_file_ids))
        ).all()
        if len(rows) != len(unique_file_ids):
            raise ValueError("包含不存在或不属于当前用户的知识文件")
        if any(not knowledge.is_embedded for knowledge, _ in rows):
            raise ValueError("只能公开已完成编码的知识文件")

        for knowledge, file in rows:
            knowledge.user_id = admin_user_id
            file.source_url = f"{PUBLIC_KNOWLEDGE_SOURCE_PREFIX}{user_id}"
            session.add(knowledge)
            session.add(file)
        session.commit()
        return unique_file_ids


def unpublish_knowledge_files(file_ids: list[uuid.UUID], user_id: uuid.UUID):
    unique_file_ids = list(dict.fromkeys(file_ids))
    if not unique_file_ids:
        return []

    with Session(engine) as session:
        admin_user_id = session.exec(
            select(Sys_User.id).where(Sys_User.user_code == DEFAULT_ADMIN_USER_CODE)
        ).first()
        if admin_user_id is None:
            raise RuntimeError("系统管理员账号不存在")

        source_marker = f"{PUBLIC_KNOWLEDGE_SOURCE_PREFIX}{user_id}"
        rows = session.exec(
            select(Knowledge, File)
            .join(File, col(Knowledge.file_id) == File.id)
            .where(Knowledge.user_id == admin_user_id)
            .where(File.source_url == source_marker)
            .where(col(Knowledge.file_id).in_(unique_file_ids))
        ).all()
        if len(rows) != len(unique_file_ids):
            raise ValueError("包含非当前用户公开的知识文件")

        for knowledge, file in rows:
            knowledge.user_id = user_id
            file.source_url = None
            session.add(knowledge)
            session.add(file)
        session.commit()
        return unique_file_ids


def delete_knowledge_files(file_ids: list[uuid.UUID], user_id: uuid.UUID):
    if not file_ids:
        return []

    with Session(engine) as session:
        owned_file_ids = session.exec(
            select(Knowledge.file_id)
            .where(Knowledge.user_id == user_id)
            .where(col(Knowledge.file_id).in_(file_ids))
        ).all()
        if not owned_file_ids:
            return []

        knowledge_ids = session.exec(
            select(Knowledge.id).where(col(Knowledge.file_id).in_(owned_file_ids))
        ).all()
        session.exec(delete(Chunks).where(col(Chunks.file_id).in_(owned_file_ids)))
        session.exec(
            delete(KnowledgeTagLink).where(col(KnowledgeTagLink.knowledge_id).in_(knowledge_ids))
        )
        session.exec(delete(Knowledge).where(col(Knowledge.file_id).in_(owned_file_ids)))
        session.exec(delete(File).where(col(File.id).in_(owned_file_ids)))
        session.commit()
        return owned_file_ids
