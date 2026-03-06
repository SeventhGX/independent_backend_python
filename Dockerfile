# 使用官方 Python 镜像作为基础镜像
FROM python:3.13-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（PostgreSQL 客户端库等）
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv（快速的 Python 包管理器）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 复制项目配置文件
COPY pyproject.toml uv.lock ./

# 使用 uv 同步依赖（创建虚拟环境并安装依赖）
RUN uv sync --frozen --no-dev

# 复制应用代码
COPY app ./app

# 创建日志目录
RUN mkdir -p /app/log

# 设置 Python 路径
ENV PYTHONPATH=/app

# 暴露应用端口
EXPOSE 8000

# 使用 uv 运行 uvicorn（生产环境推荐）
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
