from typing import Any, Dict, Optional, List, Literal, Union
from pydantic import BaseModel, Field, conlist, ConfigDict

class ProcessRequest(BaseModel):
    data: str = Field(..., min_length=1, max_length=10000, description="Data to process")
    pool_id: Optional[str] = Field(None, description="Optional pool ID")


class ProcessResponse(BaseModel):
    input_id: str
    output_id: str
    result: Any
    processing_time: float
    pool_used: str


class StatusResponse(BaseModel):
    system_id: str
    total_pools: int
    total_processors: int
    total_executions: int
    pool_status: Dict[str, Dict[str, Any]]
    global_bridges: int
    log_entries: int
    platform: str


class StressRequest(BaseModel):
    iterations: int = Field(..., ge=1, le=10000, description="Number of iterations")
    concurrent: int = Field(..., ge=1, le=100, description="Concurrent workers")
    async_mode: bool = Field(default=False, description="Run asynchronously")


class StressResult(BaseModel):
    iterations: int
    successes: int
    failures: int
    success_rate: float
    total_time: float
    throughput: float
    system_status: Dict[str, Any]


class JobSubmitResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[StressResult] = None
    error: Optional[str] = None


class PoolCreateRequest(BaseModel):
    pool_id: str
    initial_size: int = Field(ge=1, le=100, default=3)


class RebuildRequest(BaseModel):
    default_pools: int = Field(ge=0, le=50, default=2)
    pool_size: int = Field(ge=1, le=100, default=5)


# --- Cognition management ---


class SymbolicRules(BaseModel):
    rules: Dict[str, str]


class SetRulesRequest(BaseModel):
    rules: Dict[str, str]


class MemorySnapshot(BaseModel):
    size: int
    capacity: int
    top_preview: list[str] = Field(default_factory=list)


class PrimeMetrics(BaseModel):
    window: int
    entropy: float
    unique_tokens: int
    token_count: int
    top_tokens: list[tuple[str, int]]


class Suggestions(BaseModel):
    suggestions: list[dict]


# --- Sync / Symbol validation protocol ---


class SyncUpdateRequest(BaseModel):
    agent: str
    state: Dict[str, Any] = Field(default_factory=dict)


class AgentSnapshot(BaseModel):
    agent: str
    timestamp: float
    payload: Dict[str, Any]
    content_signature: tuple[int, int, int, int, int]


class SyncSnapshot(BaseModel):
    session_id: str
    agents: list[str]
    sequence: list[str]
    sequence_validation: Dict[str, Any]
    states: Dict[str, AgentSnapshot]
    events: list[Dict[str, Any]]


class SymbolValidateRequest(BaseModel):
    sequence: list[str]


class SymbolValidateResponse(BaseModel):
    valid: bool
    reason: str


class BootStep(BaseModel):
    symbol: str
    name: str
    index: int


# --- LLM / Chat / Embeddings ---


Role = Literal["system", "user", "assistant", "tool"]

class ChatMessage(BaseModel):
    role: Role
    content: str
    name: Optional[str] = None

class ChatRequest(BaseModel):
    messages: conlist(ChatMessage, min_length=1)
    temperature: Optional[float] = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    response_format: Optional[Dict[str, Any]] = None

class ChoiceMessage(BaseModel):
    role: Role
    content: Optional[str] = None

class ChatChoice(BaseModel):
    index: int
    message: ChoiceMessage
    finish_reason: Optional[str] = None

class ChatResponse(BaseModel):
    id: str
    model: Optional[str] = None
    created: int
    choices: List[ChatChoice]
    usage: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(extra="allow")  # Allow cognitive metadata

class EmbeddingsRequest(BaseModel):
    input: Union[str, List[str]]
    dimensions: Optional[int] = Field(default=None, ge=1, le=8192)

class EmbeddingVector(BaseModel):
    embedding: List[float]
    index: int

class EmbeddingsResponse(BaseModel):
    data: List[EmbeddingVector]
    model: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
