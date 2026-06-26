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

---

## 📅 June 26, 2026 (Vertex AI Migration)

### Added
- **[agent-studio-498807-a74af6d2c474.json](file:///home/rakin/Desktop/sust-hackathon/agent-studio-498807-a74af6d2c474.json)**: Added the service account credentials JSON to the project root directory.
- **[railway_deployment.md](file:///home/rakin/Desktop/sust-hackathon/docs/railway_deployment.md)**: Created a detailed Step-by-Step Railway Deployment Guide under the `docs/` folder.

### Modified
- **[.gitignore](file:///home/rakin/Desktop/sust-hackathon/.gitignore)**: Ignored `agent-studio-498807-a74af6d2c474.json` and general `*.json` key files to ensure credentials are never committed, while preserving required project JSON assets (`SUST_Preli_Sample_Cases.json`, `sample_output.json`, and `skills-lock.json`).
- **[app/config.py](file:///home/rakin/Desktop/sust-hackathon/app/config.py)**: Added `USE_VERTEXAI`, `VERTEX_PROJECT_ID`, `VERTEX_LOCATION`, and `GOOGLE_APPLICATION_CREDENTIALS` settings. Changed the default `GEMINI_MODEL` to `gemini-2.5-flash`.
- **[app/gemini_client.py](file:///home/rakin/Desktop/sust-hackathon/app/app/gemini_client.py)**: Refactored client initialization to build the Google Cloud Vertex AI client using the service account credentials pointed to by the `GOOGLE_APPLICATION_CREDENTIALS` environment variable.
- **[app/rules.py](file:///home/rakin/Desktop/sust-hackathon/app/rules.py)**: Updated `needs_human_review` to accept the transaction amount as an optional parameter and ensure that high-value refund requests (amount >= 5000) are correctly flagged as requiring human review, while preserving the severity settings of other case types.
- **[app/analyzer.py](file:///home/rakin/Desktop/sust-hackathon/app/analyzer.py)**: Normalized `evidence_verdict` by forcing alignment with rule-based deterministic database verification whenever the status check produces a clear consistent or inconsistent result. Also passed the transaction amount parameter to `needs_human_review`.
- **[.env]** & **[.env.example]**: Removed `GEMINI_API_KEY` and updated variables template to configure Google Application credentials, project ID, location, and model parameters.
- **[README.md](file:///home/rakin/Desktop/sust-hackathon/README.md)** & **[RUNBOOK.md](file:///home/rakin/Desktop/sust-hackathon/RUNBOOK.md)**: Updated technical description, environmental documentation, architecture flowchart, Docker volume-mount examples, and Vertex AI API troubleshooting guidelines.

### Verified
- **Vertex AI Client Connectivity**: Verified integration with `us-central1` Vertex API gateway and successful generation of content using `gemini-2.5-flash`.
- **Testing**: Confirmed that `python3 -m pytest` executes and successfully passes all 22 test cases under the live Vertex AI client configuration.

