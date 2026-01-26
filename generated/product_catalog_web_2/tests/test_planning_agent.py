from agents import planning_agent


def test_planning_agent_basic():
    task = {
        "task": "plan",
        "payload": {
            "idea": "demo",
            "module": "hello_mod",
        },
    }

    result = planning_agent.handle(task)

    assert isinstance(result, dict)
    assert result.get("ok") is True
    assert result.get("plan") == "demo via hello_mod"

    data = result.get("data", {})
    assert data.get("agent") == "planning"
    assert data.get("plan") == "demo via hello_mod"
    assert "raw" in data
