#!/bin/bash

# ====================================
# FastAPI 应用快速更新脚本
# ====================================
# 用途：快速更新应用代码并重启容器
# 使用：./update.sh

set -e  # 遇到错误立即退出

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}FastAPI 应用快速更新${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# 检查是否在项目目录
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${YELLOW}错误：请在项目根目录执行此脚本${NC}"
    exit 1
fi

# 1. 停止应用容器（可选，注释此行可实现滚动更新）
echo -e "${BLUE}[1/4]${NC} 停止应用容器..."
docker-compose stop app

# 2. 重新构建镜像
echo -e "${BLUE}[2/4]${NC} 重新构建 Docker 镜像..."
docker-compose build app

# 3. 启动应用容器
echo -e "${BLUE}[3/4]${NC} 启动应用容器..."
sudo docker-compose up -d app

# 4. 等待服务启动
echo -e "${BLUE}[4/4]${NC} 等待服务启动..."
sleep 3

# 检查健康状态
echo ""
echo -e "${BLUE}检查服务状态...${NC}"
if docker-compose ps app | grep -q "Up"; then
    echo -e "${GREEN}✓ 应用容器运行正常${NC}"
    
    # 尝试健康检查
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 健康检查通过${NC}"
        response=$(curl -s http://localhost:8000/health)
        echo "  响应: $response"
    else
        echo -e "${YELLOW}⚠ 健康检查未通过（服务可能还在启动）${NC}"
        echo -e "${YELLOW}  运行 'docker-compose logs -f app' 查看日志${NC}"
    fi
else
    echo -e "${YELLOW}⚠ 容器状态异常，请检查日志${NC}"
    docker-compose ps app
fi

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}更新完成！${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "查看日志: docker-compose logs -f app"
echo "查看状态: docker-compose ps"
echo ""
