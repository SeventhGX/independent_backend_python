import time
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.api.article.v1 import router as article_router
from app.api.recipient.v1 import router as recipient_router
from app.api.system.systemApi import router as system_router
from app.api.ai.v1 import router as ai_router
from app.utils.log import logger

from fastapi.middleware.cors import CORSMiddleware

# from app.utils.database import init_db

# init_db()

app = FastAPI()


class LogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 记录请求信息
        query_params = dict(request.query_params)
        body = await request.body()
        logger.info(
            f"[REQUEST] {request.method} {request.url.path} | "
            f"query_params={query_params} | "
            f"body={body.decode('utf-8', errors='replace') if body else ''}"
        )

        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # 流式响应（SSE 等）直接透传，不消费 body_iterator，否则会破坏流式传输
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
            f"body={resp_body.decode('utf-8', errors='replace')}"
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
