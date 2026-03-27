import json
from unittest.mock import MagicMock

import anthropic
import pytest

from src.models import ImplementationPlan, Scenario, TestDesignArtifact, TestDesignOutput
from src.generator import generate_implementation_plans


# --- Helpers ---

def make_mock_client(response_text: str) -> MagicMock:
    """Create a mock Anthropic client that returns a fixed text response."""
    content_block = MagicMock()
    content_block.text = response_text
    message = MagicMock()
    message.content = [content_block]
    client = MagicMock(spec=anthropic.Anthropic)
    client.messages.create.return_value = message
    return client


def make_artifact(scenarios: list[Scenario] | None = None) -> TestDesignArtifact:
    if scenarios is None:
        scenarios = [
            Scenario(
                id="TC-POS-001",
                title="Login succeeds",
                expected_result="User is redirected to dashboard",
                steps=["Enter email", "Enter password", "Click submit"],
            )
        ]
    return TestDesignArtifact(
        schema_version="1.0",
        source_project="ai-test-design-assistant",
        requirement_title="User Authentication",
        test_design_output=TestDesignOutput(positive_scenarios=scenarios),
    )


def make_valid_response(scenario_id: str = "TC-POS-001") -> str:
    return json.dumps([
        {
            "scenario_id": scenario_id,
            "test_name": "should successfully log in with valid credentials",
            "arrange": ["A registered user account exists"],
            "act": ["Navigate to login page", "Enter email", "Enter password", "Click submit"],
            "assert_steps": ["The user is redirected to the dashboard"],
            "notes": None,
        }
    ])


# --- Successful parsing ---

def test_returns_list_of_implementation_plans():
    client = make_mock_client(make_valid_response())
    plans = generate_implementation_plans(make_artifact(), client)
    assert isinstance(plans, list)
    assert len(plans) == 1
    assert isinstance(plans[0], ImplementationPlan)


def test_plan_has_correct_scenario_id():
    client = make_mock_client(make_valid_response())
    plans = generate_implementation_plans(make_artifact(), client)
    assert plans[0].scenario_id == "TC-POS-001"


def test_plan_has_naturalized_test_name():
    client = make_mock_client(make_valid_response())
    plans = generate_implementation_plans(make_artifact(), client)
    assert plans[0].test_name == "should successfully log in with valid credentials"


def test_plan_has_arrange_act_assert_fields():
    client = make_mock_client(make_valid_response())
    plans = generate_implementation_plans(make_artifact(), client)
    plan = plans[0]
    assert isinstance(plan.arrange, list)
    assert isinstance(plan.act, list)
    assert isinstance(plan.assert_steps, list)


def test_notes_is_none_when_not_provided():
    client = make_mock_client(make_valid_response())
    plans = generate_implementation_plans(make_artifact(), client)
    assert plans[0].notes is None


def test_notes_is_returned_when_present():
    response = json.dumps([{
        "scenario_id": "TC-POS-001",
        "test_name": "should log in",
        "arrange": [],
        "act": [],
        "assert_steps": [],
        "notes": "Clarify whether email validation is client-side or server-side",
    }])
    client = make_mock_client(response)
    plans = generate_implementation_plans(make_artifact(), client)
    assert plans[0].notes == "Clarify whether email validation is client-side or server-side"


# --- Empty scenarios guard ---

def test_returns_empty_list_when_no_positive_scenarios():
    artifact = make_artifact(scenarios=[])
    client = MagicMock(spec=anthropic.Anthropic)
    plans = generate_implementation_plans(artifact, client)
    assert plans == []
    client.messages.create.assert_not_called()


# --- Validation failures ---

def test_raises_on_invalid_json():
    client = make_mock_client("this is not json at all")
    with pytest.raises(ValueError, match="not valid JSON"):
        generate_implementation_plans(make_artifact(), client)


def test_raises_on_non_array_json():
    client = make_mock_client('{"scenario_id": "TC-POS-001"}')
    with pytest.raises(ValueError, match="JSON array"):
        generate_implementation_plans(make_artifact(), client)


def test_raises_on_unknown_scenario_id():
    response = json.dumps([{
        "scenario_id": "TC-POS-999",
        "test_name": "...",
        "arrange": [],
        "act": [],
        "assert_steps": [],
    }])
    client = make_mock_client(response)
    with pytest.raises(ValueError, match="unknown scenario_id"):
        generate_implementation_plans(make_artifact(), client)


def test_raises_on_missing_required_field():
    response = json.dumps([{
        "scenario_id": "TC-POS-001",
        # test_name is missing
        "arrange": [],
        "act": [],
        "assert_steps": [],
    }])
    client = make_mock_client(response)
    with pytest.raises(ValueError, match="schema validation"):
        generate_implementation_plans(make_artifact(), client)


# --- Markdown fence stripping ---

def test_handles_response_wrapped_in_markdown_fences():
    raw = make_valid_response()
    wrapped = f"```json\n{raw}\n```"
    client = make_mock_client(wrapped)
    plans = generate_implementation_plans(make_artifact(), client)
    assert len(plans) == 1
    assert plans[0].scenario_id == "TC-POS-001"


# --- API call verification ---

def test_api_is_called_with_correct_model():
    client = make_mock_client(make_valid_response())
    generate_implementation_plans(make_artifact(), client)
    call_kwargs = client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"


def test_api_is_called_with_system_prompt():
    client = make_mock_client(make_valid_response())
    generate_implementation_plans(make_artifact(), client)
    call_kwargs = client.messages.create.call_args.kwargs
    assert "system" in call_kwargs
    assert len(call_kwargs["system"]) > 0


def test_prompt_includes_scenario_data():
    client = make_mock_client(make_valid_response())
    generate_implementation_plans(make_artifact(), client)
    call_kwargs = client.messages.create.call_args.kwargs
    prompt_content = call_kwargs["messages"][0]["content"]
    assert "TC-POS-001" in prompt_content
