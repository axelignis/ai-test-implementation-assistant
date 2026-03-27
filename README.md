# ai-test-implementation-assistant

Transforms structured test design artifacts into Playwright TypeScript test skeletons. Part of an AI-assisted QA workflow.

## Workflow position

```
Requirement
  → ai-test-design-assistant
  → ai-test-implementation-assistant   ← this project
  → Playwright execution
  → ai-regression-analyzer
```

## What it does

Takes a structured JSON artifact and generates a Playwright `.spec.ts` skeleton file. The skeleton includes:

- `test.describe` block named after the requirement
- one `test()` block per positive scenario
- AAA (Arrange / Act / Assert) structure when AI assistance is available
- `// TODO:` markers on every action and assertion the engineer must implement
- placeholder Playwright syntax as a starting point

It does **not** generate selectors, infer application structure, or produce runnable tests without human completion. This tool scaffolds — it does not automate.

## Prerequisites

- Python 3.11+
- An Anthropic API key — optional. The tool falls back to a deterministic Phase 1 skeleton automatically if the key is missing or the API call fails.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

## Usage

```bash
python -m src.main --input path/to/artifact.json --output output/tests.spec.ts
```

If `--output` is omitted, the file is written to `<requirement_title>.spec.ts` in the current directory.

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python -m src.main --input examples/sample_input.json
```

A sample artifact is in `examples/sample_input.json`.

## Input contract

Input is a JSON artifact following the shared contract with `ai-test-design-assistant`:

```json
{
  "schema_version": "1.0",
  "source_project": "ai-test-design-assistant",
  "requirement_title": "User Authentication",
  "test_design_output": {
    "positive_scenarios": [
      {
        "id": "TC-POS-001",
        "title": "Login succeeds with valid credentials",
        "preconditions": ["User account exists"],
        "steps": ["Navigate to login page", "Enter credentials", "Submit"],
        "expected_result": "User is redirected to dashboard"
      }
    ]
  }
}
```

Integration with `ai-test-design-assistant` is file-based. There is no code-level coupling between the repositories.

## Architecture

```
src/models.py      Pydantic input/output contracts
src/generator.py   AI layer: scenarios → ImplementationPlan (structured JSON)
src/renderer.py    Deterministic renderer: plan/scenario → .spec.ts
src/main.py        Execution wiring: CLI entry point + fallback logic
prompts/           Externalized prompt templates
examples/          Sample input artifacts
```

**Key design decision:** AI produces structured data (`ImplementationPlan`), not TypeScript code. The renderer is the sole authority for output structure, `// TODO:` markers, and `.spec.ts` formatting. This keeps rendering deterministic and fully testable without network calls.

If AI generation fails for any reason, the tool falls back to the Phase 1 deterministic renderer automatically. Both paths produce a valid, usable skeleton file.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

65 tests across three test modules. No network calls — the AI layer is testable via client injection and mocking.

## What this is not

- Not a full autonomous test generator
- Not a locator discovery or selector inference tool
- Not a UI crawler or end-to-end automation platform
- Not a replacement for QA engineers
