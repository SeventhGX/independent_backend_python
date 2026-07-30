import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class LstmSynthesisParams(BaseModel):
    n_samples: int = Field(default=2000, ge=500, le=10_000)
    time_step: float = Field(default=50 / 1999, gt=0, le=1)
    trend_slope: float = Field(default=0.5, ge=-10, le=10)
    primary_amplitude: float = Field(default=2, ge=0, le=20)
    primary_frequency: float = Field(default=1, gt=0, le=20)
    secondary_amplitude: float = Field(default=1, ge=0, le=20)
    secondary_frequency: float = Field(default=0.5, gt=0, le=20)
    noise_std: float = Field(default=0.3, ge=0, le=10)
    seed: int = Field(default=42, ge=0, le=2_147_483_647)


class LstmModelParams(BaseModel):
    sequence_length: int = Field(default=150, ge=10, le=1000)
    hidden_size: int = Field(default=64, ge=8, le=512)
    num_layers: int = Field(default=2, ge=1, le=5)
    dropout: float = Field(default=0.2, ge=0, lt=1)


class LstmTrainingParams(BaseModel):
    epochs: int = Field(default=30, ge=1, le=300)
    batch_size: int = Field(default=32, ge=1, le=512)
    learning_rate: float = Field(default=1e-3, gt=0, le=0.1)
    train_ratio: float = Field(default=0.8, ge=0.5, le=0.9)
    device: Literal["auto", "cpu", "cuda"] = "auto"


class LstmTrainRequest(BaseModel):
    synthesis: LstmSynthesisParams = Field(default_factory=LstmSynthesisParams)
    model: LstmModelParams = Field(default_factory=LstmModelParams)
    training: LstmTrainingParams = Field(default_factory=LstmTrainingParams)
    forecast_horizon: int = Field(default=100, ge=1, le=500)

    @model_validator(mode="after")
    def validate_window_sizes(self):
        train_size = int(self.synthesis.n_samples * self.training.train_ratio)
        if self.model.sequence_length + self.forecast_horizon > train_size:
            raise ValueError("训练区间不足以容纳输入窗口和预测窗口")

        validation_size = self.synthesis.n_samples - train_size
        if self.forecast_horizon > validation_size:
            raise ValueError("验证区间长度不能小于预测步数")
        return self


class LstmTrainingMetrics(BaseModel):
    final_train_loss: float
    final_validation_loss: float
    best_validation_loss: float
    forecast_mae: float
    forecast_rmse: float
    training_seconds: float
    device: str


class LstmResultLinks(BaseModel):
    image: str
    csv: str
    excel: str


class LstmTrainResult(BaseModel):
    result_id: uuid.UUID
    created_at: datetime
    metrics: LstmTrainingMetrics
    links: LstmResultLinks


class LstmTrainEnvelope(BaseModel):
    message: str = "success"
    code: int = 200
    data: LstmTrainResult


class LstmParamNode(BaseModel):
    name: str
    desc: str
    type: str
    value: int | float | str | bool | None = None
    minimum: int | float | None = None
    maximum: int | float | None = None
    options: list[str] | None = None
    sub_nodes: list["LstmParamNode"] | None = None
