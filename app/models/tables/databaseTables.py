import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, LargeBinary, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

DEFAULT_ADMIN_USER_CODE = "00000000"


class Article(SQLModel, table=True):
    """
    新闻文章
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str
    url: str
    publish_time: datetime | None = None
    key_words: str | None = None
    summary: str | None = None
    content: str | None = None
    mail_date: date | None = None
    real_mail_date: date | None = None


class Recipient(SQLModel, table=True):
    """
    邮件接收人
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str
    name: str | None = None


class Sys_User(SQLModel, table=True):
    """
    系统用户
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_code: str
    user_name: str
    password: str
    email: str | None = None
    phone: str | None = None
    last_login_time: datetime | None = None
    last_login_ip: str | None = None
    del_flag: bool = False


class Chat_Session(SQLModel, table=True):
    """
    聊天会话
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID
    session_name: str
    create_time: datetime | None = Field(default_factory=datetime.now)
    content: dict = Field(default=None, sa_column=Column(JSONB, nullable=True))


class Chat_Model(SQLModel, table=True):
    """
    聊天模型
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    model_type: str
    model: str
    # sdk_type: str
    description: str | None = None
    del_flag: bool = False


class Chat_Model_V2(SQLModel, table=True):
    """
    聊天模型 V2
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    model_type: str
    model: str
    key_name: str
    sdk_type: str
    base_url: str
    kwargs: dict = Field(default=None, sa_column=Column(JSONB, nullable=True))
    description: str | None = None
    del_flag: bool = False


class User_Model_Cfg(SQLModel, table=True):
    """
    用户模型参数配置
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID
    model_v2_id: uuid.UUID
    cfg: dict = Field(default=None, sa_column=Column(JSONB, nullable=True))


class File(SQLModel, table=True):
    """
    文件表，主要保存聊天记录中的图片与知识库中用户上传的知识文件
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    source_url: str | None = None
    filename: str | None = None
    file_type: str | None = None
    data: bytes = Field(sa_column=Column(LargeBinary, nullable=False))


class Knowledge(SQLModel, table=True):
    """
    知识库，记录用户上传的知识文件信息
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID
    file_id: uuid.UUID
    is_embedded: bool = False
    create_time: datetime | None = Field(default_factory=datetime.now)


class KnowledgeTag(SQLModel, table=True):
    """
    用户级知识库标签
    """

    __table_args__ = (
        UniqueConstraint("user_id", "normalized_name", name="uq_knowledge_tag_user_name"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(index=True)
    name: str = Field(max_length=50)
    normalized_name: str = Field(max_length=50)
    create_time: datetime = Field(default_factory=datetime.now)


class KnowledgeTagLink(SQLModel, table=True):
    """
    知识文件与标签的多对多关联
    """

    knowledge_id: uuid.UUID = Field(primary_key=True)
    tag_id: uuid.UUID = Field(primary_key=True)


class Chunks(SQLModel, table=True):
    """
    知识文件切片
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    file_id: uuid.UUID
    chunk_index: int
    meta_data: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    content: str
    embedding: list[float] | None = Field(default=None, sa_column=Column(Vector(1024), nullable=True))


class Docs(SQLModel, table=True):
    """
    教程文档
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    docs_name: str
    docs_desc: str | None = None
    content: str
    create_time: datetime | None = Field(default_factory=datetime.now)
    update_time: datetime | None = Field(default_factory=datetime.now)


class DocsImage(SQLModel, table=True):
    """
    教程文档涉及的图床
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    docs_id: uuid.UUID | None = None
    image_name: str
    image_desc: str | None = None
    image_data: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    create_time: datetime | None = Field(default_factory=datetime.now)
    create_by: uuid.UUID | None = None


