import uuid
from typing import Any, cast

from sqlalchemy import delete, distinct, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, col, select

from app.models.tables.databaseTables import (
    Database,
    KnowledgeChunkV2,
    KnowledgeDatabaseLink,
    KnowledgeTagLinkV2,
    KnowledgeTagV2,
    KnowledgeV2,
    Metadata,
    Sys_User,
)
from app.utils.database import engine


def _get_or_create_tags(
    session: Session,
    tag_names: list[tuple[str, str]],
) -> list[KnowledgeTagV2]:
    tags = []
    for name, normalized_name in tag_names:
        session.exec(
            pg_insert(KnowledgeTagV2)
            .values(
                id=uuid.uuid4(),
                name=name,
                normalized_name=normalized_name,
            )
            .on_conflict_do_nothing(index_elements=["normalized_name"])
        )
        tag = session.exec(
            select(KnowledgeTagV2).where(
                col(KnowledgeTagV2.normalized_name) == normalized_name
            )
        ).first()
        if tag is None:
            raise RuntimeError("创建公开标签失败")
        tags.append(tag)
    return tags


def select_databases_by_names(database_names: list[str]):
    unique_names = list(dict.fromkeys(database_names))
    with Session(engine) as session:
        return session.exec(
            select(Database).where(col(Database.database_name).in_(unique_names))
        ).all()


def select_all_databases():
    with Session(engine) as session:
        return session.exec(
            select(Database).order_by(col(Database.database_name))
        ).all()


def select_metadata_options(field_names: list[str]):
    if not field_names:
        return []
    with Session(engine) as session:
        return session.exec(
            select(Metadata).where(col(Metadata.field_name).in_(field_names))
        ).all()


def select_file_by_md5(md5: str, exclude_id: uuid.UUID | None = None):
    with Session(engine) as session:
        statement = select(KnowledgeV2).where(col(KnowledgeV2.md5) == md5)
        if exclude_id is not None:
            statement = statement.where(col(KnowledgeV2.id) != exclude_id)
        return session.exec(statement).first()


def select_all_tags():
    with Session(engine) as session:
        return session.exec(
            select(KnowledgeTagV2).order_by(col(KnowledgeTagV2.normalized_name))
        ).all()


def create_file(
    knowledge: KnowledgeV2,
    database_ids: list[uuid.UUID],
    tag_names: list[tuple[str, str]],
    chunks: list[KnowledgeChunkV2],
):
    with Session(engine) as session:
        session.add(knowledge)
        session.flush()
        session.add_all(
            [
                KnowledgeDatabaseLink(
                    knowledgev2_id=knowledge.id,
                    database_id=database_id,
                    status="active",
                )
                for database_id in database_ids
            ]
        )

        tags = _get_or_create_tags(session, tag_names)

        session.add_all(
            [
                KnowledgeTagLinkV2(knowledgev2_id=knowledge.id, tagv2_id=tag.id)
                for tag in tags
            ]
        )
        session.add_all(chunks)
        session.commit()
        session.refresh(knowledge)
        for tag in tags:
            session.refresh(tag)
        return knowledge, tags


def select_active_file(knowledge_id: uuid.UUID):
    with Session(engine) as session:
        statement = (
            select(KnowledgeV2)
            .join(
                KnowledgeDatabaseLink,
                col(KnowledgeDatabaseLink.knowledgev2_id) == col(KnowledgeV2.id),
            )
            .where(col(KnowledgeV2.id) == knowledge_id)
            .where(col(KnowledgeDatabaseLink.status) == "active")
        )
        return session.exec(statement).first()


def select_owned_file(knowledge_id: uuid.UUID, user_id: uuid.UUID):
    with Session(engine) as session:
        return session.exec(
            select(KnowledgeV2)
            .where(col(KnowledgeV2.id) == knowledge_id)
            .where(col(KnowledgeV2.user_id) == user_id)
        ).first()


