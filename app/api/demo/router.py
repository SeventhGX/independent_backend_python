from fastapi import APIRouter

from app.utils.auth import UserDep

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/list", summary="获取支持的 demo 列表")
async def get_demo_list(current_user: UserDep):
    return {
        "message": "success",
        "code": 200,
        "data": [
            {
                "name": "lstm",
                "desc": "LSTM 时间序列预测",
                "type": "time-series",
            },
            {
                "name": "isolation-forest",
                "desc": "Isolation Forest 异常检测",
                "type": "anomaly-detection",
            },
            {
                "name": "kmeans",
                "desc": "K-Means 聚类与肘部法则",
                "type": "clustering",
            },
        ],
    }
