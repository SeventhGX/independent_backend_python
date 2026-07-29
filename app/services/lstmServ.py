import asyncio
import csv
import io
import threading
import time as time_module
import uuid
from collections.abc import Sized
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast

import numpy as np
import torch
from matplotlib.figure import Figure
from openpyxl import Workbook
from torch import nn
from torch.utils.data import DataLoader, Dataset

from app.models.lstm import LstmTrainingMetrics, LstmTrainRequest

RESULT_TTL = timedelta(hours=1)
MAX_CACHED_RESULTS = 20


@dataclass(slots=True)
class LstmResultArtifacts:
    result_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    expires_at: datetime
    metrics: LstmTrainingMetrics
    image: bytes
    csv: bytes
    excel: bytes


class TimeSeriesDataset(Dataset):
    def __init__(self, features, data, sequence_length, horizon):
        self.features = features
        self.data = data
        self.sequence_length = sequence_length
        self.horizon = horizon

    def __len__(self):
        return len(self.data) - self.sequence_length - self.horizon + 1

    def __getitem__(self, index):
        target_start = index + self.sequence_length
        target_end = target_start + self.horizon
        history = self.features[index:target_start]
        future_time_features = self.features[target_start:target_end, 1:]
        changes = self.data[target_start:target_end] - self.data[target_start - 1]
        return (
            torch.from_numpy(history),
            torch.from_numpy(future_time_features),
            torch.from_numpy(changes.astype(np.float32)),
        )


class LstmPredictor(nn.Module):
    def __init__(
        self,
        input_size: int,
        hidden_size: int,
        num_layers: int,
        dropout: float,
        future_feature_size: int,
    ):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )
        self.head = nn.Sequential(
            nn.Linear(hidden_size + future_feature_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, 1),
        )

    def forward(self, history, future_time_features):
        output, _ = self.lstm(history)
        context = output[:, -1, :]
        horizon = future_time_features.size(1)
        repeated_context = context.unsqueeze(1).expand(-1, horizon, -1)
        decoder_input = torch.cat((repeated_context, future_time_features), dim=-1)
        return self.head(decoder_input).squeeze(-1)


_results: dict[uuid.UUID, LstmResultArtifacts] = {}
_results_lock = threading.Lock()
_training_semaphore = asyncio.Semaphore(1)


def _build_time_features(time_values: np.ndarray, time_scale: float) -> np.ndarray:
    return np.column_stack(
        (
            time_values / time_scale,
            np.sin(time_values),
            np.cos(time_values),
        )
    ).astype(np.float32)


def _build_features(
    normalized_data: np.ndarray,
    time_values: np.ndarray,
    time_scale: float,
) -> np.ndarray:
    return np.column_stack(
        (normalized_data, _build_time_features(time_values, time_scale))
    ).astype(np.float32)


def _series_values(
    time_values: np.ndarray,
    request: LstmTrainRequest,
    noise: np.ndarray,
) -> np.ndarray:
    params = request.synthesis
    trend = params.trend_slope * time_values
    primary = params.primary_amplitude * np.sin(params.primary_frequency * time_values)
    secondary = params.secondary_amplitude * np.sin(
        params.secondary_frequency * time_values
    )
    return trend + primary + secondary + noise


def _resolve_device(requested_device: str) -> torch.device:
    if requested_device == "cuda":
        if not torch.cuda.is_available():
            raise ValueError("当前服务环境不支持 CUDA")
        return torch.device("cuda")
    if requested_device == "auto" and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def _train_model(
    model: LstmPredictor,
    train_loader: DataLoader,
    validation_loader: DataLoader,
    request: LstmTrainRequest,
    device: torch.device,
) -> tuple[list[float], list[float]]:
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=request.training.learning_rate)

    train_losses: list[float] = []
    validation_losses: list[float] = []
    for _ in range(request.training.epochs):
        model.train()
        train_total = 0.0
        for history, future_time, target in train_loader:
            history = history.to(device)
            future_time = future_time.to(device)
            target = target.to(device)
            optimizer.zero_grad()
            prediction = model(history, future_time)
            loss = criterion(prediction, target)
            loss.backward()
            optimizer.step()
            train_total += loss.item() * history.size(0)
        train_sample_count = len(cast(Sized, train_loader.dataset))
        train_losses.append(train_total / train_sample_count)

        model.eval()
        validation_total = 0.0
        with torch.no_grad():
            for history, future_time, target in validation_loader:
                history = history.to(device)
                future_time = future_time.to(device)
                target = target.to(device)
                prediction = model(history, future_time)
                validation_total += criterion(prediction, target).item() * history.size(
                    0
                )
        validation_sample_count = len(cast(Sized, validation_loader.dataset))
        validation_losses.append(validation_total / validation_sample_count)

    return train_losses, validation_losses


