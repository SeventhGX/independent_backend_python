from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.models.system import NewUserBody
from app.repositories import systemRepo
from app.utils.auth import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_current_user_with_token,
    revoke_token,
)
from app.models.system import UserInfo, Token
from app.utils.config import settings

router = APIRouter(prefix="/system")


# ---------------------------------------------------------------------------
# 登录
# ---------------------------------------------------------------------------


@router.post("/token", response_model=Token, summary="用户登录获取 Token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.user_code},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token, token_type="bearer")


# ---------------------------------------------------------------------------
# 当前用户信息
# ---------------------------------------------------------------------------


@router.get("/users/me", response_model=UserInfo, summary="获取当前登录用户信息")
async def read_users_me(current_user=Depends(get_current_active_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="当前用户未登陆或登陆状态已过期，请重新登录。",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return UserInfo(
        user_code=current_user.user_code,
        user_name=current_user.user_name,
        email=current_user.email,
        phone=current_user.phone,
        del_flag=current_user.del_flag,
    )


# ---------------------------------------------------------------------------
# 注销
# ---------------------------------------------------------------------------


@router.post("/logout", summary="用户注销登录")
async def logout(user_and_token: tuple = Depends(get_current_user_with_token)):
    _, token = user_and_token
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    jti: str | None = payload.get("jti")
    exp_ts = payload.get("exp")
    if not jti or not exp_ts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token 格式无效，请重新登录后再注销。",
        )
    exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
    revoke_token(jti, exp_dt)
    return {"code": 200, "message": "注销成功"}


# ---------------------------------------------------------------------------
# 注册新用户（按需保留，生产环境建议增加管理员权限校验）
# ---------------------------------------------------------------------------


@router.post("/users/register", response_model=UserInfo, summary="注册新用户")
async def register_user(new_user_body: NewUserBody):
    # systemRepo.insert_sys_user 内部已处理密码哈希，直接传入明文密码即可
    try:
        user = systemRepo.insert_sys_user(new_user_body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return UserInfo(
        user_code=user.user_code,
        user_name=user.user_name,
        email=user.email,
        phone=user.phone,
        del_flag=user.del_flag,
    )
