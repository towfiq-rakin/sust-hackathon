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
2. Run the Docker container (mounting the service account JSON key file so it is accessible to the application):
   ```bash
   docker run -p 8000:8000 --env-file .env -v $(pwd)/agent-studio-498807-a74af6d2c474.json:/app/agent-studio-498807-a74af6d2c474.json queuestorm-investigator
   ```

---

## ⚙️ Configuration & Environment

The service reads configuration parameters from environment variables or a `.env` file in the working directory:

- `GEMINI_MODEL`: Model version to target (defaults to `gemini-2.5-pro`).
- `GEMINI_TIMEOUT_SECONDS`: Request timeout limits (defaults to `12` seconds).
- `USE_GEMINI`: Boolean flag (`true`/`false`) to enable or completely disable AI API calls.
- `USE_VERTEXAI`: Boolean flag (`true`/`false`) to route AI calls to Vertex AI model endpoints.
- `VERTEX_PROJECT_ID`: Google Cloud Project ID for Vertex AI client billing and configuration.
- `VERTEX_LOCATION`: Regional location for Google Cloud Vertex AI resources (defaults to `us-central1`).
- `GOOGLE_APPLICATION_CREDENTIALS`: Service Account JSON filepath for authenticating Google Cloud calls.

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

### 1. Vertex AI API Errors (404/403/429/500)
- **Symptom**: Vertex AI API throws errors such as `404 Model not found`, `403 Permission denied`, or rate limits.
- **Handling**: The service will automatically log the exception and fall back to the deterministic rule-based matching engine. The API response will contain `"reason_codes": ["fallback_used", "gemini_parsing_error"]`.
- **Action**:
  - For `404 Model not found`: Verify that the `GEMINI_MODEL` is a valid Vertex AI model ID (such as `gemini-2.5-pro` or `gemini-2.5-flash`) and is available in your `VERTEX_LOCATION` region.
  - For `403 Permission denied`: Verify that your service account credentials file is placed correctly, `GOOGLE_APPLICATION_CREDENTIALS` is set to point to it, and that the service account has the necessary IAM permissions (such as `Vertex AI User` or `AI Platform User`).
  - For rate limits/quotas: Upgrade your Google Cloud quota limits. The rules-based engine ensures the API remains functional in the meantime.

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