@torch.no_grad()
def _predict_future(
    model: LstmPredictor,
    features: np.ndarray,
    normalized_data: np.ndarray,
    future_time: np.ndarray,
    time_scale: float,
    sequence_length: int,
    device: torch.device,
) -> np.ndarray:
    model.eval()
    history = torch.from_numpy(features[-sequence_length:]).unsqueeze(0).to(device)
    future_features = (
        torch.from_numpy(_build_time_features(future_time, time_scale))
        .unsqueeze(0)
        .to(device)
    )
    changes = model(history, future_features).squeeze(0).cpu().numpy()
    return normalized_data[-1] + changes


def _render_image(
    observed_time: np.ndarray,
    observed: np.ndarray,
    future_time: np.ndarray,
    forecast: np.ndarray,
    expected: np.ndarray,
    train_losses: list[float],
    validation_losses: list[float],
) -> bytes:
    figure = Figure(figsize=(14, 8), constrained_layout=True)
    loss_axis, forecast_axis = figure.subplots(2, 1)

    epochs = np.arange(1, len(train_losses) + 1)
    loss_axis.plot(epochs, train_losses, label="Train loss")
    loss_axis.plot(epochs, validation_losses, label="Validation loss")
    loss_axis.set(title="Training history", xlabel="Epoch", ylabel="MSE loss")
    loss_axis.grid(alpha=0.3)
    loss_axis.legend()

    forecast_axis.plot(observed_time, observed, label="Observed", alpha=0.8)
    forecast_axis.plot(future_time, expected, label="Expected future", linestyle="--")
    forecast_axis.plot(future_time, forecast, label="Forecast", linewidth=2)
    forecast_axis.axvline(observed_time[-1], color="gray", linestyle=":")
    forecast_axis.set(
        title="LSTM direct multi-step forecast",
        xlabel="Time",
        ylabel="Value",
    )
    forecast_axis.grid(alpha=0.3)
    forecast_axis.legend()

    output = io.BytesIO()
    figure.savefig(output, format="png", dpi=150)
    return output.getvalue()


def _build_csv(
    observed_time: np.ndarray,
    observed: np.ndarray,
    future_time: np.ndarray,
    forecast: np.ndarray,
    expected: np.ndarray,
) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(("step", "time", "series", "value"))
    for step, (time_value, value) in enumerate(
        zip(observed_time, observed, strict=True)
    ):
        writer.writerow((step, float(time_value), "observed", float(value)))
    offset = len(observed)
    for step, (time_value, predicted, actual) in enumerate(
        zip(future_time, forecast, expected, strict=True), start=offset
    ):
        writer.writerow((step, float(time_value), "forecast", float(predicted)))
        writer.writerow((step, float(time_value), "expected", float(actual)))
    return output.getvalue().encode("utf-8-sig")


def _build_excel(
    observed_time: np.ndarray,
    observed: np.ndarray,
    future_time: np.ndarray,
    forecast: np.ndarray,
    expected: np.ndarray,
    train_losses: list[float],
    validation_losses: list[float],
    request: LstmTrainRequest,
) -> bytes:
    workbook = Workbook()
    series_sheet = workbook.active
    if series_sheet is None:
        series_sheet = workbook.create_sheet()
    series_sheet.title = "series"
    series_sheet.append(("step", "time", "series", "value"))
    for step, (time_value, value) in enumerate(
        zip(observed_time, observed, strict=True)
    ):
        series_sheet.append((step, float(time_value), "observed", float(value)))
    offset = len(observed)
    for step, (time_value, predicted, actual) in enumerate(
        zip(future_time, forecast, expected, strict=True), start=offset
    ):
        series_sheet.append((step, float(time_value), "forecast", float(predicted)))
        series_sheet.append((step, float(time_value), "expected", float(actual)))

    loss_sheet = workbook.create_sheet("losses")
    loss_sheet.append(("epoch", "train_loss", "validation_loss"))
    for epoch, (train_loss, validation_loss) in enumerate(
        zip(train_losses, validation_losses, strict=True), start=1
    ):
        loss_sheet.append((epoch, train_loss, validation_loss))

    params_sheet = workbook.create_sheet("parameters")
    params_sheet.append(("group", "name", "value"))
    request_data = request.model_dump()
    for group, values in request_data.items():
        if isinstance(values, dict):
            for name, value in values.items():
                params_sheet.append((group, name, value))
        else:
            params_sheet.append(("forecast", group, values))

    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def _cleanup_results(now: datetime) -> None:
    expired_ids = [
        result_id for result_id, result in _results.items() if result.expires_at <= now
    ]
    for result_id in expired_ids:
        del _results[result_id]


