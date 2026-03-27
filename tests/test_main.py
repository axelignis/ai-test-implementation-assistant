import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.models import ImplementationPlan, TestDesignArtifact
from src.main import _derive_output_path, _load_artifact, run


# --- Sample data ---

VALID_ARTIFACT = {
    "schema_version": "1.0",
    "source_project": "ai-test-design-assistant",
    "requirement_title": "User Authentication",
    "test_design_output": {
        "positive_scenarios": [
            {
                "id": "TC-POS-001",
                "title": "Login succeeds",
                "expected_result": "User is redirected to dashboard",
            }
        ]
    },
}

VALID_PLANS = [
    ImplementationPlan(
        scenario_id="TC-POS-001",
        test_name="should successfully log in",
        arrange=["A registered user account exists"],
        act=["Navigate to login page", "Enter credentials", "Click submit"],
        assert_steps=["User is redirected to dashboard"],
        notes=None,
    )
]


# --- _derive_output_path ---

def test_derive_output_path_from_simple_title():
    assert _derive_output_path("User Authentication") == Path("user_authentication.spec.ts")


def test_derive_output_path_lowercases():
    assert _derive_output_path("Password Reset") == Path("password_reset.spec.ts")


def test_derive_output_path_collapses_special_characters():
    assert _derive_output_path("Login / Logout") == Path("login_logout.spec.ts")


# --- _load_artifact ---

def test_load_artifact_parses_valid_file(tmp_path):
    f = tmp_path / "input.json"
    f.write_text(json.dumps(VALID_ARTIFACT))
    artifact = _load_artifact(f)
    assert isinstance(artifact, TestDesignArtifact)
    assert artifact.requirement_title == "User Authentication"


def test_load_artifact_exits_on_missing_file(tmp_path):
    with pytest.raises(SystemExit) as exc_info:
        _load_artifact(tmp_path / "nonexistent.json")
    assert exc_info.value.code == 1


def test_load_artifact_exits_on_invalid_json(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("not json at all")
    with pytest.raises(SystemExit) as exc_info:
        _load_artifact(f)
    assert exc_info.value.code == 1


def test_load_artifact_exits_on_schema_mismatch(tmp_path):
    f = tmp_path / "wrong.json"
    f.write_text(json.dumps({"unexpected": "structure"}))
    with pytest.raises(SystemExit) as exc_info:
        _load_artifact(f)
    assert exc_info.value.code == 1


# --- run(): AI path ---

def test_run_ai_path_writes_output_file(tmp_path):
    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps(VALID_ARTIFACT))
    output_file = tmp_path / "output.spec.ts"

    with patch("src.main.generate_implementation_plans", return_value=VALID_PLANS):
        with patch("anthropic.Anthropic"):
            run(input_file, output_file)

    assert output_file.exists()


def test_run_ai_path_output_contains_plan_test_name(tmp_path):
    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps(VALID_ARTIFACT))
    output_file = tmp_path / "output.spec.ts"

    with patch("src.main.generate_implementation_plans", return_value=VALID_PLANS):
        with patch("anthropic.Anthropic"):
            run(input_file, output_file)

    content = output_file.read_text()
    assert "should successfully log in" in content


def test_run_ai_path_output_has_aaa_structure(tmp_path):
    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps(VALID_ARTIFACT))
    output_file = tmp_path / "output.spec.ts"

    with patch("src.main.generate_implementation_plans", return_value=VALID_PLANS):
        with patch("anthropic.Anthropic"):
            run(input_file, output_file)

    content = output_file.read_text()
    assert "// Arrange" in content
    assert "// Act" in content
    assert "// Assert" in content


# --- run(): fallback path ---

def test_run_fallback_writes_output_file(tmp_path):
    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps(VALID_ARTIFACT))
    output_file = tmp_path / "output.spec.ts"

    with patch("src.main.generate_implementation_plans", side_effect=ValueError("AI unavailable")):
        with patch("anthropic.Anthropic"):
            run(input_file, output_file)

    assert output_file.exists()


def test_run_fallback_output_has_phase1_structure(tmp_path):
    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps(VALID_ARTIFACT))
    output_file = tmp_path / "output.spec.ts"

    with patch("src.main.generate_implementation_plans", side_effect=ValueError("AI unavailable")):
        with patch("anthropic.Anthropic"):
            run(input_file, output_file)

    content = output_file.read_text()
    # Phase 1 path: no AAA section headers, but still a valid Playwright file
    assert "// Arrange" not in content
    assert "import { test, expect } from '@playwright/test';" in content


# --- run(): output path handling ---

def test_run_creates_nested_output_directory(tmp_path):
    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps(VALID_ARTIFACT))
    output_file = tmp_path / "nested" / "dir" / "output.spec.ts"

    with patch("src.main.generate_implementation_plans", return_value=VALID_PLANS):
        with patch("anthropic.Anthropic"):
            run(input_file, output_file)

    assert output_file.exists()


def test_run_derives_output_path_when_not_specified(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps(VALID_ARTIFACT))

    with patch("src.main.generate_implementation_plans", return_value=VALID_PLANS):
        with patch("anthropic.Anthropic"):
            run(input_file, None)

    assert (tmp_path / "user_authentication.spec.ts").exists()
