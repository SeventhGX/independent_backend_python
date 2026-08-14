import math
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AStarNode(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    id: str = Field(min_length=1, max_length=100)
    x: float
    y: float
    label: str | None = Field(default=None, max_length=200)


class AStarEdge(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    id: str | None = Field(default=None, min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=100)
    target: str = Field(min_length=1, max_length=100)
    weight: float | None = Field(default=None, gt=0)


class AStarSolveRequest(BaseModel):
    nodes: list[AStarNode] = Field(min_length=1, max_length=1000)
    edges: list[AStarEdge] = Field(default_factory=list, max_length=10_000)
    start_id: str
    goal_id: str
    directed: bool = False
    start_to_goal_distance: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_graph(self):
        node_by_id = {node.id: node for node in self.nodes}
        if len(node_by_id) != len(self.nodes):
            raise ValueError("节点 id 必须唯一")
        if self.start_id not in node_by_id:
            raise ValueError("起点必须存在于点集中")
        if self.goal_id not in node_by_id:
            raise ValueError("终点必须存在于点集中")

        edge_ids = [edge.id for edge in self.edges if edge.id is not None]
        if len(set(edge_ids)) != len(edge_ids):
            raise ValueError("边 id 必须唯一")
        for edge in self.edges:
            if edge.source not in node_by_id or edge.target not in node_by_id:
                raise ValueError("边的端点必须存在于点集中")
            if edge.source == edge.target:
                raise ValueError("不支持自环边")
            source = node_by_id[edge.source]
            target = node_by_id[edge.target]
            if edge.weight is None and math.hypot(source.x - target.x, source.y - target.y) == 0:
                raise ValueError("坐标重合的节点之间必须提供正边权")

        start = node_by_id[self.start_id]
        goal = node_by_id[self.goal_id]
        calculated_distance = math.hypot(start.x - goal.x, start.y - goal.y)
        if self.start_to_goal_distance is not None and not math.isclose(
            self.start_to_goal_distance,
            calculated_distance,
            rel_tol=1e-6,
            abs_tol=1e-6,
        ):
            raise ValueError("起点到终点的欧几里得距离与节点坐标不一致")
        return self


class AStarOpenNode(BaseModel):
    node_id: str
    g: float
    h: float
    f: float
    parent_id: str | None = None


class AStarNeighborEvaluation(BaseModel):
    edge_id: str
    node_id: str
    edge_weight: float
    tentative_g: float
    previous_g: float | None = None
    accepted: bool


class AStarStep(BaseModel):
    iteration: int
    current_id: str
    open_set: list[AStarOpenNode]
    closed_set: list[str]
    neighbors: list[AStarNeighborEvaluation]


class AStarMetrics(BaseModel):
    found: bool
    path_cost: float | None
    path_euclidean_distance: float | None
    heuristic_scale: float
    explored_nodes: int
    step_count: int
    node_count: int
    edge_count: int
    solve_seconds: float


class AStarResultLinks(BaseModel):
    csv: str
    excel: str


class AStarSolveResult(BaseModel):
    result_id: uuid.UUID
    created_at: datetime
    start_to_goal_distance: float
    path: list[str]
    path_edge_ids: list[str]
    steps: list[AStarStep]
    metrics: AStarMetrics
    links: AStarResultLinks


class AStarSolveEnvelope(BaseModel):
    message: str = "success"
    code: int = 200
    data: AStarSolveResult