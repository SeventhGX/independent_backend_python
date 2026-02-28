from pydantic import BaseModel


class NewUserBody(BaseModel):
    user_code: str
    user_name: str
    password: str
    email: str | None = None
    phone: str | None = None
