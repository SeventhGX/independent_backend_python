from app.models.tables.databaseTables import Sys_User
from app.models.system import NewUserBody
from datetime import date
from app.utils.database import engine
from sqlmodel import Session, select, or_, col

from pwdlib import PasswordHash


def insert_sys_user(new_user_body: NewUserBody):
    with Session(engine) as session:
        existing_user = session.exec(
            select(Sys_User).where(Sys_User.user_code == new_user_body.user_code)
        ).first()
        if existing_user:
            raise ValueError("用户编码已存在")
        password_hash = PasswordHash.recommended().hash(new_user_body.password)
        new_user = Sys_User(
            user_code=new_user_body.user_code,
            user_name=new_user_body.user_name,
            password=password_hash,
            email=new_user_body.email,
            phone=new_user_body.phone,
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return new_user
