from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.agent_graph import get_agent_trace, run_agent
from app.auth import get_current_user
from app.error_handling import operation_errors


router = APIRouter(
    prefix="/agent",
    tags=["agent"],
    dependencies=[Depends(get_current_user)],
)


class AgentQueryRequest(BaseModel):
    question: str = Field(max_length=4000)


class AgentQueryResponse(BaseModel):
    thread_id: str
    answer: str
    trace: list[dict[str, Any]]
    checkpoint: dict[str, Any]


class AgentTraceResponse(AgentQueryResponse):
    created_at: str


@router.post("/query", response_model=AgentQueryResponse)
def query_agent(
    payload: AgentQueryRequest,
    current_user=Depends(get_current_user),
):
    with operation_errors():
        return run_agent(payload.question, current_user.doc_id)


@router.get("/traces/{thread_id}", response_model=AgentTraceResponse)
def read_agent_trace(
    thread_id: str,
    current_user=Depends(get_current_user),
):
    with operation_errors():
        trace = get_agent_trace(thread_id, current_user.doc_id)
        if trace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trace no encontrado.",
            )
        return trace