def _store_result(result: LstmResultArtifacts) -> None:
    with _results_lock:
        _cleanup_results(result.created_at)
        if len(_results) >= MAX_CACHED_RESULTS:
            oldest_id = min(_results, key=lambda key: _results[key].created_at)
            del _results[oldest_id]
        _results[result.result_id] = result


def get_result(
    result_id: uuid.UUID,
    user_id: uuid.UUID,
) -> LstmResultArtifacts | None:
    with _results_lock:
        _cleanup_results(datetime.now(UTC))
        result = _results.get(result_id)
        if result is None or result.user_id != user_id:
            return None
        return result


def _train_and_store_sync(
    request: LstmTrainRequest,
    user_id: uuid.UUID,
) -> LstmResultArtifacts:
    synthesis = request.synthesis
    model_params = request.model
    training = request.training
    device = _resolve_device(training.device)

    rng = np.random.default_rng(synthesis.seed)
    torch.manual_seed(synthesis.seed)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(synthesis.seed)

    observed_time = np.arange(synthesis.n_samples) * synthesis.time_step
    observed_noise = rng.normal(0, synthesis.noise_std, synthesis.n_samples)
    observed = _series_values(observed_time, request, observed_noise)
    split = int(synthesis.n_samples * training.train_ratio)
    data_min = float(observed[:split].min())
    data_range = float(observed[:split].max() - data_min)
    if data_range <= np.finfo(np.float32).eps:
        data_range = 1.0
    normalized_data = (observed - data_min) / data_range
    time_scale = float(observed_time[split - 1])
    features = _build_features(normalized_data, observed_time, time_scale)

    train_dataset = TimeSeriesDataset(
        features[:split],
        normalized_data[:split],
        model_params.sequence_length,
        request.forecast_horizon,
    )
    validation_start = split - model_params.sequence_length
    validation_dataset = TimeSeriesDataset(
        features[validation_start:],
        normalized_data[validation_start:],
        model_params.sequence_length,
        request.forecast_horizon,
    )
    generator = torch.Generator().manual_seed(synthesis.seed)
    train_loader = DataLoader(
        train_dataset,
        batch_size=training.batch_size,
        shuffle=True,
        generator=generator,
    )
    validation_loader = DataLoader(
        validation_dataset,
        batch_size=training.batch_size,
        shuffle=False,
    )

    model = LstmPredictor(
        input_size=features.shape[1],
        hidden_size=model_params.hidden_size,
        num_layers=model_params.num_layers,
        dropout=model_params.dropout,
        future_feature_size=features.shape[1] - 1,
    ).to(device)
    training_started = time_module.perf_counter()
    train_losses, validation_losses = _train_model(
        model, train_loader, validation_loader, request, device
    )
    training_seconds = time_module.perf_counter() - training_started

    future_time = observed_time[-1] + synthesis.time_step * np.arange(
        1, request.forecast_horizon + 1
    )
    forecast_normalized = _predict_future(
        model,
        features,
        normalized_data,
        future_time,
        time_scale,
        model_params.sequence_length,
        device,
    )
    forecast = forecast_normalized * data_range + data_min
    future_noise = rng.normal(0, synthesis.noise_std, request.forecast_horizon)
    expected = _series_values(future_time, request, future_noise)

    errors = forecast - expected
    metrics = LstmTrainingMetrics(
        final_train_loss=train_losses[-1],
        final_validation_loss=validation_losses[-1],
        best_validation_loss=min(validation_losses),
        forecast_mae=float(np.mean(np.abs(errors))),
        forecast_rmse=float(np.sqrt(np.mean(np.square(errors)))),
        training_seconds=training_seconds,
        device=str(device),
    )
    created_at = datetime.now(UTC)
    result = LstmResultArtifacts(
        result_id=uuid.uuid4(),
        user_id=user_id,
        created_at=created_at,
        expires_at=created_at + RESULT_TTL,
        metrics=metrics,
        image=_render_image(
            observed_time,
            observed,
            future_time,
            forecast,
            expected,
            train_losses,
            validation_losses,
        ),
        csv=_build_csv(observed_time, observed, future_time, forecast, expected),
        excel=_build_excel(
            observed_time,
            observed,
            future_time,
            forecast,
            expected,
            train_losses,
            validation_losses,
            request,
        ),
    )
    _store_result(result)
    return result


async def train_and_store(
    request: LstmTrainRequest,
    user_id: uuid.UUID,
) -> LstmResultArtifacts:
    async with _training_semaphore:
        return await asyncio.to_thread(_train_and_store_sync, request, user_id)
