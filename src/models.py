from typing import Optional

from pydantic import BaseModel


class Scenario(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    preconditions: Optional[list[str]] = None
    steps: Optional[list[str]] = None
    expected_result: str


class TestDesignOutput(BaseModel):
    positive_scenarios: list[Scenario]
    negative_scenarios: Optional[list[Scenario]] = None
    edge_cases: Optional[list[Scenario]] = None
    clarification_questions: Optional[list[str]] = None
    risks: Optional[list[str]] = None


class TestDesignArtifact(BaseModel):
    schema_version: str
    source_project: str
    requirement_title: str
    test_design_output: TestDesignOutput


class ImplementationPlan(BaseModel):
    scenario_id: str
    test_name: str
    arrange: list[str]
    act: list[str]
    assert_steps: list[str]
    notes: Optional[str] = None
