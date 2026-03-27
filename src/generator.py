import json
from pathlib import Path

import anthropic
from pydantic import ValidationError

from src.models import ImplementationPlan, TestDesignArtifact

_MODEL = "claude-sonnet-4-6"
_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "implementation_plan.txt"

_SYSTEM_PROMPT = (
    "You are a QA automation planning assistant. "
    "Return only valid JSON. Do not include any explanation, prose, or markdown formatting."
)


def _load_prompt(artifact: TestDesignArtifact) -> str:
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    scenarios_data = [
        {
            "scenario_id": s.id,
            "title": s.title,
            "description": s.description,
            "preconditions": s.preconditions or [],
            "steps": s.steps or [],
            "expected_result": s.expected_result,
        }
        for s in artifact.test_design_output.positive_scenarios
    ]
    return template.replace("{scenarios_json}", json.dumps(scenarios_data, indent=2))


def _extract_json(text: str) -> str:
    """Strip markdown code fences if present.

    Claude occasionally wraps JSON in ```json...``` blocks despite instructions.
    This guard handles that case without requiring a more complex parser.
    """
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[1:end])
    return text.strip()


def _parse_and_validate(
    response_text: str,
    artifact: TestDesignArtifact,
) -> list[ImplementationPlan]:
    response_text = _extract_json(response_text)

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI response is not valid JSON: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError(
            f"AI response must be a JSON array, got: {type(data).__name__}"
        )

    try:
        plans = [ImplementationPlan(**item) for item in data]
    except (ValidationError, TypeError) as exc:
        raise ValueError(f"AI response failed schema validation: {exc}") from exc

    valid_ids = {s.id for s in artifact.test_design_output.positive_scenarios}
    for plan in plans:
        if plan.scenario_id not in valid_ids:
            raise ValueError(
                f"AI returned plan for unknown scenario_id '{plan.scenario_id}'. "
                f"Valid IDs: {sorted(valid_ids)}"
            )

    return plans


def generate_implementation_plans(
    artifact: TestDesignArtifact,
    client: anthropic.Anthropic,
) -> list[ImplementationPlan]:
    """Generate structured implementation plans from a validated test design artifact.

    Sends all positive scenarios in a single prompt and returns a validated
    list of ImplementationPlan objects — one per scenario.

    The client is injected to keep this function testable without network calls.

    Raises:
        ValueError: if the AI response cannot be parsed or validated against
                    the ImplementationPlan schema, or contains unknown scenario IDs.
    """
    if not artifact.test_design_output.positive_scenarios:
        return []

    prompt = _load_prompt(artifact)

    response = client.messages.create(
        model=_MODEL,
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = response.content[0].text
    return _parse_and_validate(response_text, artifact)
