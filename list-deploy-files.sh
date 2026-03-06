#!/bin/bash

# ====================================
# 生成部署文件列表
# ====================================
# 用途：列出需要上传到服务器的所有文件
# 使用：./list-deploy-files.sh

echo "================================"
echo "需要上传到服务器的文件"
echo "================================"
echo ""
echo "📦 必需文件："
echo ""

# 必需文件
files=(
    "Dockerfile"
    "docker-compose.yml"
    ".dockerignore"
    "pyproject.toml"
    "uv.lock"
    "deploy.sh"
    "update.sh"
    "Makefile"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        size=$(du -h "$file" | cut -f1)
        echo "  ✓ $file ($size)"
    else
        echo "  ✗ $file (缺失)"
    fi
done

echo ""
echo "📂 必需目录："
echo ""

if [ -d "app" ]; then
    size=$(du -sh app | cut -f1)
    file_count=$(find app -type f | wc -l)
    echo "  ✓ app/ ($size, $file_count 个文件)"
else
    echo "  ✗ app/ (缺失)"
fi

echo ""
echo "📄 推荐文件（文档）："
echo ""

docs=(
    "README.md"
    "DOCKER_DEPLOYMENT.md"
    "QUICK_REFERENCE.md"
    "SERVER_DEPLOYMENT.md"
    ".env.production.example"
)

for file in "${docs[@]}"; do
    if [ -f "$file" ]; then
        size=$(du -h "$file" | cut -f1)
        echo "  ✓ $file ($size)"
    else
        echo "  - $file (不存在)"
    fi
done

echo ""
echo "🚫 不要上传的文件/目录："
echo ""
echo "  ✗ .env (包含敏感信息，需在服务器单独配置)"
echo "  ✗ .git/ (版本控制，体积大)"
echo "  ✗ .vscode/ (IDE 配置)"
echo "  ✗ __pycache__/ (Python 缓存)"
echo "  ✗ log/ (日志文件)"
echo "  ✗ functionDemo/ (演示代码)"
echo "  ✗ backups/ (备份文件)"
echo ""
echo "================================"
echo "总计大小估算："
echo "================================"

# 计算总大小（排除不需要的文件）
total_size=$(du -sh --exclude=.git --exclude=.env --exclude=__pycache__ --exclude=log --exclude=functionDemo --exclude=.vscode --exclude=backups . 2>/dev/null | cut -f1)
echo "  需要上传: $total_size (约)"
echo ""
