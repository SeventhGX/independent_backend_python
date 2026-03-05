from app.models.tables.databaseTables import Sys_User
from app.models.system import NewUserBody
from app.utils.database import engine
from sqlmodel import Session, select, or_

from pwdlib import PasswordHash


def insert_sys_user(new_user_body: NewUserBody):
    with Session(engine) as session:
        existing_user = session.exec(
            select(Sys_User).where(Sys_User.user_code == new_user_body.user_code)
        ).first()
        if existing_user:
            raise ValueError("用户编号已存在")
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


def select_by_user(user_: str) -> Sys_User | None:
    with Session(engine) as session:
        user = session.exec(
            select(Sys_User).where(or_(Sys_User.user_code == user_, Sys_User.user_name == user_))
        ).first()
        return user
