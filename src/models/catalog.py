from typing import Any

from pydantic import BaseModel, Field


class QueryParam(BaseModel):
    name: str
    example: str | None = None


class Endpoint(BaseModel):
    id: str
    method: str
    host: str
    path_template: str
    calls: int
    first_step: int
    statuses: list[int]
    avg_ms: float
    request_content_type: str | None = None
    auth_schemes: list[str] = Field(default_factory=list)
    query_params: list[QueryParam] = Field(default_factory=list)
    request_headers: dict[str, str] = Field(default_factory=dict)
    request_schema: dict[str, Any] | None = None
    response_schema: dict[str, Any] | None = None
    request_example: Any = None
    response_example: Any = None


class FlowStep(BaseModel):
    index: int
    started: str
    endpoint_id: str
    method: str
    host: str
    path_template: str
    status: int
    duration_ms: float


class Dependency(BaseModel):
    """Um valor produzido por uma resposta e reutilizado num request posterior.

    O valor em si nunca é armazenado — apenas onde nasce e onde é consumido.
    """

    from_endpoint: str
    from_location: str
    to_endpoint: str
    to_location: str
    first_from_step: int
    first_to_step: int
    occurrences: int = 1
    value_kind: str
    sensitive: bool


class Catalog(BaseModel):
    source_har: str
    generated_at: str
    total_entries: int
    api_entries: int
    endpoints: list[Endpoint]
    flow: list[FlowStep]
    dependencies: list[Dependency]
