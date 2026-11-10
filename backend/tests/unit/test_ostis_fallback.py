import pytest
from app.ostis.memory import Memory


@pytest.mark.mock
def test_action_nodes_without_usable_sources_do_not_block_template_search(monkeypatch):
    memory = Memory()
    monkeypatch.setattr(
        memory,
        "user_request",
        lambda term: (
            ["unusable-agent-node"],
            {"status": "finished", "method": "action_user_request"},
        ),
    )
    monkeypatch.setattr(memory, "concepts", lambda term, **kwargs: ["test-only-concept"])
    monkeypatch.setattr(
        memory,
        "source",
        lambda node: {"id": "test-only-source", "excerpt": "test-only-text"}
        if node == "test-only-concept"
        else None,
    )
    result = memory.lookup(["test-only-term"])
    assert result["matches"][0]["id"] == "test-only-source"
    assert result["trace"][0]["result_nodes_count"] == 1
    assert result["trace"][0]["source_count"] == 0
    assert result["trace"][1]["reason"] == "agent_no_sources"
    assert result["trace"][1]["status"] == "matched"
