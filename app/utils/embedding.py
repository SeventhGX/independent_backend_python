from app.utils.config import settings
from openai import AsyncOpenAI
import dashscope
from io import BytesIO

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from markitdown import MarkItDown

markitdown = MarkItDown()
QWEN_EMBEDDING_BATCH_SIZE = 10


async def qwen_embedding_texts(input_texts: list[str]):
    if not input_texts:
        return []

    async with AsyncOpenAI(
        api_key=settings.QWEN_EMBEDDING_API_KEY,
        base_url="https://llm-ch7hgluabv286ib6.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
    ) as client:
        embeddings = []
        for start_index in range(0, len(input_texts), QWEN_EMBEDDING_BATCH_SIZE):
            batch = input_texts[start_index : start_index + QWEN_EMBEDDING_BATCH_SIZE]
            completion = await client.embeddings.create(
                model="text-embedding-v4", input=batch, dimensions=1024
            )
            embeddings.extend(item.embedding for item in completion.data)
        return embeddings


async def qwen_embedding_text(input_text: list[str]):
    embeddings = await qwen_embedding_texts(input_text)
    return embeddings[0]


def qwen_embedding_multi(text: str | None = None, image: str | None = None, video: str | None = None):
    input_data = [{"text": text}, {"image": image}, {"video": video}]
    dashscope.MultiModalEmbedding.call(
        # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
        api_key=settings.QWEN_EMBEDDING_API_KEY,
        model="qwen3-vl-embedding",
        input=input_data,  # type: ignore
        enable_fusion=True,
        # 可选参数：指定向量维度（支持 2560, 2048, 1536, 1024, 768, 512, 256，默认 2560）
        # dimension = 1024
    )


def _matches_file_type(file_type: str, accepted_file_types: set[str]) -> bool:
    return file_type in accepted_file_types or any(
        file_type.endswith(f"/{accepted_file_type}") for accepted_file_type in accepted_file_types
    )


def extract_markdown(file_data: bytes, file_type: str | None, file_name: str | None) -> str:
    normalized_file_type = (file_type or "").lower()
    normalized_file_name = (file_name or "").lower()

    if _matches_file_type(
        normalized_file_type, {"text/plain", "txt", "text/markdown", "md"}
    ) or normalized_file_name.endswith((".txt", ".md")):
        return file_data.decode("utf-8", errors="ignore")

    if _matches_file_type(
        normalized_file_type,
        {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ) or normalized_file_name.endswith(".docx"):
        result = markitdown.convert_stream(BytesIO(file_data), file_extension=".docx")
        return result.text_content

    if _matches_file_type(normalized_file_type, {"application/msword"}) or normalized_file_name.endswith(
        ".doc"
    ):
        raise ValueError("暂不支持旧版 .doc 文件，请先转换为 .docx 后再读取")

    raise ValueError(f"不支持的文件类型: {file_type or file_name or 'unknown'}")


def extract_text(file_data: bytes, file_type: str | None, file_name: str | None) -> str:
    return extract_markdown(file_data, file_type, file_name)


def chunk_markdown(
    text: str,
    metadata: dict | None = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[Document]:
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            # ("####", "Header 4"),
            # ("**", "Bold Header"),
        ],
        strip_headers=False,
        # custom_header_patterns={"**": 2},
    )
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        add_start_index=True,
    )

    chunked_documents: list[Document] = []
    for split in markdown_splitter.split_text(text):
        split_metadata = {**(metadata or {}), **split.metadata}
        if len(split.page_content) <= chunk_size:
            chunked_documents.append(Document(page_content=split.page_content, metadata=split_metadata))
            continue

        sub_chunks = recursive_splitter.split_text(split.page_content)
        for sub_chunk_index, sub_chunk in enumerate(sub_chunks):
            chunked_documents.append(
                Document(
                    page_content=sub_chunk,
                    metadata={
                        **split_metadata,
                        "sub_chunk_index": sub_chunk_index,
                        "sub_chunk_total": len(sub_chunks),
                    },
                )
            )
    return chunked_documents


def chunk_text(text: str, chunk_size: int = 600, chunk_overlap: int = 80) -> list[str]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        add_start_index=True,
    )
    return text_splitter.split_text(text)