def replace_file_content(
    knowledge_id: uuid.UUID,
    user_id: uuid.UUID,
    data: bytes,
    file_type: str,
    md5: str,
    metadata: dict[str, str],
    database_ids: list[uuid.UUID],
    tag_names: list[tuple[str, str]],
    chunks: list[KnowledgeChunkV2],
):
    with Session(engine) as session:
        knowledge = session.exec(
            select(KnowledgeV2)
            .where(col(KnowledgeV2.id) == knowledge_id)
            .where(col(KnowledgeV2.user_id) == user_id)
        ).first()
        if knowledge is None:
            return None

        knowledge.data = data
        knowledge.file_type = file_type
        knowledge.md5 = md5
        knowledge.meta_data = metadata
        knowledge.is_embedded = True
        session.add(knowledge)
        session.exec(
            delete(KnowledgeChunkV2).where(
                col(KnowledgeChunkV2.knowledgev2_id) == knowledge_id
            )
        )
        session.exec(
            delete(KnowledgeDatabaseLink).where(
                col(KnowledgeDatabaseLink.knowledgev2_id) == knowledge_id
            )
        )
        session.exec(
            delete(KnowledgeTagLinkV2).where(
                col(KnowledgeTagLinkV2.knowledgev2_id) == knowledge_id
            )
        )
        tags = _get_or_create_tags(session, tag_names)
        session.add_all(
            [
                KnowledgeDatabaseLink(
                    knowledgev2_id=knowledge_id,
                    database_id=database_id,
                    status="active",
                )
                for database_id in database_ids
            ]
        )
        session.add_all(
            [
                KnowledgeTagLinkV2(knowledgev2_id=knowledge_id, tagv2_id=tag.id)
                for tag in tags
            ]
        )
        session.add_all(chunks)
        session.commit()
        session.refresh(knowledge)
        for tag in tags:
            session.refresh(tag)
        return knowledge, tags


def replace_file_tags(
    knowledge_id: uuid.UUID,
    user_id: uuid.UUID,
    tag_ids: list[uuid.UUID],
    new_tag_names: list[tuple[str, str]],
):
    with Session(engine) as session:
        knowledge = session.exec(
            select(KnowledgeV2)
            .where(col(KnowledgeV2.id) == knowledge_id)
            .where(col(KnowledgeV2.user_id) == user_id)
        ).first()
        if knowledge is None:
            return None

        unique_tag_ids = list(dict.fromkeys(tag_ids))
        selected_tags = (
            session.exec(
                select(KnowledgeTagV2).where(
                    col(KnowledgeTagV2.id).in_(unique_tag_ids)
                )
            ).all()
            if unique_tag_ids
            else []
        )
        if len(selected_tags) != len(unique_tag_ids):
            raise ValueError("包含不存在的公开标签")

        tags_by_name = {tag.normalized_name: tag for tag in selected_tags}
        for tag in _get_or_create_tags(session, new_tag_names):
            tags_by_name[tag.normalized_name] = tag
        tags = sorted(tags_by_name.values(), key=lambda tag: tag.normalized_name)

        session.exec(
            delete(KnowledgeTagLinkV2).where(
                col(KnowledgeTagLinkV2.knowledgev2_id) == knowledge_id
            )
        )
        session.add_all(
            [
                KnowledgeTagLinkV2(knowledgev2_id=knowledge_id, tagv2_id=tag.id)
                for tag in tags
            ]
        )
        session.commit()
        for tag in tags:
            session.refresh(tag)
        return tags


def select_owned_files(knowledge_ids: list[uuid.UUID], user_id: uuid.UUID):
    unique_ids = list(dict.fromkeys(knowledge_ids))
    if not unique_ids:
        return []
    with Session(engine) as session:
        return session.exec(
            select(KnowledgeV2)
            .where(col(KnowledgeV2.id).in_(unique_ids))
            .where(col(KnowledgeV2.user_id) == user_id)
        ).all()


def replace_file_chunks(
    knowledge_id: uuid.UUID,
    user_id: uuid.UUID,
    chunks: list[KnowledgeChunkV2],
):
    with Session(engine) as session:
        knowledge = session.exec(
            select(KnowledgeV2)
            .where(col(KnowledgeV2.id) == knowledge_id)
            .where(col(KnowledgeV2.user_id) == user_id)
        ).first()
        if knowledge is None:
            return None
        session.exec(
            delete(KnowledgeChunkV2).where(
                col(KnowledgeChunkV2.knowledgev2_id) == knowledge_id
            )
        )
        session.add_all(chunks)
        knowledge.is_embedded = True
        session.add(knowledge)
        session.commit()
        return len(chunks)


