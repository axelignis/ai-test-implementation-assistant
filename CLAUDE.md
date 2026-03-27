# ai-test-implementation-assistant

## Purpose
Transforms structured test design artifacts (JSON) into Playwright TypeScript test skeletons.
Sits between ai-test-design-assistant (design stage) and test execution (implementation stage).
This tool scaffolds — it does not automate.

## Workflow Position
Requirement → ai-test-design-assistant → [this project] → Playwright execution → ai-regression-analyzer

## Stack
- Python — orchestration, validation, rendering
- Pydantic — input contract enforcement
- Claude API — limited AI assistance (deferred), not structural authority
- TypeScript Playwright — output format

## AI Role Boundary
The deterministic renderer is the authority for all output structure. AI is not.

The renderer owns:
- describe/test block structure
- TODO markers
- placeholder action comments
- placeholder assertion comments
- final .spec.ts formatting

AI may assist in later phases with limited tasks only:
- naturalizing test names
- improving comment wording
- suggesting test grouping (if justified)

AI output is always treated as untrusted input. It is never written directly to disk.

## Input Contract
Consumes a versioned JSON artifact (`schema_version` field required).
Primary source: ai-test-design-assistant output.
Integration is file-based. No code-level coupling to other repositories.

## Output Contract
Produces a `.spec.ts` Playwright skeleton file.
Selectors and assertions are TODO-marked stubs.
The output must be immediately useful to a QA engineer as a starting point.

## Architecture Principles
- Validate input before any processing
- Rendering is deterministic and separately testable without AI
- Prompts are externalized when used
- Small, single-responsibility modules
- AI used for reasoning assistance only — never structural authority

## Engineering Rules
- Do not invent selectors or application-specific implementation details
- Do not generate assertions beyond placeholder intent
- TODO markers are required on every line a QA engineer must implement
- Test names are derived deterministically from scenario titles
