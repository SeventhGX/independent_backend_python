#!/bin/bash

# ====================================
# FastAPI Docker 快速部署脚本
# ====================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Docker 是否安装
check_docker() {
    print_info "检查 Docker 环境..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    print_success "Docker 环境检查通过"
}

# 检查并创建 .env 文件
check_env_file() {
    print_info "检查环境配置文件..."
    
    if [ ! -f .env ]; then
        print_warning ".env 文件不存在，从模板创建..."
        
        if [ -f .env.production.example ]; then
            cp .env.production.example .env
            print_success ".env 文件已创建"
            print_warning "请编辑 .env 文件，填写实际配置后重新运行此脚本"
            print_info ""
            print_info "必填配置项："
            print_info "  1. DATABASE_USER - 数据库用户名"
            print_info "  2. DATABASE_PASSWORD - 数据库密码（建议使用强密码）"
            print_info "  3. DATABASE_NAME - 数据库名称"
            print_info "  4. JWT_SECRET_KEY - JWT 密钥（运行 'openssl rand -hex 32' 生成）"
            print_info "  5. DEEPSEEK_API_KEY - DeepSeek API 密钥"
            print_info "  6. DOUBAO_API_KEY - 豆包 API 密钥"
            print_info "  7. DOUBAO_CRAWLER_BOT_ID - 豆包爬虫 Bot ID"
            print_info ""
            print_info "配置完成后，重新运行: ./deploy.sh"
            exit 0
        else
            print_error "找不到 .env.production.example 文件"
            exit 1
        fi
    else
        print_success "环境配置文件已存在"
    fi
    
    # 检查必填项
    print_info "验证环境配置..."
    
    missing_vars=()
    
    if ! grep -q "DATABASE_PASSWORD=.*[^CHANGE_THIS]" .env; then
        missing_vars+=("DATABASE_PASSWORD")
    fi
    
    if ! grep -q "JWT_SECRET_KEY=.*[^CHANGE_THIS]" .env; then
        missing_vars+=("JWT_SECRET_KEY")
    fi
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        print_error "以下配置项需要更新："
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        print_info "请编辑 .env 文件后重新运行"
        exit 1
    fi
    
    print_success "环境配置验证通过"
}

# 构建镜像
build_images() {
    print_info "开始构建 Docker 镜像..."
    docker-compose build
    print_success "镜像构建完成"
}

# 启动服务
start_services() {
    print_info "启动所有服务..."
    docker-compose up -d
    
    print_info "等待服务启动..."
    sleep 5
    
    # 检查服务状态
    print_info "检查服务状态..."
    docker-compose ps
}

# 检查服务健康状态
check_health() {
    print_info "等待服务健康检查..."
    
    max_attempts=30
    attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            print_success "应用健康检查通过"
            response=$(curl -s http://localhost:8000/health)
            echo "  响应: $response"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    
    echo ""
    print_warning "健康检查超时，请手动检查应用日志"
    print_info "运行 'docker-compose -p app_backend logs app' 查看日志"
    return 1
}

# 显示部署信息
show_info() {
    print_success "======================================"
    print_success "部署完成！"
    print_success "======================================"
    echo ""
    print_info "服务访问信息："
    echo "  - 应用地址: http://localhost:8000"
    echo "  - 健康检查: http://localhost:8000/health"
    echo "  - API 文档: http://localhost:8000/docs"
    echo ""
    print_info "默认管理员账号（首次初始化后）："
    echo "  - 用户代码: 00000000"
    echo "  - 用户名: admin"
    echo "  - 密码: admin123"
    echo "  ⚠️  生产环境请立即修改密码！"
    echo ""
    print_info "常用命令："
    echo "  - 查看日志: docker-compose logs -f app"
    echo "  - 停止服务: docker-compose down"
    echo "  - 重启服务: docker-compose restart"
    echo "  - 查看状态: docker-compose ps"
    echo ""
    print_info "更多信息请查看 DOCKER_DEPLOYMENT.md"
}

# 主函数
main() {
    echo ""
    echo "======================================"
    echo "FastAPI Docker 快速部署"
    echo "======================================"
    echo ""
    
    # 执行部署步骤
    check_docker
    check_env_file
    build_images
    start_services
    
    # 检查健康状态
    if check_health; then
        show_info
    else
        print_warning "部署已完成，但健康检查未通过"
        print_info "请运行以下命令查看日志："
        echo "  docker-compose logs app"
    fi
}

# 运行主函数
main
