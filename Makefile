.PHONY: help build up down restart logs ps clean backup

# 默认目标：显示帮助信息
help:
	@echo "================================"
	@echo "Docker 部署管理命令"
	@echo "================================"
	@echo ""
	@echo "基础操作："
	@echo "  make build       - 构建 Docker 镜像"
	@echo "  make up          - 启动所有服务"
	@echo "  make down        - 停止所有服务"
	@echo "  make restart     - 重启所有服务"
	@echo ""
	@echo "监控操作："
	@echo "  make logs        - 查看所有服务日志"
	@echo "  make logs-app    - 查看应用日志"
	@echo "  make logs-db     - 查看数据库日志"
	@echo "  make ps          - 查看容器状态"
	@echo "  make stats       - 查看资源使用情况"
	@echo ""
	@echo "维护操作："
	@echo "  make clean       - 清理未使用的 Docker 资源"
	@echo "  make backup      - 备份数据库"
	@echo "  make exec-app    - 进入应用容器"
	@echo "  make exec-db     - 进入数据库容器"
	@echo ""
	@echo "开发操作："
	@echo "  make rebuild     - 重新构建并启动应用"
	@echo "  make update      - 更新应用（重新构建 app 容器）"
	@echo ""

# 构建镜像
build:
	@echo "构建 Docker 镜像..."
	docker-compose build

# 启动所有服务
up:
	@echo "启动所有服务..."
	docker-compose up -d
	@echo "等待服务启动..."
	@sleep 3
	@echo "服务状态："
	@docker-compose ps

# 停止所有服务
down:
	@echo "停止所有服务..."
	docker-compose down

# 停止并删除所有数据（危险操作）
down-volumes:
	@echo "⚠️  警告：此操作将删除所有数据！"
	@read -p "确认删除所有数据？[y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker-compose down -v; \
		echo "已删除所有容器和数据卷"; \
	else \
		echo "操作已取消"; \
	fi

# 重启所有服务
restart:
	@echo "重启所有服务..."
	docker-compose restart

# 重启应用服务
restart-app:
	@echo "重启应用服务..."
	docker-compose restart app

# 查看所有日志
logs:
	docker-compose logs -f

# 查看应用日志
logs-app:
	docker-compose logs -f app

# 注意：数据库和 Redis 运行在外部容器中
# 查看外部数据库日志
logs-db:
	docker logs -f postgres-18

# 查看外部 Redis 日志
logs-redis:
	docker logs -f my-redis

# 查看容器状态
ps:
	docker-compose ps

# 查看资源使用
stats:
	docker stats

# 清理未使用的资源
clean:
	@echo "清理未使用的 Docker 资源..."
	docker system prune -f

# 深度清理（包括未使用的镜像）
deep-clean:
	@echo "深度清理 Docker 资源..."
	docker system prune -af

# 备份外部数据库
backup:
	@echo "备份数据库..."
	@mkdir -p backups
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	docker exec postgres-18 pg_dump -U $$DATABASE_USER $$DATABASE_NAME > backups/backup_$$TIMESTAMP.sql && \
	echo "备份完成: backups/backup_$$TIMESTAMP.sql" || \
	echo "备份失败，请检查数据库配置"

# 恢复数据库（需要指定备份文件）
# 使用方法：make restore FILE=backups/backup_20240101_120000.sql
restore:
	@if [ -z "$(FILE)" ]; then \
		echo "错误：请指定备份文件"; \
		echo "使用方法：make restore FILE=backups/backup_20240101_120000.sql"; \
		exit 1; \
	fi
	@echo "恢复数据库从 $(FILE)..."
	@docker exec -i postgres-18 psql -U $$DATABASE_USER $$DATABASE_NAME < $(FILE)
	@echo "恢复完成"

# 进入应用容器
exec-app:
	docker-compose exec app bash

# 进入外部数据库容器
exec-db:
	docker exec -it postgres-18 psql -U $$DATABASE_USER -d $$DATABASE_NAME

# 进入外部 Redis 容器
exec-redis:
	docker exec -it my-redis redis-cli

# 重新构建并启动
rebuild:
	@echo "重新构建并启动..."
	docker-compose build --no-cache
	docker-compose up -d
	@echo "重启完成"

# 更新应用
update:
	@echo "更新应用..."
	docker-compose build app
	docker-compose up -d app
	@echo "应用更新完成"

# 检查健康状态
health:
	@echo "检查服务健康状态..."
	@curl -s http://localhost:8000/health | json_pp || curl -s http://localhost:8000/health

# 初始化（首次部署）
init:
	@echo "初始化部署环境..."
	@if [ ! -f .env ]; then \
		echo "创建 .env 文件..."; \
		cp .env.production.example .env; \
		echo "请编辑 .env 文件，填写实际配置"; \
		echo ""; \
		echo "必填项："; \
		echo "  - DATABASE_USER"; \
		echo "  - DATABASE_PASSWORD"; \
		echo "  - DATABASE_NAME"; \
		echo "  - JWT_SECRET_KEY (使用 openssl rand -hex 32 生成)"; \
		echo "  - DEEPSEEK_API_KEY"; \
		echo "  - DOUBAO_API_KEY"; \
		echo "  - DOUBAO_CRAWLER_BOT_ID"; \
		echo ""; \
		echo "配置完成后执行：make build && make up"; \
	else \
		echo ".env 文件已存在，跳过创建"; \
	fi

# 显示环境变量（隐藏敏感信息）
show-env:
	@echo "当前环境变量配置："
	@cat .env 2>/dev/null | grep -E "^[A-Z]" | sed 's/=.*/=***/' || echo ".env 文件不存在"
