from src.agent import ClinicAgent, build_session
from src.config import AgentConfig


def test_agent_exposes_required_tools() -> None:
    tool_names = {tool.info.name for tool in ClinicAgent().tools}
    assert tool_names == {"check_availability", "book_appointment"}


def test_smallest_stack_session_constructs_without_network_calls() -> None:
    session = build_session(
        config=AgentConfig(),
        smallest_key="test-key",
        vad=None,
    )
    assert session is not None
