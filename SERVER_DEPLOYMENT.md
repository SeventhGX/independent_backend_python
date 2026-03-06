# 🚀 生产服务器部署指南

## 📦 需要上传到服务器的文件

### 必需文件（核心）
```
independent_backend_python/
├── app/                          # 应用代码目录（必需）
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   ├── models/
│   ├── repositories/
│   ├── services/
│   └── utils/
├── Dockerfile                    # Docker 镜像构建文件（必需）
├── docker-compose.yml            # 容器编排配置（必需）
├── .dockerignore                 # Docker 构建排除规则（必需）
├── pyproject.toml               # Python 项目配置（必需）
├── uv.lock                      # 依赖锁定文件（必需）
├── deploy.sh                    # 一键部署脚本（推荐）
└── Makefile                     # 便捷命令工具（推荐）
```

### 可选文件（文档）
```
├── README.md                    # 项目说明
├── DOCKER_DEPLOYMENT.md         # Docker 部署文档
├── QUICK_REFERENCE.md           # 快速参考
└── .env.production.example      # 环境变量模板
```

### ⚠️ 不要上传的文件
```
❌ .env                          # 本地环境配置（包含敏感信息）
❌ .git/                         # Git 仓库（体积大）
❌ .vscode/                      # IDE 配置
❌ __pycache__/                  # Python 缓存
❌ log/                          # 日志文件
❌ functionDemo/                 # 演示代码
❌ backups/                      # 备份文件
```

---

## 🎯 首次部署流程

### 1. 准备服务器环境

```bash
# 确保已安装 Docker 和 Docker Compose
docker --version
docker-compose --version

# 如果未安装，安装 Docker（Ubuntu/Debian 示例）
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装 Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin
```

### 2. 上传文件到服务器

**方式 1：使用 rsync（推荐）**
```bash
# 在本地执行，上传必需文件
rsync -avz --progress \
  --exclude='.git' \
  --exclude='.env' \
  --exclude='__pycache__' \
  --exclude='log' \
  --exclude='functionDemo' \
  --exclude='.vscode' \
  --exclude='backups' \
  ./ user@your-server:/path/to/app/

# 或使用简化命令（推荐）
rsync -avz --progress \
  --exclude-from='.gitignore' \
  --exclude='.git' \
  ./ user@your-server:/path/to/app/
```

**方式 2：使用 Git（推荐）**
```bash
# 在服务器上执行
cd /path/to/
git clone https://your-git-repo.git independent_backend_python
cd independent_backend_python
```

**方式 3：使用 scp**
```bash
# 打包并上传
tar czf app.tar.gz \
  --exclude='.git' \
  --exclude='.env' \
  --exclude='__pycache__' \
  --exclude='log' \
  --exclude='functionDemo' \
  .

scp app.tar.gz user@your-server:/path/to/
ssh user@your-server "cd /path/to && tar xzf app.tar.gz"
```

### 3. 在服务器上配置环境变量

```bash
# SSH 登录到服务器
ssh user@your-server
cd /path/to/independent_backend_python

# 创建 .env 文件
cp .env.production.example .env

# 编辑配置（使用你习惯的编辑器）
vim .env
# 或
nano .env
```

**重要配置项**：
```bash
# Docker 配置
COMPOSE_PROJECT_NAME=app_backend

# 数据库配置（使用外部容器名）
DATABASE_HOST=postgres-18
DATABASE_PORT=5432
DATABASE_USER=your_db_user
DATABASE_PASSWORD=your_secure_password
DATABASE_NAME=your_db_name
INITIALIZE_DB=true  # 首次部署设为 true

# Redis 配置
REDIS_HOST=my-redis
REDIS_PORT=6379

# AI API Keys
DEEPSEEK_API_KEY=sk-xxxxx
DOUBAO_API_KEY=xxxxx
DOUBAO_CRAWLER_BOT_ID=bot-xxxxx

# JWT 配置（生成新的密钥）
JWT_SECRET_KEY=$(openssl rand -hex 32)
```

### 4. 确保外部容器运行

```bash
# 检查 PostgreSQL 容器
docker ps | grep postgres-18

# 如果没有运行，启动它
docker start postgres-18

# 检查 Redis 容器
docker ps | grep my-redis

# 如果没有运行，启动它
docker start my-redis
```

### 5. 首次部署

```bash
# 添加执行权限
chmod +x deploy.sh

# 运行部署脚本
./deploy.sh

# 部署脚本会自动：
# 1. 检查 Docker 环境
# 2. 验证 .env 配置
# 3. 构建 Docker 镜像
# 4. 启动应用容器
# 5. 执行健康检查
```

### 6. 验证部署

```bash
# 查看容器状态
docker-compose ps

# 查看应用日志
docker-compose logs -f app

# 测试健康检查
curl http://localhost:8000/health

# 测试 API 文档
curl http://localhost:8000/docs
```

---

## 🔄 应用更新流程

### 方案 A：快速更新（推荐）⚡

当你只更新了应用代码（`app/` 目录），使用此方法：

```bash
# 1. 上传新代码到服务器
rsync -avz --progress ./app/ user@your-server:/path/to/independent_backend_python/app/

# 2. SSH 登录到服务器
ssh user@your-server
cd /path/to/independent_backend_python

# 3. 使用 Makefile 一键更新（推荐）
make update

# 等价于：
# docker-compose build app
# docker-compose up -d app
```

