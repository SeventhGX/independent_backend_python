# 🚀 服务器部署快速命令卡片

## 📦 需要上传的文件

运行以下命令查看需要上传的文件清单：
```bash
./list-deploy-files.sh
```

**核心文件（必需）：**
- ✅ `app/` - 应用代码目录
- ✅ `Dockerfile` - Docker 构建文件
- ✅ `docker-compose.yml` - 容器编排配置
- ✅ `pyproject.toml` + `uv.lock` - Python 依赖
- ✅ `deploy.sh` - 一键部署脚本
- ✅ `update.sh` - 快速更新脚本
- ✅ `Makefile` - 运维命令工具

**不要上传：**
- ❌ `.env` - 需在服务器单独配置
- ❌ `.git/`, `__pycache__/`, `log/`, `functionDemo/`

---

## 📤 上传到服务器

### 方式 1：使用 rsync（推荐）⚡
```bash
# 上传所有必需文件（自动排除不需要的）
rsync -avz --progress \
  --exclude='.git' \
  --exclude='.env' \
  --exclude='__pycache__' \
  --exclude='log' \
  --exclude='functionDemo' \
  --exclude='.vscode' \
  --exclude='backups' \
  ./ user@server:/path/to/app/
```

### 方式 2：使用 Git
```bash
# 在服务器上
git clone https://your-repo.git
cd your-repo
```

---

## 🎯 首次部署（在服务器上）

```bash
# 1. 进入项目目录
cd /path/to/independent_backend_python

# 2. 配置环境变量
cp .env.production.example .env
vim .env  # 编辑配置

# 3. 确保外部容器运行
docker ps | grep postgres-18
docker ps | grep my-redis

# 4. 一键部署
chmod +x deploy.sh
./deploy.sh

# 5. 验证
curl http://localhost:8000/health
```

**重要配置（在 .env 中）：**
```bash
COMPOSE_PROJECT_NAME=app_backend
DATABASE_HOST=postgres-18
DATABASE_USER=your_user
DATABASE_PASSWORD=strong_password
DATABASE_NAME=your_database
JWT_SECRET_KEY=运行_openssl_rand_-hex_32_生成
```

---

## 🔄 应用更新（最常用）

### ⚡ 方式 1：快速更新（30秒）
**仅更新应用代码时使用**

```bash
# 本地 → 上传代码
rsync -avz ./app/ user@server:/path/to/app/app/

# 服务器 → 更新
ssh user@server
cd /path/to/independent_backend_python
./update.sh
# 或
make update
```

**等价于：**
```bash
docker-compose stop app      # 停止容器
docker-compose build app     # 重新构建
docker-compose up -d app     # 启动容器
```

---

### 🔄 方式 2：完整更新
**更新了 Dockerfile 或依赖时使用**

```bash
# 1. 上传所有文件
rsync -avz --exclude='.git' --exclude='.env' \
  ./ user@server:/path/to/app/

# 2. 服务器操作
ssh user@server
cd /path/to/independent_backend_python

# 3. 完整重建
make down
make build
make up

# 或使用
make rebuild
```

---

## 📋 更新步骤对比

| 步骤 | 快速更新 | 完整更新 |
|------|---------|---------|
| 上传文件 | 只上传 `app/` | 上传所有文件 |
| 停止容器 | 自动 | `make down` |
| 构建镜像 | 增量构建 | 完整重建 |
| 启动容器 | 自动 | `make up` |
| 耗时 | ~30秒 | ~2-3分钟 |
| 使用场景 | 代码修改 | 配置/依赖变更 |

---

## 🛠️ 常用运维命令

```bash
# 查看状态
make ps                    # 容器状态
make logs-app              # 实时日志
docker stats app_backend   # 资源使用

# 重启服务
make restart-app           # 快速重启
make restart               # 重启所有

# 进入容器
make exec-app              # 进入应用容器
make exec-db               # 进入数据库

# 数据备份
make backup                # 备份数据库

# 查看所有命令
make help
```

---

## 🔍 故障排查

```bash
# 查看日志
docker-compose logs -f app
docker-compose logs --tail=100 app

# 检查配置
docker-compose config

# 测试网络
docker exec app_backend ping postgres-18
docker exec app_backend curl http://localhost:8000/health

# 重新部署
make down && make rebuild
```

---

## ⏱️ 典型更新时间线

**快速更新流程：**
```
00:00 - 本地上传代码 (rsync)           → 10秒
00:10 - SSH 登录服务器                 → 2秒
00:12 - 运行 ./update.sh              → 开始
00:13 - 停止容器                       → 1秒
00:14 - 构建镜像                       → 10秒
00:24 - 启动容器                       → 2秒
00:26 - 健康检查                       → 3秒
00:29 - 完成 ✓
```

**总耗时：约 30 秒** ⏱️

---

## 📞 获取帮助

详细文档：
- **服务器部署**：`SERVER_DEPLOYMENT.md`
- **Docker 部署**：`DOCKER_DEPLOYMENT.md`
- **快速参考**：`QUICK_REFERENCE.md`
- **所有命令**：`make help`

---

**快速提示：** 
- 💡 99% 的更新只需要：`rsync + ./update.sh`
- 💡 记住命令：`make update` = 停止 + 构建 + 启动
- 💡 查看日志：`make logs-app`
