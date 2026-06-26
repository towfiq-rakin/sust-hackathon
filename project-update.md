# Project Update Log

Tracked changes and updates made to QueueStorm Investigator.

## 📅 June 26, 2026

### Added
- **[.gitignore](file:///home/rakin/Desktop/sust-hackathon/.gitignore)**: New comprehensive ignore list for Python build outputs, local virtual environments (`.venv`), temporary credentials (`.env`), test suites cache (`.pytest_cache`), and IDE workspace files (`.vscode`, `.idea`).
- **[README.md](file:///home/rakin/Desktop/sust-hackathon/README.md)**: Exhaustive project documentation covering architecture, tech stack, configuration instructions, request/response models, Gemini/fallback reasoning engines, safety sanitizer policies, and deployment steps.
- **[test_schema.py](file:///home/rakin/Desktop/sust-hackathon/tests/test_schema.py)**: Added unit tests targeting request/response Pydantic models to assert validation behavior, default factories, and correct enum rejection.
- **[test_safety.py](file:///home/rakin/Desktop/sust-hackathon/tests/test_safety.py)**: Added unit tests verifying safety check rules for allowed warnings, blocked credential requests, and forbidden promise sanitizations.
- **[test_samples.py](file:///home/rakin/Desktop/sust-hackathon/tests/test_samples.py)**: Added functional tests for normal classification flow, transaction matching, rule-based verdicts, and department override policies.
- **[test_samples_json.py](file:///home/rakin/Desktop/sust-hackathon/tests/test_samples_json.py)**: Added compliance checks against the 10 official SUST Carnival preliminary sample cases.

### Modified
- **[schemas.py](file:///home/rakin/Desktop/sust-hackathon/app/schemas.py)**: Loosened `campaign_context` field type restrictions to handle string parameters presented in official datasets.
- **[main.py](file:///home/rakin/Desktop/sust-hackathon/app/main.py)**: Restructured FastAPI exception handlers to return standard JSON structures for request validation (`400`), empty complaints (`422`), and internal failures (`500`).
- **[rules.py](file:///home/rakin/Desktop/sust-hackathon/app/rules.py)**: Expanded case classifier to natively support Bangla keyphrases, prioritized duplicate check ordering, implemented chronological tie-breaking during matching, added merchant/agent verdict validations, and updated severity/human review routing rules. Also resolved ambiguity in multiple matching transactions for non-duplicate cases and split `wrong_transfer` detection keywords into specific and general phases to prevent overlap with `refund_request`.
- **[safety.py](file:///home/rakin/Desktop/sust-hackathon/app/safety.py)**: Improved safety sanitizer regex matching to allow negative context warnings (e.g. "do not share") while strictly blocking direct requests and invalid promises.
- **[analyzer.py](file:///home/rakin/Desktop/sust-hackathon/app/analyzer.py)**: Enforced department and severity overrides across fallback engines and main reasoning pipelines.
- **[test.rest](file:///home/rakin/Desktop/sust-hackathon/test.rest)**: Corrected payload structure to direct root fields, bypassing the nested `"input"` case block wrapper.
- **[RUNBOOK.md](file:///home/rakin/Desktop/sust-hackathon/RUNBOOK.md)**: Created the operational and troubleshooting manual.
- **[sample_output.json](file:///home/rakin/Desktop/sust-hackathon/sample_output.json)**: Created standard schema-compliant output.
- **[agent.md](file:///home/rakin/Desktop/sust-hackathon/agent.md)**: Generated standard build instruction copy.

### Verified
- **Local Dev Server**: Confirmed `uvicorn app.main:app --reload` runs cleanly and responds to `GET /health` requests with status `{"status": "ok"}`.
- **Dependencies**: Verified all package requirements are satisfied under the target Python environment.
- **Testing**: Confirmed that `python -m pytest` executes and passes all test cases (22/22 passed, including health checks, schema limits, safety checkers, local functional samples, and official JSON case packs under fallback rules).

