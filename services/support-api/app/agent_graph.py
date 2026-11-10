from __future__ import annotations

from datetime import datetime, timezone
from typing import TypedDict
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from nexova_rag import embed, generate_answer, retrieve, setup


class AgentState(TypedDict, total=False):
    question: str
    retrieved_chunks: list[dict[str, object]]
    answer: str
    error: bool
    trace: list[dict[str, object]]


_knowledge_base = embed(setup())
_trace_store: dict[str, dict[str, object]] = {}


def _append_trace(
    state: AgentState,
    node: str,
    output: dict[str, object],
) -> list[dict[str, object]]:
    return [*state.get("trace", []), {"node": node, "output": output}]


def receive_question(state: AgentState) -> AgentState:
    question = state.get("question", "")
    valid = bool(question.strip())
    return {
        "error": not valid,
        "trace": _append_trace(
            state,
            "receive_question",
            {"valid": valid, "length": len(question)},
        ),
    }


def retrieve_context(state: AgentState) -> AgentState:
    chunks = retrieve(
        state.get("question", ""),
        _knowledge_base,
        threshold=0.24,
    )
    return {
        "retrieved_chunks": chunks,
        "trace": _append_trace(
            state,
            "retrieve",
            {"count": len(chunks), "chunks": chunks},
        ),
    }


def generate_response(state: AgentState) -> AgentState:
    question = state.get("question", "")
    chunks = state.get("retrieved_chunks", [])
    answer = generate_answer(question, chunks)
    return {
        "answer": answer,
        "trace": _append_trace(
            state,
            "generate_answer",
            {"answer": answer},
        ),
    }


def answer_without_context(state: AgentState) -> AgentState:
    answer = "No tengo información suficiente en la base de conocimiento de Nexova."
    return {
        "answer": answer,
        "trace": _append_trace(
            state,
            "no_context",
            {"answer": answer, "reason": "no_matching_context"},
        ),
    }


def reject_empty_question(state: AgentState) -> AgentState:
    answer = "La pregunta no puede estar vacía."
    return {
        "answer": answer,
        "trace": _append_trace(
            state,
            "invalid_question",
            {"answer": answer, "reason": "empty_question"},
        ),
    }


def _route_question(state: AgentState) -> str:
    return "invalid_question" if state.get("error") else "retrieve"


def _route_retrieval(state: AgentState) -> str:
    return "generate_answer" if state.get("retrieved_chunks") else "no_context"


def _compile_agent_graph():
    builder = StateGraph(AgentState)
    builder.add_node("receive_question", receive_question)
    builder.add_node("retrieve", retrieve_context)
    builder.add_node("generate_answer", generate_response)
    builder.add_node("no_context", answer_without_context)
    builder.add_node("invalid_question", reject_empty_question)
    builder.add_edge(START, "receive_question")
    builder.add_conditional_edges(
        "receive_question",
        _route_question,
        {
            "retrieve": "retrieve",
            "invalid_question": "invalid_question",
        },
    )
    builder.add_conditional_edges(
        "retrieve",
        _route_retrieval,
        {
            "generate_answer": "generate_answer",
            "no_context": "no_context",
        },
    )
    builder.add_edge("generate_answer", END)
    builder.add_edge("no_context", END)
    builder.add_edge("invalid_question", END)
    try:
        return builder.compile(checkpointer=MemorySaver())
    except Exception as error:
        raise RuntimeError("No se pudo compilar el grafo del agente Nexova.") from error


agent_graph = _compile_agent_graph()


def run_agent(question: str, owner_id: int) -> dict[str, object]:
    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    state = agent_graph.invoke(
        {"question": question, "trace": []},
        config=config,
    )
    checkpoint = agent_graph.get_state(config)
    trace_record = {
        "thread_id": thread_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "trace": state.get("trace", []),
        "checkpoint": {
            "available": bool(checkpoint.values),
            "next": list(checkpoint.next),
        },
        "answer": state.get("answer", ""),
    }
    _trace_store[thread_id] = {**trace_record, "owner_id": owner_id}
    return trace_record


def get_agent_trace(thread_id: str, owner_id: int) -> dict[str, object] | None:
    record = _trace_store.get(thread_id)
    if record is None or record.get("owner_id") != owner_id:
        return None
    return {key: value for key, value in record.items() if key != "owner_id"}