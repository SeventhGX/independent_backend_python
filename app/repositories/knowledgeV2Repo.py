import uuid
from typing import Any, cast

from sqlalchemy import delete, distinct, func, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.models.tables.databaseTables import (
    Database,
    KnowledgeChunkV2,
    KnowledgeDatabaseLink,
    KnowledgeTagLinkV2,
    KnowledgeTagV2,
    KnowledgeV2,
    KnowledgeV2Require,
    Metadata,
    QuestionLog,
    Sys_User,
)
from app.utils.database import engine


class RequirementAlreadyExistsError(Exception):
    def __init__(self, requirement_id: uuid.UUID):
        self.requirement_id = requirement_id
        super().__init__("该问答已创建知识库缺口请求")


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


def _attach_requirements(
    session: Session,
    requirement_ids: list[uuid.UUID],
    knowledge_id: uuid.UUID,
) -> None:
    unique_ids = list(dict.fromkeys(requirement_ids))
    if not unique_ids:
        return
    requirements = session.exec(
        select(KnowledgeV2Require)
        .where(col(KnowledgeV2Require.id).in_(unique_ids))
        .where(col(KnowledgeV2Require.is_resolved).is_(False))
    ).all()
    if len(requirements) != len(unique_ids):
        raise ValueError("包含不存在或已关闭的知识库缺口请求")

    knowledge_id_value = str(knowledge_id)
    for requirement in requirements:
        related_ids = list(requirement.related_knowledgev2_ids or [])
        if knowledge_id_value not in related_ids:
            related_ids.append(knowledge_id_value)
        requirement.related_knowledgev2_ids = related_ids
        session.add(requirement)


def _detach_requirements(
    session: Session,
    knowledge_id: uuid.UUID,
) -> None:
    knowledge_id_value = str(knowledge_id)
    requirements = session.exec(
        select(KnowledgeV2Require)
        .where(
            cast(Any, KnowledgeV2Require.related_knowledgev2_ids).contains(
                [knowledge_id_value]
            )
        )
    ).all()
    for requirement in requirements:
        related_ids = [
            related_id
            for related_id in requirement.related_knowledgev2_ids or []
            if related_id != knowledge_id_value
        ]
        requirement.related_knowledgev2_ids = related_ids
        session.add(requirement)


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
    requirement_ids: list[uuid.UUID] | None = None,
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
        _attach_requirements(
            session,
            requirement_ids or [],
            knowledge.id,
        )
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
    requirement_ids: list[uuid.UUID] | None = None,
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
        _attach_requirements(
            session,
            requirement_ids or [],
            knowledge_id,
        )
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
        _detach_requirements(session, knowledge_id)
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