class LstmResult(SQLModel, table=True):
    """LSTM demo 的训练参数、损失与预测数据。"""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(index=True)
    dataset_params: dict = Field(sa_column=Column(JSONB, nullable=False))
    model_params: dict = Field(sa_column=Column(JSONB, nullable=False))
    training_params: dict = Field(sa_column=Column(JSONB, nullable=False))
    metrics: dict = Field(sa_column=Column(JSONB, nullable=False))
    train_losses: list[float] = Field(sa_column=Column(JSONB, nullable=False))
    validation_losses: list[float] = Field(sa_column=Column(JSONB, nullable=False))
    observed_time: list[float] = Field(sa_column=Column(JSONB, nullable=False))
    observed_data: list[float] = Field(sa_column=Column(JSONB, nullable=False))
    future_time: list[float] = Field(sa_column=Column(JSONB, nullable=False))
    forecast_data: list[float] = Field(sa_column=Column(JSONB, nullable=False))
    expected_data: list[float] = Field(sa_column=Column(JSONB, nullable=False))
    create_time: datetime = Field(default_factory=datetime.now)


class IsolationForestResult(SQLModel, table=True):
    """Isolation Forest demo 的参数、指标与检测数据。"""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(index=True)
    dataset_params: dict = Field(sa_column=Column(JSONB, nullable=False))
    model_params: dict = Field(sa_column=Column(JSONB, nullable=False))
    metrics: dict = Field(sa_column=Column(JSONB, nullable=False))
    x_values: list[float] = Field(sa_column=Column(JSONB, nullable=False))
    y_values: list[float] = Field(sa_column=Column(JSONB, nullable=False))
    actual_labels: list[int] = Field(sa_column=Column(JSONB, nullable=False))
    predicted_labels: list[int] = Field(sa_column=Column(JSONB, nullable=False))
    anomaly_scores: list[float] = Field(sa_column=Column(JSONB, nullable=False))
    create_time: datetime = Field(default_factory=datetime.now)


class KMeansResult(SQLModel, table=True):
    """K-Means demo 的参数、指标、聚类数据与肘部法则曲线。"""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(index=True)
    dataset_params: dict = Field(sa_column=Column(JSONB, nullable=False))
    model_params: dict = Field(sa_column=Column(JSONB, nullable=False))
    evaluation_params: dict = Field(sa_column=Column(JSONB, nullable=False))
    metrics: dict = Field(sa_column=Column(JSONB, nullable=False))
    x_values: list[float] = Field(sa_column=Column(JSONB, nullable=False))
    y_values: list[float] = Field(sa_column=Column(JSONB, nullable=False))
    true_labels: list[int] = Field(sa_column=Column(JSONB, nullable=False))
    cluster_labels: list[int] = Field(sa_column=Column(JSONB, nullable=False))
    center_distances: list[float] = Field(sa_column=Column(JSONB, nullable=False))
    center_x_values: list[float] = Field(sa_column=Column(JSONB, nullable=False))
    center_y_values: list[float] = Field(sa_column=Column(JSONB, nullable=False))
    elbow_k_values: list[int] = Field(sa_column=Column(JSONB, nullable=False))
    elbow_inertias: list[float] = Field(sa_column=Column(JSONB, nullable=False))
    elbow_silhouettes: list[float] = Field(sa_column=Column(JSONB, nullable=False))
    create_time: datetime = Field(default_factory=datetime.now)


class AStarResult(SQLModel, table=True):
    """A* demo 的原始图、探索过程与最短路径结果。"""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(index=True)
    graph: dict = Field(sa_column=Column(JSONB, nullable=False))
    start_id: str
    goal_id: str
    start_to_goal_distance: float
    path: list[str] = Field(sa_column=Column(JSONB, nullable=False))
    path_edge_ids: list[str] = Field(sa_column=Column(JSONB, nullable=False))
    steps: list[dict] = Field(sa_column=Column(JSONB, nullable=False))
    metrics: dict = Field(sa_column=Column(JSONB, nullable=False))
    create_time: datetime = Field(default_factory=datetime.now)
