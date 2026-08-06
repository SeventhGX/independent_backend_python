import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class IsolationForestSynthesisParams(BaseModel):
    normal_samples: int = Field(default=500, ge=100, le=10_000)
    anomaly_samples: int = Field(default=25, ge=1, le=1000)
    cluster_std: float = Field(default=0.7, gt=0, le=5)
    anomaly_radius_min: float = Field(default=5, gt=0, le=20)
    anomaly_radius_max: float = Field(default=8, gt=0, le=30)
    seed: int = Field(default=42, ge=0, le=2_147_483_647)

    @model_validator(mode="after")
    def validate_anomaly_distribution(self):
        if self.anomaly_radius_max <= self.anomaly_radius_min:
            raise ValueError("异常点最大半径必须大于最小半径")
        if self.anomaly_samples >= self.normal_samples:
            raise ValueError("异常样本数量必须小于正常样本数量")
        return self


class IsolationForestModelParams(BaseModel):
    n_estimators: int = Field(default=100, ge=10, le=500)
    contamination: float = Field(default=0.05, ge=0.001, le=0.5)
    max_samples: int = Field(default=256, ge=32, le=10_000)


class IsolationForestDetectRequest(BaseModel):
    synthesis: IsolationForestSynthesisParams = Field(
        default_factory=IsolationForestSynthesisParams
    )
    model: IsolationForestModelParams = Field(
        default_factory=IsolationForestModelParams
    )

    @model_validator(mode="after")
    def validate_sample_count(self):
        sample_count = self.synthesis.normal_samples + self.synthesis.anomaly_samples
        if self.model.max_samples > sample_count:
            raise ValueError("模型采样数量不能大于数据集样本总数")
        return self


class IsolationForestMetrics(BaseModel):
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    detected_anomalies: int
    actual_anomalies: int
    detection_seconds: float
    device: str = "cpu"


class IsolationForestResultLinks(BaseModel):
    image: str
    csv: str
    excel: str


class IsolationForestDetectResult(BaseModel):
    result_id: uuid.UUID
    created_at: datetime
    metrics: IsolationForestMetrics
    links: IsolationForestResultLinks


class IsolationForestDetectEnvelope(BaseModel):
    message: str = "success"
    code: int = 200
    data: IsolationForestDetectResult


class IsolationForestParamNode(BaseModel):
    name: str
    desc: str
    type: str
    value: int | float | str | bool | None = None
    minimum: int | float | None = None
    maximum: int | float | None = None
    sub_nodes: list["IsolationForestParamNode"] | None = None