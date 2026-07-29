import uuid
from urllib.parse import quote

from fastapi import HTTPException, Response, status

from app.models.lstm import (
    LstmParamNode,
    LstmResultLinks,
    LstmTrainEnvelope,
    LstmTrainingMetrics,
    LstmTrainRequest,
    LstmTrainResult,
)
from app.services import lstmServ
from app.utils.auth import UserDep

from .router import router as demo_router


@demo_router.get("/lstm/param-list", summary="获取 LSTM demo 支持的参数")
def get_demo_param_list(current_user: UserDep):
    return {
        "message": "success",
        "code": 200,
        "data": [
            LstmParamNode(
                name="synthesis",
                desc="合成时间序列参数",
                type="group",
                sub_nodes=[
                    LstmParamNode(
                        name="n_samples",
                        desc="样本数量",
                        type="integer",
                        value=2000,
                        minimum=500,
                        maximum=10_000,
                    ),
                    LstmParamNode(
                        name="time_step",
                        desc="时间步长",
                        type="number",
                        value=50 / 1999,
                        minimum=0,
                        maximum=1,
                    ),
                    LstmParamNode(
                        name="trend_slope",
                        desc="线性趋势斜率",
                        type="number",
                        value=0.5,
                        minimum=-10,
                        maximum=10,
                    ),
                    LstmParamNode(
                        name="primary_amplitude",
                        desc="主周期振幅",
                        type="number",
                        value=2,
                        minimum=0,
                        maximum=20,
                    ),
                    LstmParamNode(
                        name="primary_frequency",
                        desc="主周期频率",
                        type="number",
                        value=1,
                        minimum=0,
                        maximum=20,
                    ),
                    LstmParamNode(
                        name="secondary_amplitude",
                        desc="次周期振幅",
                        type="number",
                        value=1,
                        minimum=0,
                        maximum=20,
                    ),
                    LstmParamNode(
                        name="secondary_frequency",
                        desc="次周期频率",
                        type="number",
                        value=0.5,
                        minimum=0,
                        maximum=20,
                    ),
                    LstmParamNode(
                        name="noise_std",
                        desc="高斯噪声标准差",
                        type="number",
                        value=0.3,
                        minimum=0,
                        maximum=10,
                    ),
                    LstmParamNode(
                        name="seed",
                        desc="随机种子",
                        type="integer",
                        value=42,
                        minimum=0,
                        maximum=2_147_483_647,
                    ),
                ],
            ),
            LstmParamNode(
                name="model",
                desc="LSTM 模型参数",
                type="group",
                sub_nodes=[
                    LstmParamNode(
                        name="sequence_length",
                        desc="历史输入窗口长度",
                        type="integer",
                        value=150,
                        minimum=10,
                        maximum=1000,
                    ),
                    LstmParamNode(
                        name="hidden_size",
                        desc="隐藏层维度",
                        type="integer",
                        value=64,
                        minimum=8,
                        maximum=512,
                    ),
                    LstmParamNode(
                        name="num_layers",
                        desc="LSTM 层数",
                        type="integer",
                        value=2,
                        minimum=1,
                        maximum=5,
                    ),
                    LstmParamNode(
                        name="dropout",
                        desc="层间 Dropout",
                        type="number",
                        value=0.2,
                        minimum=0,
                        maximum=1,
                    ),
                ],
            ),
            LstmParamNode(
                name="training",
                desc="训练参数",
                type="group",
                sub_nodes=[
                    LstmParamNode(
                        name="epochs",
                        desc="训练轮数",
                        type="integer",
                        value=30,
                        minimum=1,
                        maximum=300,
                    ),
                    LstmParamNode(
                        name="batch_size",
                        desc="批大小",
                        type="integer",
                        value=32,
                        minimum=1,
                        maximum=512,
                    ),
                    LstmParamNode(
                        name="learning_rate",
                        desc="学习率",
                        type="number",
                        value=1e-3,
                        minimum=0,
                        maximum=0.1,
                    ),
                    LstmParamNode(
                        name="train_ratio",
                        desc="训练集比例",
                        type="number",
                        value=0.8,
                        minimum=0.5,
                        maximum=0.9,
                    ),
                    LstmParamNode(
                        name="device",
                        desc="训练设备",
                        type="select",
                        value="auto",
                        options=["auto", "cpu", "cuda"],
                    ),
                ],
            ),
            LstmParamNode(
                name="forecast_horizon",
                desc="直接预测步数",
                type="integer",
                value=100,
                minimum=1,
                maximum=500,
            ),
        ],
    }


@demo_router.post(
    "/lstm/train",
    summary="训练 LSTM 并生成预测结果",
    response_model=LstmTrainEnvelope,
)
async def train_lstm(request: LstmTrainRequest, current_user: UserDep):
    try:
        result = await lstmServ.train_and_store(request, current_user.id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    result_id = result.id
    return LstmTrainEnvelope(
        data=LstmTrainResult(
            result_id=result_id,
            created_at=result.create_time,
            metrics=LstmTrainingMetrics.model_validate(result.metrics),
            links=LstmResultLinks(
                image=f"/demo/lstm/results/{result_id}/image",
                csv=f"/demo/lstm/results/{result_id}/csv",
                excel=f"/demo/lstm/results/{result_id}/excel",
            ),
        )
    )


def _get_result_or_404(result_id: uuid.UUID, current_user: UserDep):
    result = lstmServ.get_result(result_id, current_user.id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LSTM result not found",
        )
    return result


@demo_router.get("/lstm/results/{result_id}/image", summary="预览 LSTM 预测结果图")
def get_lstm_result_image(result_id: uuid.UUID, current_user: UserDep):
    result = _get_result_or_404(result_id, current_user)
    filename = quote(f"lstm-{result_id}.png")
    return Response(
        content=lstmServ.render_result_image(result),
        media_type="image/png",
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{filename}"},
    )


@demo_router.get("/lstm/results/{result_id}/csv", summary="下载 LSTM 预测 CSV")
def download_lstm_result_csv(result_id: uuid.UUID, current_user: UserDep):
    result = _get_result_or_404(result_id, current_user)
    filename = quote(f"lstm-{result_id}.csv")
    return Response(
        content=lstmServ.export_result_csv(result),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@demo_router.get("/lstm/results/{result_id}/excel", summary="下载 LSTM 预测 Excel")
def download_lstm_result_excel(result_id: uuid.UUID, current_user: UserDep):
    result = _get_result_or_404(result_id, current_user)
    filename = quote(f"lstm-{result_id}.xlsx")
    return Response(
        content=lstmServ.export_result_excel(result),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )
