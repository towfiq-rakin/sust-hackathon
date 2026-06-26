# Project Update Log

Tracked changes and updates made to QueueStorm Investigator.

## 📅 June 26, 2026

### Added
- **[.gitignore](file:///home/rakin/Desktop/sust-hackathon/.gitignore)**: New comprehensive ignore list for Python build outputs, local virtual environments (`.venv`), temporary credentials (`.env`), test suites cache (`.pytest_cache`), and IDE workspace files (`.vscode`, `.idea`).
- **[README.md](file:///home/rakin/Desktop/sust-hackathon/README.md)**: Exhaustive project documentation covering architecture, tech stack, configuration instructions, request/response models, Gemini/fallback reasoning engines, safety sanitizer policies, and deployment steps.
- **[test_schema.py](file:///home/rakin/Desktop/sust-hackathon/tests/test_schema.py)**: Added unit tests targeting request/response Pydantic models to assert validation behavior, default factories, and correct enum rejection.
- **[test_safety.py](file:///home/rakin/Desktop/sust-hackathon/tests/test_safety.py)**: Added unit tests verifying safety check rules for allowed warnings, blocked credential requests, and forbidden promise sanitizations.
- **[test_samples.py](file:///home/rakin/Desktop/sust-hackathon/tests/test_samples.py)**: Added functional tests for normal classification flow, transaction matching, rule-based verdicts, and department override policies.

### Modified
- **[schemas.py](file:///home/rakin/Desktop/sust-hackathon/app/schemas.py)**: Added missing `metadata` field to the `TicketRequest` schema to fully comply with spec.
- **[main.py](file:///home/rakin/Desktop/sust-hackathon/app/main.py)**: Restructured FastAPI exception handlers to return standard JSON structures for request validation (`400`), empty complaints (`422`), and internal failures (`500`).
- **[rules.py](file:///home/rakin/Desktop/sust-hackathon/app/rules.py)**: Integrated department overrides for contested or high-risk refund requests.
- **[safety.py](file:///home/rakin/Desktop/sust-hackathon/app/safety.py)**: Improved safety sanitizer regex matching to allow negative context warnings (e.g. "do not share") while strictly blocking direct requests and invalid promises.
- **[analyzer.py](file:///home/rakin/Desktop/sust-hackathon/app/analyzer.py)**: Enforced department overrides inside fallback logic and main AI analysis flows.

### Verified
- **Local Dev Server**: Confirmed `uvicorn app.main:app --reload` runs cleanly and responds to `GET /health` requests with status `{"status": "ok"}`.
- **Dependencies**: Verified all package requirements are satisfied under the target Python environment.
- **Testing**: Confirmed that `python -m pytest` executes and passes all test cases (21/21 passed, including health checks, schema limits, safety checkers, and sample scenarios).

