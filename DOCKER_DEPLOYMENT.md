# Docker 部署指南

本指南将帮助您使用 Docker 和 Docker Compose 将 FastAPI 应用部署到生产环境。

## 架构说明

本应用使用多容器架构，包含以下服务：

- **app**：FastAPI 应用容器（使用 uv 管理 Python 环境）
- **postgres**：PostgreSQL 数据库容器
- **redis**：Redis 缓存容器

所有容器通过 Docker 网络 `app_network` 相互通信，数据通过 Docker volumes 持久化。

## 前置要求

- Docker 20.10 或更高版本
- Docker Compose 2.0 或更高版本

检查版本：
```bash
docker --version
docker-compose --version
```

## 快速开始

### 1. 配置环境变量

首先，复制环境变量示例文件并填写实际值：

```bash
cp .env.example .env
```

编辑 `.env` 文件，至少需要配置以下必填项：

```bash
# 数据库配置（生产环境请使用强密码）
DATABASE_USER=your_db_user
DATABASE_PASSWORD=your_secure_password
DATABASE_NAME=independent_backend

# 首次部署时设为 true 以初始化数据库
INITIALIZE_DB=true

# AI API Keys（根据实际使用情况配置）
DEEPSEEK_API_KEY=sk-xxxxx
DOUBAO_API_KEY=your_doubao_api_key
DOUBAO_CRAWLER_BOT_ID=your_bot_id

# JWT 密钥（使用以下命令生成）
# openssl rand -hex 32
JWT_SECRET_KEY=your_generated_secret_key_here
```

### 2. 构建并启动所有服务

```bash
# 构建镜像并启动所有容器
docker-compose up -d

# 查看容器状态
docker-compose ps

# 查看应用日志
docker-compose logs -f app
```

### 3. 验证部署

应用启动后，可以通过以下方式验证：

```bash
# 检查健康检查端点
curl http://localhost:8000/health

# 预期输出
# {"status":"healthy","service":"independent-backend-python"}
```

### 4. 数据库初始化

首次部署时，应用会自动创建数据表和默认管理员账号：
- 用户代码：`00000000`
- 用户名：`admin`
- 密码：`admin123`

**重要：生产环境请立即修改默认密码！**

## 常用操作

### 查看日志

```bash
# 查看所有服务的日志
docker-compose logs -f

# 只查看应用日志
docker-compose logs -f app

# 只查看数据库日志
docker-compose logs -f postgres

# 只查看最近 100 行日志
docker-compose logs --tail=100 app
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 只重启应用服务
docker-compose restart app
```

### 停止服务

```bash
# 停止所有服务（保留数据）
docker-compose stop

# 停止并删除容器（保留数据卷）
docker-compose down

# 停止并删除容器和数据卷（⚠️ 会删除所有数据）
docker-compose down -v
```

### 更新应用

当代码更新后，需要重新构建镜像：

```bash
# 重新构建应用镜像
docker-compose build app

# 或者强制重新构建（不使用缓存）
docker-compose build --no-cache app

# 重启应用容器
docker-compose up -d app
```

### 进入容器

```bash
# 进入应用容器
docker-compose exec app bash

# 进入数据库容器
docker-compose exec postgres psql -U your_db_user -d independent_backend

# 进入 Redis 容器
docker-compose exec redis redis-cli
```

### 数据备份

#### 备份 PostgreSQL 数据库

```bash
# 导出数据库
docker-compose exec postgres pg_dump -U your_db_user independent_backend > backup_$(date +%Y%m%d_%H%M%S).sql

# 或者使用 docker cp（包含二进制格式）
docker-compose exec postgres pg_dump -U your_db_user -Fc independent_backend > backup.dump
```

#### 恢复数据库

```bash
# 从 SQL 文件恢复
docker-compose exec -T postgres psql -U your_db_user independent_backend < backup.sql

# 从 dump 文件恢复
docker-compose exec -T postgres pg_restore -U your_db_user -d independent_backend < backup.dump
```

## 生产环境配置建议

### 1. 环境变量安全

- 不要将 `.env` 文件提交到版本控制系统
- 使用强密码和随机生成的密钥
- 定期轮换敏感凭证

### 2. 端口映射

默认配置中，所有服务端口都映射到宿主机。在生产环境中：

- **app 端口**：保持映射（通过反向代理访问）
- **postgres 端口**：可以移除映射（除非需要外部访问）
- **redis 端口**：可以移除映射（除非需要外部访问）

移除端口映射示例（编辑 `docker-compose.yml`）：

```yaml
postgres:
  # 注释掉或删除 ports 部分
  # ports:
  #   - "5432:5432"
```

### 3. 使用反向代理

建议在应用前加一层反向代理（如 Nginx 或 Traefik），提供：
- HTTPS 支持
- 负载均衡
- 静态文件服务
- 速率限制

Nginx 配置示例：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. 资源限制

在生产环境中，建议为容器设置资源限制（编辑 `docker-compose.yml`）：

```yaml
app:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 512M
```

### 5. 日志管理

配置日志轮转以防止日志文件过大：

```yaml
app:
  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "3"
```

### 6. 健康检查

配置文件中已包含健康检查，确保容器异常时自动重启。可以通过以下命令查看健康状态：

```bash
docker-compose ps
# 状态列应显示 "UP (healthy)"
```

## 监控和维护

### 查看资源使用情况

```bash
# 查看容器资源使用
docker stats

# 查看磁盘使用
docker system df

# 清理未使用的资源
docker system prune -a
```

### 定期维护

1. **定期备份数据库**（建议每天）
2. **监控磁盘空间**（日志和数据卷）
3. **更新镜像**（定期更新基础镜像以获取安全补丁）
4. **查看应用日志**（发现潜在问题）

## 故障排查

### 应用无法启动

```bash
# 查看详细日志
docker-compose logs app

# 常见问题：
# 1. 数据库连接失败 -> 检查 DATABASE_* 环境变量
# 2. Redis 连接失败 -> 检查 Redis 容器状态
# 3. 端口被占用 -> 修改 APP_PORT
```

### 数据库连接问题

```bash
# 检查数据库容器是否运行
docker-compose ps postgres

# 测试数据库连接
docker-compose exec postgres psql -U your_db_user -d independent_backend -c "SELECT 1"

# 查看数据库日志
docker-compose logs postgres
```

### 容器频繁重启

```bash
# 查看容器状态
docker-compose ps

# 查看重启原因
docker-compose logs --tail=50 app

# 检查健康检查
docker inspect independent_backend_app | grep -A 10 Health
```

## 网络配置说明

所有容器都在同一个 Docker 网络 `app_network` 中，容器间通信规则：

- **app → postgres**：通过主机名 `postgres` 和端口 `5432`
- **app → redis**：通过主机名 `redis` 和端口 `6379`

容器内部使用服务名作为主机名，无需使用 `localhost` 或 IP 地址。

## 安全检查清单

部署前请确认：

- [ ] 修改了所有默认密码
- [ ] 使用了强 JWT 密钥
- [ ] `.env` 文件已添加到 `.gitignore`
- [ ] 数据库密码足够复杂
- [ ] 移除了不必要的端口映射
- [ ] 配置了反向代理和 HTTPS
- [ ] 启用了日志轮转
- [ ] 设置了自动备份计划

## 支持

如有问题，请查看：
1. 应用日志：`docker-compose logs app`
2. 容器状态：`docker-compose ps`
3. 健康检查：访问 `http://localhost:8000/health`

---

**祝部署顺利！🚀**
