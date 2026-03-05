from pydantic import BaseModel


class NewUserBody(BaseModel):
    user_code: str
    user_name: str
    password: str
    email: str | None = None
    phone: str | None = None


class UserInfo(BaseModel):
    """对外暴露的用户信息（不含密码哈希）"""

    user_code: str
    user_name: str
    email: str | None = None
    phone: str | None = None
    del_flag: bool = False


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str
