from pydantic import BaseModel

from app.utils.auth import UserDep

from .router import router as demo_router


class LstmParamNode(BaseModel):
    name: str
    desc: str
    type: str
    value: float | None = None
    options: list[str] | None = None
    sub_nodes: list["LstmParamNode"] | None = None


@demo_router.get("/lstm/param-list", summary="获取 demo 支持自定义的参数")
def get_demo_param_list(current_user: UserDep):
    pass
