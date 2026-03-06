# 🚀 Docker 部署快速参考

## 一键部署

```bash
./deploy.sh
```

## 常用命令

### 启动/停止

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启单个服务
docker-compose restart app
```

### 日志查看

```bash
# 查看所有日志
docker-compose logs -f

# 查看应用日志
docker-compose logs -f app

# 查看最近 100 行
docker-compose logs --tail=100 app
```

### 服务管理

```bash
# 查看服务状态
docker-compose ps

# 查看资源使用
docker stats

# 健康检查
curl http://localhost:8000/health
```

### 容器操作

```bash
# 进入应用容器
docker-compose exec app bash

# 进入数据库（外部容器 postgres-18）
docker exec -it postgres-18 psql -U [用户名] -d [数据库名]

# 进入 Redis（外部容器 my-redis）
docker exec -it my-redis redis-cli
```

### 更新应用

```bash
# 方式 1：使用 Makefile
make update

# 方式 2：手动更新
docker-compose build app
docker-compose up -d app
```

### 数据备份

```bash
# 备份数据库（使用 Makefile）
make backup

# 手动备份（备份外部数据库 postgres-18）
docker exec postgres-18 pg_dump -U [用户名] [数据库名] > backup.sql
```

## 使用 Makefile（推荐）

```bash
# 查看所有命令
make help

# 初始化项目
make init

# 构建并启动
make build && make up

# 查看日志
make logs-app

# 备份数据库
make backup

# 更新应用
make update

# 检查健康状态
make health
```

## 服务访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 应用首页 | http://localhost:8000 | FastAPI 应用 |
| API 文档 | http://localhost:8000/docs | Swagger UI |
| 健康检查 | http://localhost:8000/health | 健康状态 |
| PostgreSQL | localhost:5432 | 外部数据库 (postgres-18) |
| Redis | localhost:6379 | 外部缓存 (my-redis) |

## 默认账号（首次初始化）

- **用户代码**: `00000000`
- **用户名**: `admin`
- **密码**: `admin123`

⚠️ **生产环境请立即修改密码！**

## 故障排查

### 容器无法启动

```bash
# 查看详细日志
docker-compose logs app

# 检查配置文件
docker-compose config
```

### 数据库连接失败

```bash
# 检查外部数据库容器状态
docker ps | grep postgres-18

# 测试连接
docker exec postgres-18 pg_isready -U [用户名]
```

### 端口被占用

编辑 `.env` 文件，修改 `APP_PORT`

## 环境配置

关键环境变量（在 `.env` 文件中配置）：

```bash
DATABASE_USER=your_user
DATABASE_PASSWORD=strong_password
DATABASE_NAME=your_database
JWT_SECRET_KEY=your_secret_key  # 使用 openssl rand -hex 32 生成
DEEPSEEK_API_KEY=sk-xxx
DOUBAO_API_KEY=xxx
```

## 安全检查清单

- [ ] 修改了所有默认密码
- [ ] 使用强 JWT 密钥
- [ ] `.env` 文件不在版本控制中
- [ ] 配置了反向代理和 HTTPS
- [ ] 设置了日志轮转
- [ ] 配置了自动备份

## 获取帮助

- 详细文档：`DOCKER_DEPLOYMENT.md`
- 查看日志：`docker-compose logs app`
- 容器状态：`docker-compose ps`
- 健康检查：`http://localhost:8000/health`

---

**祝部署顺利！** 🎉
