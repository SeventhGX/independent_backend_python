import uuid
from urllib.parse import quote

from fastapi import HTTPException, Response, status

from app.models.isolation_forest import (
    IsolationForestDetectEnvelope,
    IsolationForestDetectRequest,
    IsolationForestDetectResult,
    IsolationForestMetrics,
    IsolationForestParamNode,
    IsolationForestResultLinks,
)
from app.models.tables.databaseTables import IsolationForestResult
from app.services import isolationForestServ
from app.utils.auth import UserDep

from .router import router as demo_router


@demo_router.get(
    "/isolation-forest/param-list",
    summary="获取 Isolation Forest demo 支持的参数",
)
def get_isolation_forest_param_list(current_user: UserDep):
    return {
        "message": "success",
        "code": 200,
        "data": [
            IsolationForestParamNode(
                name="synthesis",
                desc="二维合成数据参数",
                type="group",
                sub_nodes=[
                    IsolationForestParamNode(
                        name="normal_samples",
                        desc="正常样本数量",
                        type="integer",
                        value=500,
                        minimum=100,
                        maximum=10_000,
                    ),
                    IsolationForestParamNode(
                        name="anomaly_samples",
                        desc="注入异常样本数量",
                        type="integer",
                        value=25,
                        minimum=1,
                        maximum=1000,
                    ),
                    IsolationForestParamNode(
                        name="cluster_std",
                        desc="正常样本簇标准差",
                        type="number",
                        value=0.7,
                        minimum=0,
                        maximum=5,
                    ),
                    IsolationForestParamNode(
                        name="anomaly_radius_min",
                        desc="异常点最小分布半径",
                        type="number",
                        value=5,
                        minimum=0,
                        maximum=20,
                    ),
                    IsolationForestParamNode(
                        name="anomaly_radius_max",
                        desc="异常点最大分布半径",
                        type="number",
                        value=8,
                        minimum=0,
                        maximum=30,
                    ),
                    IsolationForestParamNode(
                        name="seed",
                        desc="随机种子",
                        type="integer",
                        value=42,
                        minimum=0,
                        maximum=2_147_483_647,
                    ),
                ],
            ),
            IsolationForestParamNode(
                name="model",
                desc="Isolation Forest 模型参数",
                type="group",
                sub_nodes=[
                    IsolationForestParamNode(
                        name="n_estimators",
                        desc="孤立树数量",
                        type="integer",
                        value=100,
                        minimum=10,
                        maximum=500,
                    ),
                    IsolationForestParamNode(
                        name="contamination",
                        desc="预期异常样本比例",
                        type="number",
                        value=0.05,
                        minimum=0.001,
                        maximum=0.5,
                    ),
                    IsolationForestParamNode(
                        name="max_samples",
                        desc="每棵孤立树的采样数量",
                        type="integer",
                        value=256,
                        minimum=32,
                        maximum=10_000,
                    ),
                ],
            ),
        ],
    }


def _build_detect_result(
    result: IsolationForestResult,
) -> IsolationForestDetectEnvelope:
    result_id = result.id
    return IsolationForestDetectEnvelope(
        data=IsolationForestDetectResult(
            result_id=result_id,
            created_at=result.create_time,
            metrics=IsolationForestMetrics.model_validate(result.metrics),
            links=IsolationForestResultLinks(
                image=f"/demo/isolation-forest/results/{result_id}/image",
                csv=f"/demo/isolation-forest/results/{result_id}/csv",
                excel=f"/demo/isolation-forest/results/{result_id}/excel",
            ),
        )
    )


@demo_router.post(
    "/isolation-forest/detect",
    summary="运行 Isolation Forest 异常检测",
    response_model=IsolationForestDetectEnvelope,
)
async def detect_anomalies(
    request: IsolationForestDetectRequest,
    current_user: UserDep,
):
    result = await isolationForestServ.detect_and_store(request, current_user.id)
    return _build_detect_result(result)


def _get_result_or_404(
    result_id: uuid.UUID,
    current_user: UserDep,
) -> IsolationForestResult:
    result = isolationForestServ.get_result(result_id, current_user.id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Isolation Forest result not found",
        )
    return result


@demo_router.get(
    "/isolation-forest/results/{result_id}/image",
    summary="预览 Isolation Forest 检测结果图",
)
def get_isolation_forest_result_image(
    result_id: uuid.UUID,
    current_user: UserDep,
):
    result = _get_result_or_404(result_id, current_user)
    filename = quote(f"isolation-forest-{result_id}.png")
    return Response(
        content=isolationForestServ.render_result_image(result),
        media_type="image/png",
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{filename}"},
    )


@demo_router.get(
    "/isolation-forest/results/{result_id}/csv",
    summary="下载 Isolation Forest 检测 CSV",
)
def download_isolation_forest_result_csv(
    result_id: uuid.UUID,
    current_user: UserDep,
):
    result = _get_result_or_404(result_id, current_user)
    filename = quote(f"isolation-forest-{result_id}.csv")
    return Response(
        content=isolationForestServ.export_result_csv(result),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@demo_router.get(
    "/isolation-forest/results/{result_id}/excel",
    summary="下载 Isolation Forest 检测 Excel",
)
def download_isolation_forest_result_excel(
    result_id: uuid.UUID,
    current_user: UserDep,
):
    result = _get_result_or_404(result_id, current_user)
    filename = quote(f"isolation-forest-{result_id}.xlsx")
    return Response(
        content=isolationForestServ.export_result_excel(result),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )