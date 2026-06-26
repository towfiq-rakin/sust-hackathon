# QueueStorm Investigator Runbook ⚡📖

This runbook outlines operational procedures, troubleshooting steps, and deployment guidelines for the QueueStorm Investigator service.

---

## 🚀 Deployment & Startup

### Local Execution
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the development server with reload enabled:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Docker Execution
1. Build the Docker image:
   ```bash
   docker build -t queuestorm-investigator .
   ```
2. Run the Docker container:
   ```bash
   docker run -p 8000:8000 --env-file .env queuestorm-investigator
   ```

---

## ⚙️ Configuration & Environment

The service reads configuration parameters from environment variables or a `.env` file in the working directory:

- `GEMINI_API_KEY`: API credential key for Google Gemini model.
- `GEMINI_MODEL`: Model version to target (defaults to `gemini-1.5-flash`).
- `GEMINI_TIMEOUT_SECONDS`: Request timeout limits (defaults to `12` seconds).
- `USE_GEMINI`: Boolean flag (`true`/`false`) to enable or completely disable AI API calls.

---

## 🔍 Verification & Health Checks

### Verification Steps
1. Perform health check to ensure server is listening:
   ```bash
   curl -I http://127.0.0.1:8000/health
   ```
   *Expected Response: HTTP 200 OK, Content: `{"status": "ok"}`*

2. Verify analysis pipeline using the test suite:
   ```bash
   python3 -m pytest
   ```
   *Expected Response: All 22 tests pass successfully.*

3. Run sample payload from `test.rest`:
   ```bash
   curl -X POST http://127.0.0.1:8000/analyze-ticket \
     -H "Content-Type: application/json" \
     -d @test.rest
   ```

---

## 🛠️ Troubleshooting

### 1. 429 Resource Exhausted (Gemini Quota Exceeded)
- **Symptom**: Gemini API throws `429 RESOURCE_EXHAUSTED` or rate limit errors.
- **Handling**: The service will automatically log the exception and fall back to the deterministic rule-based matching engine. The API response will contain `"reason_codes": ["fallback_used", "gemini_parsing_error"]` or similar.
- **Action**: Check your Google AI Studio billing details and API quotas. If quotas are depleted, the service continues to operate safely using fallback rules.

### 2. Invalid or Unsafe Customer Replies
- **Symptom**: LLM draft replies attempt to ask for credentials (PIN/OTP) or promise refunds/reversals.
- **Handling**: The internal `safety.py` sanitizer scans all responses. If an unsafe pattern is detected, it sanitizes the reply or replaces it with the default secure message.
- **Action**: Verify the model configuration and system prompt rules.

### 3. Server Startup Failures
- **Symptom**: Port 8000 is already in use.
- **Action**: Locate the process holding the port and kill it, or run uvicorn on a different port:
  ```bash
  uvicorn app.main:app --port 8080
  ```
