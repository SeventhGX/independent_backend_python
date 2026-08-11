import uuid
from urllib.parse import quote

from fastapi import HTTPException, Response, status

from app.models.kmeans import (
    KMeansClusterEnvelope,
    KMeansClusterRequest,
    KMeansClusterResult,
    KMeansMetrics,
    KMeansParamNode,
    KMeansResultLinks,
)
from app.models.tables.databaseTables import KMeansResult
from app.services import kmeansServ
from app.utils.auth import UserDep

from .router import router as demo_router


@demo_router.get(
    "/kmeans/param-list",
    summary="获取 K-Means demo 支持的参数",
)
def get_kmeans_param_list(current_user: UserDep):
    return {
        "message": "success",
        "code": 200,
        "data": [
            KMeansParamNode(
                name="synthesis",
                desc="二维合成数据参数",
                type="group",
                sub_nodes=[
                    KMeansParamNode(
                        name="cluster_count",
                        desc="真实簇数量",
                        type="integer",
                        value=4,
                        minimum=2,
                        maximum=10,
                    ),
                    KMeansParamNode(
                        name="samples_per_cluster",
                        desc="每个簇的样本数量",
                        type="integer",
                        value=150,
                        minimum=20,
                        maximum=1000,
                    ),
                    KMeansParamNode(
                        name="cluster_std",
                        desc="簇内样本标准差",
                        type="number",
                        value=4,
                        minimum=0,
                        maximum=5,
                    ),
                    KMeansParamNode(
                        name="center_spread",
                        desc="簇中心分布半径",
                        type="number",
                        value=15,
                        minimum=0,
                        maximum=30,
                    ),
                    KMeansParamNode(
                        name="seed",
                        desc="随机种子",
                        type="integer",
                        value=42,
                        minimum=0,
                        maximum=2_147_483_647,
                    ),
                ],
            ),
            KMeansParamNode(
                name="model",
                desc="K-Means 模型参数",
                type="group",
                sub_nodes=[
                    KMeansParamNode(
                        name="n_clusters",
                        desc="聚类簇数 K",
                        type="integer",
                        value=4,
                        minimum=2,
                        maximum=12,
                    ),
                    KMeansParamNode(
                        name="init",
                        desc="质心初始化方式",
                        type="enum",
                        value="k-means++",
                        options=["k-means++", "random"],
                    ),
                    KMeansParamNode(
                        name="n_init",
                        desc="重复初始化次数",
                        type="integer",
                        value=10,
                        minimum=1,
                        maximum=50,
                    ),
                    KMeansParamNode(
                        name="max_iter",
                        desc="单次运行最大迭代次数",
                        type="integer",
                        value=300,
                        minimum=10,
                        maximum=1000,
                    ),
                    KMeansParamNode(
                        name="tol",
                        desc="质心变化收敛阈值",
                        type="number",
                        value=0.0001,
                        minimum=0,
                        maximum=1,
                    ),
                ],
            ),
            KMeansParamNode(
                name="evaluation",
                desc="聚类评估参数",
                type="group",
                sub_nodes=[
                    KMeansParamNode(
                        name="elbow_max_k",
                        desc="肘部法则遍历的最大簇数",
                        type="integer",
                        value=8,
                        minimum=2,
                        maximum=12,
                    ),
                ],
            ),
        ],
    }


def _build_cluster_result(result: KMeansResult) -> KMeansClusterEnvelope:
    result_id = result.id
    return KMeansClusterEnvelope(
        data=KMeansClusterResult(
            result_id=result_id,
            created_at=result.create_time,
            metrics=KMeansMetrics.model_validate(result.metrics),
            links=KMeansResultLinks(
                image=f"/demo/kmeans/results/{result_id}/image",
                csv=f"/demo/kmeans/results/{result_id}/csv",
                excel=f"/demo/kmeans/results/{result_id}/excel",
            ),
        )
    )


@demo_router.post(
    "/kmeans/cluster",
    summary="运行 K-Means 聚类",
    response_model=KMeansClusterEnvelope,
)
async def cluster_samples(
    request: KMeansClusterRequest,
    current_user: UserDep,
):
    result = await kmeansServ.cluster_and_store(request, current_user.id)
    return _build_cluster_result(result)


def _get_result_or_404(
    result_id: uuid.UUID,
    current_user: UserDep,
) -> KMeansResult:
    result = kmeansServ.get_result(result_id, current_user.id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KMeans result not found",
        )
    return result


@demo_router.get(
    "/kmeans/results/{result_id}/image",
    summary="预览 K-Means 聚类结果图",
)
def get_kmeans_result_image(
    result_id: uuid.UUID,
    current_user: UserDep,
):
    result = _get_result_or_404(result_id, current_user)
    filename = quote(f"kmeans-{result_id}.png")
    return Response(
        content=kmeansServ.render_result_image(result),
        media_type="image/png",
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{filename}"},
    )


@demo_router.get(
    "/kmeans/results/{result_id}/csv",
    summary="下载 K-Means 聚类 CSV",
)
def download_kmeans_result_csv(
    result_id: uuid.UUID,
    current_user: UserDep,
):
    result = _get_result_or_404(result_id, current_user)
    filename = quote(f"kmeans-{result_id}.csv")
    return Response(
        content=kmeansServ.export_result_csv(result),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@demo_router.get(
    "/kmeans/results/{result_id}/excel",
    summary="下载 K-Means 聚类 Excel",
)
def download_kmeans_result_excel(
    result_id: uuid.UUID,
    current_user: UserDep,
):
    result = _get_result_or_404(result_id, current_user)
    filename = quote(f"kmeans-{result_id}.xlsx")
    return Response(
        content=kmeansServ.export_result_excel(result),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )
