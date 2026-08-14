import uuid
from urllib.parse import quote

from fastapi import HTTPException, Response, status

from app.models.astar import (
	AStarMetrics,
	AStarResultLinks,
	AStarSolveEnvelope,
	AStarSolveRequest,
	AStarSolveResult,
	AStarStep,
)
from app.models.tables.databaseTables import AStarResult
from app.services import astarServ
from app.utils.auth import UserDep

from .router import router as demo_router


def _build_solve_result(result: AStarResult) -> AStarSolveEnvelope:
	result_id = result.id
	return AStarSolveEnvelope(
		data=AStarSolveResult(
			result_id=result_id,
			created_at=result.create_time,
			start_to_goal_distance=result.start_to_goal_distance,
			path=result.path,
			path_edge_ids=result.path_edge_ids,
			steps=[AStarStep.model_validate(step) for step in result.steps],
			metrics=AStarMetrics.model_validate(result.metrics),
			links=AStarResultLinks(
				csv=f"/demo/astar/results/{result_id}/csv",
				excel=f"/demo/astar/results/{result_id}/excel",
			),
		)
	)


@demo_router.post(
	"/astar/solve",
	summary="使用 A* 搜索前端提交的图网络",
	response_model=AStarSolveEnvelope,
)
async def solve_graph(request: AStarSolveRequest, current_user: UserDep):
	result = await astarServ.solve_and_store(request, current_user.id)
	return _build_solve_result(result)


def _get_result_or_404(result_id: uuid.UUID, current_user: UserDep) -> AStarResult:
	result = astarServ.get_result(result_id, current_user.id)
	if result is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="A* result not found",
		)
	return result


@demo_router.get("/astar/results/{result_id}/csv", summary="下载 A* 图网络与求解结果 CSV")
def download_astar_result_csv(result_id: uuid.UUID, current_user: UserDep):
	result = _get_result_or_404(result_id, current_user)
	filename = quote(f"astar-{result_id}.csv")
	return Response(
		content=astarServ.export_result_csv(result),
		media_type="text/csv; charset=utf-8",
		headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
	)


@demo_router.get("/astar/results/{result_id}/excel", summary="下载 A* 图网络与求解结果 Excel")
def download_astar_result_excel(result_id: uuid.UUID, current_user: UserDep):
	result = _get_result_or_404(result_id, current_user)
	filename = quote(f"astar-{result_id}.xlsx")
	return Response(
		content=astarServ.export_result_excel(result),
		media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
		headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
	)