def select_owned_file_page(
    user_id: uuid.UUID,
    filename: str | None,
    page: int,
    page_size: int,
):
    with Session(engine) as session:
        statement = select(KnowledgeV2).where(col(KnowledgeV2.user_id) == user_id)
        if filename:
            escaped_filename = (
                filename.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            statement = statement.where(
                col(KnowledgeV2.filename).ilike(
                    f"%{escaped_filename}%",
                    escape="\\",
                )
            )
        total = session.exec(
            select(func.count()).select_from(statement.subquery())
        ).one()
        items = session.exec(
            statement.order_by(col(KnowledgeV2.create_time).desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return items, int(total)


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


def select_chunks_by_ids(chunk_ids: list[uuid.UUID]):
    unique_ids = list(dict.fromkeys(chunk_ids))
    if not unique_ids:
        return []
    with Session(engine) as session:
        return session.exec(
            select(KnowledgeChunkV2, KnowledgeV2.filename)
            .join(
                KnowledgeV2,
                col(KnowledgeChunkV2.knowledgev2_id) == col(KnowledgeV2.id),
            )
            .where(col(KnowledgeChunkV2.id).in_(unique_ids))
        ).all()


def select_open_requirements(requirement_ids: list[uuid.UUID]):
    unique_ids = list(dict.fromkeys(requirement_ids))
    if not unique_ids:
        return []
    with Session(engine) as session:
        return session.exec(
            select(KnowledgeV2Require)
            .where(col(KnowledgeV2Require.id).in_(unique_ids))
            .where(col(KnowledgeV2Require.is_resolved).is_(False))
        ).all()


def select_requirements(
    is_resolved: bool | None,
    keyword: str | None,
    page: int,
    page_size: int,
):
    with Session(engine) as session:
        statement = (
            select(KnowledgeV2Require, Sys_User, QuestionLog.question)
            .join(Sys_User, col(KnowledgeV2Require.user_id) == col(Sys_User.id))
            .outerjoin(
                QuestionLog,
                col(KnowledgeV2Require.related_log_id) == col(QuestionLog.id),
            )
        )
        if is_resolved is not None:
            statement = statement.where(
                col(KnowledgeV2Require.is_resolved) == is_resolved
            )
        if keyword:
            escaped_keyword = (
                keyword.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            pattern = f"%{escaped_keyword}%"
            statement = statement.where(
                or_(
                    col(KnowledgeV2Require.requirement).ilike(pattern, escape="\\"),
                    col(QuestionLog.question).ilike(pattern, escape="\\"),
                )
            )

        total = session.exec(
            select(func.count()).select_from(statement.subquery())
        ).one()
        items = session.exec(
            statement.order_by(col(KnowledgeV2Require.create_time).desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return items, int(total)


def update_requirement_status(
    requirement_id: uuid.UUID,
    user_id: uuid.UUID,
    is_admin: bool,
    is_resolved: bool,
):
    with Session(engine) as session:
        requirement = session.get(KnowledgeV2Require, requirement_id)
        if requirement is None:
            return None
        if requirement.user_id != user_id and not is_admin:
            raise PermissionError("仅缺口所有者或管理员可以更新缺口状态")
        requirement.is_resolved = is_resolved
        session.add(requirement)
        session.commit()
        session.refresh(requirement)
        owner = session.get(Sys_User, requirement.user_id)
        if owner is None:
            raise RuntimeError("知识库缺口提出者不存在")
        question = (
            session.get(QuestionLog, requirement.related_log_id)
            if requirement.related_log_id
            else None
        )
        return requirement, owner, question.question if question else None


def create_question_log(question_log: QuestionLog):
    with Session(engine) as session:
        session.add(question_log)
        session.commit()
        session.refresh(question_log)
        return question_log


def update_question_feedback(
    question_log_id: uuid.UUID,
    user_id: uuid.UUID,
    feedback: str,
):
    with Session(engine) as session:
        question_log = session.exec(
            select(QuestionLog)
            .where(col(QuestionLog.id) == question_log_id)
            .where(col(QuestionLog.user_id) == user_id)
        ).first()
        if question_log is None:
            return None
        question_log.user_feedback = feedback
        session.add(question_log)
        session.commit()
        session.refresh(question_log)
        return question_log


def delete_question_log(question_log_id: uuid.UUID, user_id: uuid.UUID):
    with Session(engine) as session:
        question_log = session.exec(
            select(QuestionLog)
            .where(col(QuestionLog.id) == question_log_id)
            .where(col(QuestionLog.user_id) == user_id)
        ).first()
        if question_log is None:
            return None
        session.delete(question_log)
        session.commit()
        return question_log_id


def create_requirement(
    user_id: uuid.UUID,
    related_log_id: uuid.UUID,
    requirement: str | None,
):
    with Session(engine) as session:
        question_log = session.exec(
            select(QuestionLog)
            .where(col(QuestionLog.id) == related_log_id)
            .where(col(QuestionLog.user_id) == user_id)
        ).first()
        if question_log is None:
            return None
        if question_log.user_feedback != "not_helpful":
            raise ValueError("仅可为反馈为 not_helpful 的问答创建知识库缺口请求")

        existing_requirement = session.exec(
            select(KnowledgeV2Require).where(
                col(KnowledgeV2Require.related_log_id) == related_log_id
            )
        ).first()
        if existing_requirement is not None:
            raise RequirementAlreadyExistsError(existing_requirement.id)

        knowledge_requirement = KnowledgeV2Require(
            user_id=user_id,
            requirement=requirement,
            related_log_id=related_log_id,
        )
        session.add(knowledge_requirement)
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            existing_requirement = session.exec(
                select(KnowledgeV2Require).where(
                    col(KnowledgeV2Require.related_log_id) == related_log_id
                )
            ).first()
            if existing_requirement is not None:
                raise RequirementAlreadyExistsError(
                    existing_requirement.id
                ) from error
            raise
        session.refresh(knowledge_requirement)
        return knowledge_requirement, question_log.question


def select_question_logs(
    user_id: uuid.UUID | None,
    feedback: str | None,
    keyword: str | None,
    page: int,
    page_size: int,
):
    with Session(engine) as session:
        statement = select(QuestionLog)
        if user_id is not None:
            statement = statement.where(col(QuestionLog.user_id) == user_id)
        if feedback is not None:
            statement = statement.where(col(QuestionLog.user_feedback) == feedback)
        if keyword:
            escaped_keyword = (
                keyword.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            statement = statement.where(
                col(QuestionLog.question).ilike(
                    f"%{escaped_keyword}%",
                    escape="\\",
                )
            )

        total = session.exec(
            select(func.count()).select_from(statement.subquery())
        ).one()
        items = session.exec(
            statement.order_by(col(QuestionLog.create_time).desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return items, int(total)


def search_similar_questions(query_embedding: list[float], top_k: int):
    with Session(engine) as session:
        distance = cast(Any, QuestionLog.embedding).cosine_distance(
            query_embedding
        ).label("distance")
        statement = (
            select(QuestionLog, distance)
            .where(col(QuestionLog.user_feedback) == "collect")
            .where(col(QuestionLog.embedding).is_not(None))
            .order_by(distance)
            .limit(top_k)
        )
        return session.exec(statement).all()