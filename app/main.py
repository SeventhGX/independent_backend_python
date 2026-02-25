from fastapi import FastAPI
from app.api.article.v1 import router as article_router
from app.api.recipient.v1 import router as recipient_router

from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # 允许的前端地址
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有请求头
)


app.include_router(article_router, prefix="/articles", tags=["articles"])
app.include_router(recipient_router, tags=["recipients"])