**完整流程：**
```bash
# 本地 → 服务器上传
rsync -avz ./app/ user@server:/path/to/app/app/

# 服务器操作
ssh user@server
cd /path/to/independent_backend_python
make update
make logs-app  # 查看启动日志
```

**总耗时：约 30-60 秒** ⏱️

---

### 方案 B：完整更新流程

当你更新了 Dockerfile、依赖（pyproject.toml）或其他配置文件时：

```bash
# === 在服务器上操作 ===

# 1. 进入项目目录
cd /path/to/independent_backend_python

# 2. 停止应用容器（保留数据）
docker-compose down
# 或
make down

# 3. 更新代码（选择一种方式）
# 方式 1：如果使用 Git
git pull origin main

# 方式 2：如果使用 rsync（在本地执行）
rsync -avz --exclude='.git' --exclude='.env' \
  ./ user@server:/path/to/independent_backend_python/

# 4. 重新构建镜像
docker-compose build --no-cache
# 或
make rebuild

# 5. 启动服务
docker-compose up -d
# 或
make up

# 6. 验证部署
docker-compose ps
docker-compose logs -f app
curl http://localhost:8000/health
```

---

### 方案 C：零停机更新（进阶）🔥

如果需要零停机部署，可以使用滚动更新：

```bash
# 1. 构建新镜像（带新标签）
docker-compose build
docker tag app_backend:latest app_backend:v2

# 2. 启动新容器（使用不同端口）
docker run -d --name app_backend_v2 \
  --env-file .env \
  -e APP_PORT=8001 \
  -p 8001:8000 \
  --network bridge \
  --link postgres-18 \
  --link my-redis \
  app_backend:v2

# 3. 验证新版本
curl http://localhost:8001/health

# 4. 切换流量（通过反向代理或修改端口映射）
# 5. 停止旧容器
docker stop app_backend
docker rm app_backend

# 6. 重命名新容器
docker rename app_backend_v2 app_backend
```

---

## 📝 常用运维命令

### 查看状态
```bash
# 查看所有容器
docker ps -a

# 查看应用日志（实时）
docker-compose logs -f app

# 查看最近 100 行日志
docker-compose logs --tail=100 app

# 查看资源使用
docker stats app_backend
```

### 重启服务
```bash
# 重启应用（方式 1：推荐）
make restart-app

# 重启应用（方式 2）
docker-compose restart app

# 完全重启（停止 → 启动）
docker-compose down && docker-compose up -d
```

### 进入容器
```bash
# 进入应用容器
docker-compose exec app bash

# 查看应用环境
docker-compose exec app env

# 查看日志文件
docker-compose exec app ls -la /app/log
```

### 数据备份
```bash
# 备份数据库
make backup

# 手动备份
docker exec postgres-18 pg_dump -U hanaga department > backup_$(date +%Y%m%d).sql

# 下载备份到本地
scp user@server:/path/to/backups/backup_*.sql ./
```

---

## 🔐 安全检查清单

部署前请确认：

- [ ] ✅ 修改了所有默认密码
- [ ] ✅ 使用了强 JWT 密钥（`openssl rand -hex 32`）
- [ ] ✅ `.env` 文件权限设置为 600（`chmod 600 .env`）
- [ ] ✅ 数据库密码足够复杂（至少 16 位）
- [ ] ✅ 配置了防火墙规则（只开放必要端口）
- [ ] ✅ 设置了反向代理（Nginx/Caddy）
- [ ] ✅ 配置了 HTTPS 证书
- [ ] ✅ 启用了日志轮转
- [ ] ✅ 设置了自动备份计划
- [ ] ✅ 配置了监控告警

---

## 🚨 故障排查

### 容器无法启动
```bash
# 查看详细日志
docker-compose logs app

# 查看容器状态
docker-compose ps

# 检查配置
docker-compose config
```

### 数据库连接失败
```bash
# 检查外部容器状态
docker ps | grep postgres-18
docker ps | grep my-redis

# 测试网络连接
docker exec app_backend ping postgres-18
docker exec app_backend ping my-redis

# 检查环境变量
docker-compose exec app env | grep DATABASE
```

### 端口冲突
```bash
# 查看端口占用
sudo netstat -tlnp | grep 8000
# 或
sudo lsof -i :8000

# 修改端口（编辑 .env）
echo "APP_PORT=8001" >> .env
docker-compose up -d
```

---

## 📊 性能优化建议

### 1. 多进程运行
编辑 Dockerfile，使用多个 worker：

```dockerfile
CMD ["uv", "run", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4"]
```

### 2. 资源限制
编辑 docker-compose.yml，添加资源限制：

```yaml
app:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '0.5'
        memory: 512M
```

### 3. 日志轮转
```yaml
app:
  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "3"
```

---

## 📞 获取帮助

- 查看完整文档：`DOCKER_DEPLOYMENT.md`
- 快速命令参考：`QUICK_REFERENCE.md`
- Makefile 命令列表：`make help`
- 健康检查：`curl http://localhost:8000/health`

---

**祝部署顺利！🎉**
