# Deployment Guide: Deploying QueueStorm Investigator on Railway ⚡🚀

This guide provides step-by-step instructions for deploying the **QueueStorm Investigator** service on [Railway](https://railway.app).

---

## 📋 Overview

Railway is a cloud platform where you can provision infrastructure, build from Git, and deploy applications instantly. Since QueueStorm Investigator is packaged with a `Dockerfile` and configured to run on a standard FastAPI/Uvicorn server, it can be deployed on Railway with minimal setup.

Vertex AI authentication is managed via Google Service Account credentials. On Railway, we recommend providing the credentials directly via an environment variable string to avoid committing private keys to your Git repository.

---

## ⚙️ Required Configuration (Environment Variables)

When deploying to Railway, configure the following variables in the **Variables** section of your Railway service:

| Variable | Recommended Value | Description |
| :--- | :--- | :--- |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Target Vertex AI model (use `gemini-2.5-flash` for low-latency responses). |
| `USE_GEMINI` | `true` | Enables/disables the Vertex AI model reasoning pipeline. |
| `USE_VERTEXAI` | `true` | Tells the client to use the Vertex AI gateway. |
| `VERTEX_PROJECT_ID` | `agent-studio-498807` | Your Google Cloud project ID. |
| `VERTEX_LOCATION` | `us-central1` | GCP region location for Vertex AI resource calls. |
| `VERTEX_SERVICE_ACCOUNT_JSON` | *(Paste raw JSON contents)* | Raw text content of your service account key file (`agent-studio-498807-a74af6d2c474.json`). |

> [!WARNING]
> Do **NOT** commit your service account JSON file to GitHub. The `.gitignore` file is configured to exclude it. Instead, copy the entire raw contents of the JSON key file and paste it directly into the `VERTEX_SERVICE_ACCOUNT_JSON` environment variable in Railway. The application will dynamically read, decode, and apply these credentials at startup.

---

## 🚀 Step-by-Step Deployment

### Step 1: Push Your Code to GitHub
Ensure your local changes are committed and pushed to your GitHub repository (excluding `agent-studio-498807-a74af6d2c474.json` which is ignored).

### Step 2: Create a Project on Railway
1. Go to the [Railway Dashboard](https://railway.app) and sign in.
2. Click **New Project** in the upper right.
3. Select **Deploy from GitHub repo**.
4. Choose the repository containing your QueueStorm Investigator code.

### Step 3: Configure Build & Start Command
Railway automatically detects the `Dockerfile` in the root directory. It will build a production-ready Docker container using:
* Base image: `python:3.11-slim`
* Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (Railway automatically overrides and passes the active `$PORT`).

No extra buildpack configuration is needed.

### Step 4: Configure Environment Variables
1. Once the service is created, go to the **Variables** tab of the service.
2. Click **New Variable** or **Raw Editor** and paste the following variables:
   ```env
   GEMINI_MODEL=gemini-2.5-flash
   USE_GEMINI=true
   USE_VERTEXAI=true
   VERTEX_PROJECT_ID=agent-studio-498807
   VERTEX_LOCATION=us-central1
   VERTEX_SERVICE_ACCOUNT_JSON={"type": "service_account", ...}
   ```
   *(Ensure you replace the `VERTEX_SERVICE_ACCOUNT_JSON` placeholder with the complete content of your private key JSON file).*
3. Save the variables. Railway will automatically trigger a redeployment with the new environment configurations.

### Step 5: Generate a Public Domain
1. Go to the **Settings** tab of your service.
2. Under the **Networking** section, click **Generate Domain** (or set up a custom domain).
3. Copy the generated domain (e.g., `queuestorm-investigator-production.up.railway.app`).

---

## 📡 Verifying Your Deployment

Once the deployment finishes and shows a green checkmark, verify the endpoints using `curl` or another REST client.

### 1. Test Health Check (`GET /health`)
Make a request to the health endpoint. It must return `{"status": "ok"}` instantly without invoking Vertex AI:
```bash
curl https://<your-railway-domain>/health
```
*Expected Response (`200 OK`):*
```json
{"status":"ok"}
```

### 2. Test Complaint Investigation (`POST /analyze-ticket`)
Send a ticket analysis payload to verify that Vertex AI authentication, transaction matching, and safety rules work end-to-end:
```bash
curl -X POST https://<your-railway-domain>/analyze-ticket \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TKT-WT-1",
    "complaint": "I sent 5000 taka to a wrong number 01712345678.",
    "transaction_history": [
      {
        "transaction_id": "TXN-9101",
        "amount": 5000,
        "counterparty": "01712345678",
        "status": "completed",
        "type": "transfer"
      }
    ]
  }'
```

*Expected Response (`200 OK`):*
```json
{
  "ticket_id": "TKT-WT-1",
  "relevant_transaction_id": "TXN-9101",
  "evidence_verdict": "consistent",
  "case_type": "wrong_transfer",
  "severity": "high",
  "department": "dispute_resolution",
  "agent_summary": "Customer reports wrong transfer of 5000 BDT to counterparty 01712345678. Transaction history shows a completed transfer TXN-9101 matching the details.",
  "recommended_next_action": "Verify recipient details and initiate dispute resolution workflow for wrong transfer.",
  "customer_reply": "We have noted your concern. Please do not share your PIN, OTP, password, or sensitive account information with anyone. Our team will review the issue through official channels.",
  "human_review_required": true,
  "confidence": 0.9,
  "reason_codes": [
    "wrong_transfer",
    "transaction_match"
  ]
}
```

---

## 🛠️ Troubleshooting Deployment Errors

### 1. Application Log shows "Model not found"
* **Symptom**: Vertex AI returns a `404` or model not found error.
* **Resolution**: Verify that `GEMINI_MODEL` is set to a valid Vertex model name (such as `gemini-2.5-flash` or `gemini-2.5-pro`) and that `VERTEX_LOCATION` is set to the correct GCP region where the model is enabled.

### 2. Application Log shows "Permission Denied" (403)
* **Symptom**: Vertex AI returns a `403` auth error.
* **Resolution**: Verify that the content of `VERTEX_SERVICE_ACCOUNT_JSON` is copied completely (with no missing braces or truncated private keys) and that the Service Account has `Vertex AI User` or `AI Platform User` roles assigned on Google Cloud Console.
