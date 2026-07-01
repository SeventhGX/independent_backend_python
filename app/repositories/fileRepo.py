from app.models.tables.databaseTables import File
import base64
import uuid
from app.utils.database import engine
from sqlmodel import Session, select, col


def _is_image_file(file: File) -> bool:
    return bool(file.file_type) and file.file_type.lower().startswith("image/")


# base64 字符集（含 url-safe 变体与换行/填充），用于判断数据是否已是 base64 编码
_B64_CHARS = frozenset(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=-_\r\n"
)


def _looks_like_base64(data: bytes) -> bool:
    # 原始图片字节（如 PNG \x89、JPEG \xff）会包含 base64 字符集之外的字节，
    # 而合法 base64 仅由 ASCII 字母数字及 +/=（或 url-safe 的 -_）和换行构成，据此区分新旧数据
    if not data:
        return False
    return all(byte in _B64_CHARS for byte in bytes(data))


def insert_file(file: File):
    # 图片以 base64 形式传入，落库前解码为原始字节以降低硬盘占用
    if _is_image_file(file) and file.data:
        file.data = base64.b64decode(file.data)
    with Session(engine) as db_session:
        db_session.add(file)
        db_session.commit()
        db_session.refresh(file)
        return file


def _encode_image_file(file: File | None):
    # 图片以原始字节存储，查询时重新编码为 base64 供上层使用；
    # 若数据本身已是 base64（历史遗留数据），则原样返回以兼容旧数据
    if file is not None and _is_image_file(file) and file.data and not _looks_like_base64(file.data):
        file.data = base64.b64encode(bytes(file.data))
    return file


def select_file_by_id(file_id: uuid.UUID):
    with Session(engine) as session:
        return _encode_image_file(session.exec(select(File).where(File.id == file_id)).first())


def select_files_by_ids(file_ids: list[uuid.UUID]):
    if not file_ids:
        return []
    with Session(engine) as session:
        files = session.exec(select(File).where(col(File.id).in_(file_ids))).all()
        return [_encode_image_file(file) for file in files]
