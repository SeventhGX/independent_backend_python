from datetime import datetime, timedelta, timezone
from typing import Annotated
import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from app.models.system import TokenData

from app.repositories import systemRepo
from app.utils.config import settings

# ---------------------------------------------------------------------------
# 基础配置
# ---------------------------------------------------------------------------

password_hash = PasswordHash.recommended()

# 防时序攻击：用户不存在时仍执行哈希校验
_DUMMY_HASH = password_hash.hash("dummypassword")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/system/token")

# ---------------------------------------------------------------------------
# Token 黑名单（内存实现，key=jti, value=过期时间）
# 生产环境建议替换为 Redis
# ---------------------------------------------------------------------------

_token_blacklist: dict[str, datetime] = {}


def _cleanup_blacklist() -> None:
    """清理已自然过期的 jti，防止内存无限增长。"""
    now = datetime.now(timezone.utc)
    expired = [jti for jti, exp in _token_blacklist.items() if exp <= now]
    for jti in expired:
        del _token_blacklist[jti]


def revoke_token(jti: str, exp: datetime) -> None:
    """将指定 jti 加入黑名单。"""
    _cleanup_blacklist()
    _token_blacklist[jti] = exp


def is_token_revoked(jti: str) -> bool:
    """检查 jti 是否已被吊销。"""
    return jti in _token_blacklist


# ---------------------------------------------------------------------------
# 密码工具
# ---------------------------------------------------------------------------


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


# ---------------------------------------------------------------------------
# 用户认证
# ---------------------------------------------------------------------------


def authenticate_user(user_: str, password: str):
    """根据 user_code 或 user_name 验证用户密码，成功返回 Sys_User，否则返回 False。"""
    user = systemRepo.select_by_user(user_)
    if not user:
        # 仍执行哈希，避免时序攻击泄露账号是否存在
        verify_password(password, _DUMMY_HASH)
        return False
    if not verify_password(password, user.password):
        return False
    return user


# ---------------------------------------------------------------------------
# JWT 工具
# ---------------------------------------------------------------------------


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=15))
    # jti 用于唯一标识本次 token，注销时加入黑名单
    to_encode.update({"exp": expire, "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# FastAPI 依赖项
# ---------------------------------------------------------------------------


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    """解析 JWT，返回当前用户的数据库对象。"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="当前用户未登陆或登陆状态已过期，请重新登录。",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str | None = payload.get("sub")
        jti: str | None = payload.get("jti")
        if username is None or jti is None:
            # jti 缺失说明是旧格式 token，强制重新登录
            raise credentials_exception
        # 检查 token 是否已被主动注销
        if is_token_revoked(jti):
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception

    user = systemRepo.select_by_user(token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_user_with_token(token: Annotated[str, Depends(oauth2_scheme)]):
    """与 get_current_user 相同，但同时返回原始 token 字符串，供注销使用。"""
    user = await get_current_user(token)
    return user, token


async def get_current_active_user(current_user=Depends(get_current_user)):
    """确保当前用户未被删除/禁用。"""
    if current_user.del_flag:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已停用")
    return current_user