def delete_owned_file(knowledge_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    with Session(engine) as session:
        knowledge = session.exec(
            select(KnowledgeV2)
            .where(col(KnowledgeV2.id) == knowledge_id)
            .where(col(KnowledgeV2.user_id) == user_id)
        ).first()
        if knowledge is None:
            return False

        session.exec(
            delete(KnowledgeChunkV2).where(
                col(KnowledgeChunkV2.knowledgev2_id) == knowledge_id
            )
        )
        session.exec(
            delete(KnowledgeTagLinkV2).where(
                col(KnowledgeTagLinkV2.knowledgev2_id) == knowledge_id
            )
        )
        session.exec(
            delete(KnowledgeDatabaseLink).where(
                col(KnowledgeDatabaseLink.knowledgev2_id) == knowledge_id
            )
        )
        session.delete(knowledge)
        session.commit()
        return True


def _file_ids_for_tags(normalized_tag_names: list[str]):
    return (
        select(KnowledgeTagLinkV2.knowledgev2_id)
        .join(
            KnowledgeTagV2,
            col(KnowledgeTagLinkV2.tagv2_id) == col(KnowledgeTagV2.id),
        )
        .where(col(KnowledgeTagV2.normalized_name).in_(normalized_tag_names))
        .group_by(col(KnowledgeTagLinkV2.knowledgev2_id))
        .having(func.count(distinct(col(KnowledgeTagV2.id))) == len(normalized_tag_names))
    )


def select_files(
    database_name: str,
    metadata_filters: dict[str, str],
    normalized_tag_names: list[str],
    page: int,
    page_size: int,
):
    with Session(engine) as session:
        id_statement = (
            select(KnowledgeV2.id)
            .join(
                KnowledgeDatabaseLink,
                col(KnowledgeDatabaseLink.knowledgev2_id) == col(KnowledgeV2.id),
            )
            .join(Database, col(KnowledgeDatabaseLink.database_id) == col(Database.id))
            .where(col(Database.database_name) == database_name)
            .where(col(KnowledgeDatabaseLink.status) == "active")
        )
        if metadata_filters:
            id_statement = id_statement.where(
                cast(Any, KnowledgeV2.meta_data).contains(metadata_filters)
            )
        if normalized_tag_names:
            id_statement = id_statement.where(
                col(KnowledgeV2.id).in_(_file_ids_for_tags(normalized_tag_names))
            )

        total = session.exec(
            select(func.count()).select_from(id_statement.subquery())
        ).one()
        paged_ids = session.exec(
            id_statement.order_by(col(KnowledgeV2.create_time).desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        if not paged_ids:
            return [], int(total)

        rows = session.exec(
            select(KnowledgeV2, Sys_User)
            .join(Sys_User, col(KnowledgeV2.user_id) == col(Sys_User.id))
            .where(col(KnowledgeV2.id).in_(paged_ids))
        ).all()
        row_by_id = {knowledge.id: (knowledge, user) for knowledge, user in rows}
        return [row_by_id[file_id] for file_id in paged_ids], int(total)


def select_database_map(knowledge_ids: list[uuid.UUID]):
    if not knowledge_ids:
        return {}
    with Session(engine) as session:
        rows = session.exec(
            select(KnowledgeDatabaseLink.knowledgev2_id, Database)
            .join(Database, col(KnowledgeDatabaseLink.database_id) == col(Database.id))
            .where(col(KnowledgeDatabaseLink.knowledgev2_id).in_(knowledge_ids))
            .where(col(KnowledgeDatabaseLink.status) == "active")
            .order_by(col(Database.database_name))
        ).all()
        result: dict[uuid.UUID, list[Database]] = {}
        for knowledge_id, database in rows:
            result.setdefault(knowledge_id, []).append(database)
        return result


def select_tag_map(knowledge_ids: list[uuid.UUID]):
    if not knowledge_ids:
        return {}
    with Session(engine) as session:
        rows = session.exec(
            select(KnowledgeTagLinkV2.knowledgev2_id, KnowledgeTagV2)
            .join(
                KnowledgeTagV2,
                col(KnowledgeTagLinkV2.tagv2_id) == col(KnowledgeTagV2.id),
            )
            .where(col(KnowledgeTagLinkV2.knowledgev2_id).in_(knowledge_ids))
            .order_by(col(KnowledgeTagV2.normalized_name))
        ).all()
        result: dict[uuid.UUID, list[KnowledgeTagV2]] = {}
        for knowledge_id, tag in rows:
            result.setdefault(knowledge_id, []).append(tag)
        return result


def search_similar_chunks(
    query_embedding: list[float],
    database_name: str,
    normalized_tag_names: list[str],
    top_k: int,
):
    with Session(engine) as session:
        distance = cast(Any, KnowledgeChunkV2.embedding).cosine_distance(
            query_embedding
        ).label("distance")
        statement = (
            select(KnowledgeChunkV2, KnowledgeV2.filename, distance)
            .join(
                KnowledgeV2,
                col(KnowledgeChunkV2.knowledgev2_id) == col(KnowledgeV2.id),
            )
            .join(
                KnowledgeDatabaseLink,
                col(KnowledgeDatabaseLink.knowledgev2_id) == col(KnowledgeV2.id),
            )
            .join(Database, col(KnowledgeDatabaseLink.database_id) == col(Database.id))
            .where(col(Database.database_name) == database_name)
            .where(col(KnowledgeDatabaseLink.status) == "active")
            .where(col(KnowledgeChunkV2.embedding).is_not(None))
        )
        if normalized_tag_names:
            statement = statement.where(
                col(KnowledgeV2.id).in_(_file_ids_for_tags(normalized_tag_names))
            )
        return session.exec(statement.order_by(distance).limit(top_k)).all()