import base64
import binascii
from io import BytesIO
import uuid

from PIL import Image, ImageOps, UnidentifiedImageError

from app.models.docs import (
    DocsCreateRequest,
    DocsImageCreateRequest,
    DocsImageInfo,
    DocsImageUpdateRequest,
    DocsUpdateRequest,
)
from app.models.tables.databaseTables import Docs, DocsImage
from app.repositories import docsRepo


async def get_docs_list():
    return docsRepo.select_all_docs()


async def get_docs(docs_id: uuid.UUID):
    return docsRepo.select_docs_by_id(docs_id)


async def create_docs(request: DocsCreateRequest):
    return docsRepo.insert_docs(Docs(**request.model_dump()))


async def update_docs(docs_id: uuid.UUID, request: DocsUpdateRequest):
    return docsRepo.update_docs(docs_id, request.model_dump(exclude_unset=True))


async def delete_docs(docs_id: uuid.UUID):
    return docsRepo.delete_docs(docs_id)


async def get_image_list(docs_id: uuid.UUID | None = None):
    rows = docsRepo.select_image_info(docs_id)
    return [
        DocsImageInfo(
            id=row[0],
            docs_id=row[1],
            image_name=row[2],
            image_desc=row[3],
            create_time=row[4],
            create_by=row[5],
        )
        for row in rows
    ]


async def get_image(image_id: uuid.UUID):
    return docsRepo.select_image_by_id(image_id)


async def create_image(request: DocsImageCreateRequest, user_id: uuid.UUID):
    if request.docs_id is not None and docsRepo.select_docs_by_id(request.docs_id) is None:
        raise ValueError("Docs not found")
    values = request.model_dump()
    values["image_data"] = _normalize_image_data(request.image_data)
    return docsRepo.insert_image(DocsImage(**values, create_by=user_id))


async def update_image(image_id: uuid.UUID, request: DocsImageUpdateRequest):
    values = request.model_dump(exclude_unset=True)
    if "docs_id" in values and values["docs_id"] is not None:
        if docsRepo.select_docs_by_id(values["docs_id"]) is None:
            raise ValueError("Docs not found")
    if values.get("image_data") is not None:
        values["image_data"] = _normalize_image_data(values["image_data"])
    return docsRepo.update_image(image_id, values)


async def delete_image(image_id: uuid.UUID):
    return docsRepo.delete_image(image_id)


async def create_thumbnail(image_data: bytes, max_size: int) -> bytes:
    try:
        with Image.open(BytesIO(image_data)) as source:
            image = ImageOps.exif_transpose(source)
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            if image.mode not in ("RGB", "L"):
                background = Image.new("RGB", image.size, "white")
                if "A" in image.getbands():
                    background.paste(image, mask=image.getchannel("A"))
                else:
                    background.paste(image.convert("RGB"))
                image = background
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=75, optimize=True)
            return buffer.getvalue()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Invalid image data") from exc


def _normalize_image_data(image_data: bytes) -> bytes:
    try:
        with Image.open(BytesIO(image_data)) as image:
            image.verify()
        return image_data
    except (UnidentifiedImageError, OSError):
        try:
            decoded = base64.b64decode(image_data, validate=True)
            with Image.open(BytesIO(decoded)) as image:
                image.verify()
            return decoded
        except (binascii.Error, UnidentifiedImageError, OSError) as exc:
            raise ValueError("Invalid image data") from exc
