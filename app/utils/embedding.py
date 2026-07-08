from app.utils.config import settings
from openai import AsyncOpenAI
import dashscope
from io import BytesIO

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


async def qwen_embedding_text(input_text: list[str]):
    async with AsyncOpenAI(
        api_key=settings.QWEN_EMBEDDING_API_KEY,
        base_url="https://llm-ch7hgluabv286ib6.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
    ) as client:
        completion = await client.embeddings.create(
            model="text-embedding-v4", input=input_text, dimensions=1024
        )
        return completion.data[0].embedding


def qwen_embedding_multi(text: str | None = None, image: str | None = None, video: str | None = None):
    input_data = [{"text": text}, {"image": image}, {"video": video}]
    resp = dashscope.MultiModalEmbedding.call(
        # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
        api_key=settings.QWEN_EMBEDDING_API_KEY,
        model="qwen3-vl-embedding",
        input=input_data,  # type: ignore
        enable_fusion=True,
        # 可选参数：指定向量维度（支持 2560, 2048, 1536, 1024, 768, 512, 256，默认 2560）
        # dimension = 1024
    )


def docx_chunking(file_data: bytes) -> list[str]:
    document = Document(BytesIO(file_data))
    text_parts: list[str] = []

    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            text = Paragraph(child, document).text.strip()
            if text:
                text_parts.append(text)
        elif child.tag.endswith("}tbl"):
            table = Table(child, document)
            for row in table.rows:
                row_text = "\t".join(cell.text.strip() for cell in row.cells)
                if row_text:
                    text_parts.append(row_text)

    return text_parts


def chunking(file_data: bytes, file_type: str | None, file_name: str | None) -> list[str]:
    normalized_file_type = (file_type or "").lower()
    normalized_file_name = (file_name or "").lower()

    if normalized_file_type in {"text/plain", "txt"} or normalized_file_name.endswith(".txt"):
        return file_data.decode("utf-8", errors="ignore").splitlines()

    if (
        normalized_file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or normalized_file_name.endswith(".docx")
    ):
        return docx_chunking(file_data)

    if normalized_file_type == "application/msword" or normalized_file_name.endswith(".doc"):
        raise ValueError("暂不支持旧版 .doc 文件，请先转换为 .docx 后再读取")

    raise ValueError(f"不支持的文件类型: {file_type or file_name or 'unknown'}")
