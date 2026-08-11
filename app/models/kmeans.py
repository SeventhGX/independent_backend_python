import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class KMeansSynthesisParams(BaseModel):
    cluster_count: int = Field(default=4, ge=2, le=10)
    samples_per_cluster: int = Field(default=150, ge=20, le=1000)
    cluster_std: float = Field(default=4, gt=0, le=5)
    center_spread: float = Field(default=15, gt=0, le=30)
    seed: int = Field(default=42, ge=0, le=2_147_483_647)


class KMeansModelParams(BaseModel):
    n_clusters: int = Field(default=4, ge=2, le=12)
    init: Literal["k-means++", "random"] = "k-means++"
    n_init: int = Field(default=10, ge=1, le=50)
    max_iter: int = Field(default=300, ge=10, le=1000)
    tol: float = Field(default=0.0001, gt=0, le=1)


class KMeansEvaluationParams(BaseModel):
    elbow_max_k: int = Field(default=8, ge=2, le=12)


class KMeansClusterRequest(BaseModel):
    synthesis: KMeansSynthesisParams = Field(default_factory=KMeansSynthesisParams)
    model: KMeansModelParams = Field(default_factory=KMeansModelParams)
    evaluation: KMeansEvaluationParams = Field(
        default_factory=KMeansEvaluationParams
    )

    @model_validator(mode="after")
    def validate_elbow_range(self):
        if self.evaluation.elbow_max_k < self.model.n_clusters:
            raise ValueError("肘部法则最大簇数不能小于模型聚类簇数")
        return self


class KMeansMetrics(BaseModel):
    inertia: float
    silhouette: float
    davies_bouldin: float
    calinski_harabasz: float
    adjusted_rand_index: float
    iterations: int
    actual_k: int
    suggested_k: int
    sample_count: int
    cluster_seconds: float
    device: str = "cpu"


class KMeansResultLinks(BaseModel):
    image: str
    csv: str
    excel: str


class KMeansClusterResult(BaseModel):
    result_id: uuid.UUID
    created_at: datetime
    metrics: KMeansMetrics
    links: KMeansResultLinks


class KMeansClusterEnvelope(BaseModel):
    message: str = "success"
    code: int = 200
    data: KMeansClusterResult


class KMeansParamNode(BaseModel):
    name: str
    desc: str
    type: str
    value: int | float | str | bool | None = None
    minimum: int | float | None = None
    maximum: int | float | None = None
    options: list[str] | None = None
    sub_nodes: list["KMeansParamNode"] | None = None
