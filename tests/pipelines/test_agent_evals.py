import json
from pathlib import Path


TRACE_FIXTURE = Path(__file__).parent / "fixtures" / "agent_traces.json"


def load_evals() -> dict[str, dict[str, object]]:
    return json.loads(TRACE_FIXTURE.read_text(encoding="utf-8"))


def test_sla_trace_retrieves_before_generation():
    evaluation = load_evals()["known_sla"]
    events = evaluation["trace"]
    nodes = [event["node"] for event in events]

    assert nodes.index("retrieve") < nodes.index("generate_answer")
    assert events[1]["output"]["chunks"][0]["source"] == "CONTEXT.md"


def test_unknown_policy_trace_uses_honest_fallback():
    evaluation = load_evals()["unknown_policy"]
    events = evaluation["trace"]
    nodes = [event["node"] for event in events]

    assert nodes == ["receive_question", "retrieve", "no_context"]
    assert events[1]["output"]["count"] == 0
    assert "No tengo información suficiente" in evaluation["answer"]


def test_sla_answer_is_anchored_in_company_context():
    evaluation = load_evals()["known_sla"]
    retrieval = evaluation["trace"][1]["output"]["chunks"][0]

    assert retrieval["source"] == "CONTEXT.md"
    assert "24 horas" in evaluation["answer"]
    assert "48 horas" in evaluation["answer"]


def test_empty_question_trace_stops_before_retrieval():
    evaluation = load_evals()["empty_question"]
    events = evaluation["trace"]

    assert [event["node"] for event in events] == [
        "receive_question",
        "invalid_question",
    ]
    assert evaluation["answer"] == "La pregunta no puede estar vacía."