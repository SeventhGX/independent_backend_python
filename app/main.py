import base64
import binascii
import json
import time
from email import policy
from email.parser import BytesParser
from urllib.parse import unquote

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.ai.v1 import router as ai_router
from app.api.ai.v2 import router as ai_router_v2
from app.api.article.v1 import router as article_router
from app.api.demo.lstm import demo_router
from app.api.docs.api import router as docs_router
from app.api.knowledge.v1 import router as knowledge_router
from app.api.recipient.v1 import router as recipient_router
from app.api.system.systemApi import router as system_router
from app.utils.log import logger

# from app.utils.database import init_db

# init_db()

app = FastAPI()


def _summarize_multipart_body(body: bytes, content_type: str) -> str:
    try:
        message = BytesParser(policy=policy.default).parsebytes(
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body
        )
    except Exception as e:
        return f"multipart_form=<failed to summarize: {e}; body_size={len(body)}>"

    files = []
    fields = []
    for part in message.iter_parts() if message.is_multipart() else []:
        field_name = part.get_param("name", header="content-disposition")
        filename = part.get_filename()
        if filename is None:
            if field_name:
                fields.append(field_name)
            continue

        payload = part.get_payload(decode=True) or b""
        files.append(
            {
                "field": field_name,
                "filename": filename,
                "size": len(payload),
            }
        )

    return f"multipart_form={{files={files}, fields={fields}}}"


def _format_request_body_for_log(body: bytes, content_type: str) -> str:
    if not body:
        return ""
    # 文件上传接口：multipart/form-data 只记录文件字段、文件名和文件大小，避免把上传文件写进日志。
    if content_type.lower().startswith("multipart/form-data"):
        return _summarize_multipart_body(body, content_type)
    if "application/json" in content_type.lower():
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return body.decode("utf-8", errors="replace")
        return json.dumps(_replace_image_data(payload), ensure_ascii=False)
    return body.decode("utf-8", errors="replace")


def _get_logged_data_size(data) -> int:
    if data is None:
        return 0
    if isinstance(data, str):
        return len(data.encode("utf-8"))
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        return len(json.dumps(data, ensure_ascii=False).encode("utf-8"))
    return len(str(data).encode("utf-8"))


def _looks_like_file_response(value: dict) -> bool:
    return "id" in value and "filename" in value and "file_type" in value and "data" in value


def _get_logged_image_size(data) -> int:
    if isinstance(data, str):
        encoded_data = data.split(",", 1)[1] if data.startswith("data:") and "," in data else data
        try:
            return len(base64.b64decode(encoded_data, validate=True))
        except (binascii.Error, ValueError):
            pass
    return _get_logged_data_size(data)


def _replace_image_data(value):
    if isinstance(value, list):
        return [_replace_image_data(item) for item in value]
    if not isinstance(value, dict):
        return value

    return {
        key: {"size": _get_logged_image_size(item)} if key == "image_data" else _replace_image_data(item)
        for key, item in value.items()
    }


def _replace_file_response_data(value):
    if isinstance(value, list):
        return [_replace_file_response_data(item) for item in value]
    if not isinstance(value, dict):
        return value

    result = {key: _replace_file_response_data(item) for key, item in value.items()}
    if _looks_like_file_response(result):
        result["data"] = {"size": _get_logged_data_size(value.get("data"))}
    return result


def _extract_download_filename(content_disposition: str) -> str | None:
    for item in content_disposition.split(";"):
        item = item.strip()
        if item.lower().startswith("filename*="):
            value = item.split("=", 1)[1].strip().strip('"')
            if "''" in value:
                value = value.split("''", 1)[1]
            return unquote(value)
        if item.lower().startswith("filename="):
            return unquote(item.split("=", 1)[1].strip().strip('"'))
    return None


def _summarize_download_response(body: bytes, content_type: str, content_disposition: str) -> str:
    return json.dumps(
        {
            "download": True,
            "filename": _extract_download_filename(content_disposition),
            "media_type": content_type,
            "size": len(body),
        },
        ensure_ascii=False,
    )


def _summarize_image_response(body: bytes, content_type: str, content_disposition: str) -> str:
    return json.dumps(
        {
            "image": True,
            "filename": _extract_download_filename(content_disposition),
            "media_type": content_type,
            "size": len(body),
        },
        ensure_ascii=False,
    )


def _format_response_body_for_log(body: bytes, content_type: str, headers) -> str:
    if not body:
        return ""
    content_disposition = headers.get("content-disposition", "")

    # 文件下载接口：带 attachment 的二进制响应只记录文件名、类型和大小，避免把下载内容写进日志。
    if "attachment" in content_disposition.lower():
        return _summarize_download_response(body, content_type, content_disposition)

    # 图片预览和缩略图响应只记录元数据，避免将完整二进制内容写入日志。
    if content_type.lower().startswith("image/"):
        return _summarize_image_response(body, content_type, content_disposition)

    if "application/json" not in content_type.lower():
        return body.decode("utf-8", errors="replace")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body.decode("utf-8", errors="replace")

    # 文件查询接口：JSON 中出现 FileResponse 结构时，将 data 替换为大小摘要。
    return json.dumps(_replace_file_response_data(payload), ensure_ascii=False)


class LogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 记录请求信息
        query_params = dict(request.query_params)
        body = await request.body()

        # 健康检查和用户信息接口不进行日志记录，避免日志过大
        if request.url.path in ["/health", "/system/users/me"]:
            return await call_next(request)

        logger.info(
            f"[REQUEST] {request.method} {request.url.path} | "
            f"query_params={query_params} | "
            f"body={_format_request_body_for_log(body, request.headers.get('content-type', ''))}"
        )

        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # 流式响应接口：SSE 等直接透传，不消费 body_iterator，否则会破坏流式传输。
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            logger.info(
                f"[END] {request.method} {request.url.path} | "
                f"status={response.status_code} | "
                f"duration={process_time:.3f}s | streaming=true"
            )
            return response

        # 读取普通响应体并记录日志
        resp_body = b""
        async for chunk in response.body_iterator:  # type: ignore
            resp_body += chunk

        logger.debug(
            f"[RESPONSE] {request.method} {request.url.path} | "
            f"body={_format_response_body_for_log(resp_body, content_type, response.headers)}"
        )

        logger.info(
            f"[END] {request.method} {request.url.path} | "
            f"status={response.status_code} | "
            f"duration={process_time:.3f}s"
        )

        return Response(
            content=resp_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )


app.add_middleware(LogMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # 允许的前端地址
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有请求头
)


@app.get("/health")
async def health_check():
    """健康检查端点，用于 Docker 健康检查和负载均衡器"""
    return {"status": "healthy", "service": "independent-backend-python"}


app.include_router(system_router, tags=["system"])
app.include_router(article_router, tags=["articles"])
app.include_router(recipient_router, tags=["recipients"])
app.include_router(ai_router, tags=["ai"])
app.include_router(ai_router_v2, tags=["ai_v2"])
app.include_router(knowledge_router, tags=["knowledge"])
app.include_router(docs_router, tags=["docs"])
app.include_router(demo_router)
