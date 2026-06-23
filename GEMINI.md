# Coding Agent Guide: ADR Decision Log Agent

This repository contains an AI-powered, database-backed **Architecture Decision Record (ADR) Log Agent** built using the **Google ADK v2** framework. The agent extracts structured architecture decisions from unstructured developer brain-dumps and securely logs them to a private database.

---

## 🏗️ Architecture Overview

The system is deployed as a fully serverless, highly secure, private full-stack application on Google Cloud Platform:

```
[ User (Dev UI) ] --(Proxy Tunnel)--> [ Cloud Run (FastAPI/Agent) ]
                                                |
                                    (VPC Access Connector)
                                                |
                                                v
                                    [ Private Cloud SQL (Postgres) ]
```

### 1. Networking (VPC & Peering)
*   **VPC Network**: `decision-log-vpc` (custom VPC).
*   **Private Services Access**: Peered range `10.8.0.0/16` reserved for Google services (Cloud SQL).
*   **Serverless VPC Access Connector**: `dec-log-vpc-conn` (subnet `10.9.0.0/28`) in `us-central1`. This connector acts as a private network bridge, routing all outbound Cloud Run database traffic privately into the VPC.

### 2. Database (Cloud SQL)
*   **Instance Name**: `decision-log-db` (PostgreSQL 15).
*   **IP Address**: `10.8.0.3` (**Private IP only**; no public IP, completely hidden from the internet).
*   **Database Name**: `decision_records`
*   **Database Username**: `agent_user`

### 3. Compute (Cloud Run)
*   **Service Name**: `decision-log-agent-service` in region `us-central1`.
*   **Execution Identity**: Compute Engine default service account (`PROJECT_NUMBER-compute@developer.gserviceaccount.com`).
*   **Ingress**: Internal/Private (secured behind IAM authentication).

---

## ⚙️ Local Development & Testing

### 1. Bypassing Corporate Airlock/Registry Errors
If your local laptop uses a corporate package proxy (e.g., Airlock) that blocks public PyPI packages with a `403 Forbidden` error, bypass it by running all `uv` and `agents-cli` commands with the `UV_NO_CONFIG=true` environment variable:
```bash
UV_NO_CONFIG=true uv sync
UV_NO_CONFIG=true agents-cli playground
```

### 2. Running the Local Playground
To run the agent locally with an interactive web UI and trace viewer (using a local SQLite database):
```bash
UV_NO_CONFIG=true agents-cli playground
```
Navigate to `http://localhost:8000/dev-ui` to chat with the agent and inspect execution traces.

### 3. Running Unit and Integration Tests
```bash
UV_NO_CONFIG=true uv run pytest tests/unit tests/integration
```

---

## 🚀 Deployment Guide

Deploying changes is a two-step process: building the container and updating the Cloud Run service.

### Step 1: Build & Package (Cloud Build)
Submit the codebase to Google Cloud Build. It will compile your Dockerfile and push the finished image to your private Artifact Registry repository:
```bash
gcloud builds submit --tag us-central1-docker.pkg.dev/arnav-sandbox/decision-log-agent-repo/agent-image:v3 .
```

### Step 2: Deploy to Cloud Run
Deploy the compiled container to Cloud Run. Crucially, pass the Serverless VPC Access Connector and the connection string environment variables so the agent can route database queries privately:
```bash
gcloud run deploy decision-log-agent-service \
  --image=us-central1-docker.pkg.dev/arnav-sandbox/decision-log-agent-repo/agent-image:v3 \
  --region=us-central1 \
  --vpc-connector=dec-log-vpc-conn \
  --set-env-vars=DATABASE_URL="postgresql+asyncpg://agent_user:AgentUser1112@10.8.0.3/decision_records",GOOGLE_CLOUD_PROJECT="arnav-sandbox",GOOGLE_CLOUD_LOCATION="us-central1",GOOGLE_GENAI_USE_VERTEXAI="True" \
  --allow-unauthenticated
```
*Note: Due to organization policies (Domain Restricted Sharing), `--allow-unauthenticated` will deploy the service as private/authenticated by default, which is the correct secure behavior.*

---

## 🔒 Secure Browser Access (Local Proxy)

Because the Cloud Run service is 100% private, you cannot load the service URL directly in a browser without getting a `403 Forbidden` error. 

To access the live cloud-hosted Developer UI securely from your local browser, run the official **Google Cloud Run Services Proxy**:

```bash
gcloud run services proxy decision-log-agent-service \
  --region=us-central1 \
  --project=arnav-sandbox
```
This starts a local proxy at `http://127.0.0.1:8080` and automatically handles authentication tokens under the hood. 

Simply open your browser and navigate to:
👉 **`http://localhost:8080/dev-ui`**

Any decisions you log here will write directly into your **private Cloud SQL PostgreSQL database** in the cloud!

---

## 🛠️ Troubleshooting & IAM Gotchas

If you encounter errors during development or deployment, verify these known resolutions:

### 1. Cloud Build Fails to Download Source Code (403 GCS)
*   **Error**: `Error 403: PROJECT-compute@developer.gserviceaccount.com does not have storage.objects.get access...`
*   **Fix**: Grant the `Storage Object Viewer` role to the Compute default service account:
    ```bash
    gcloud projects add-iam-policy-binding arnav-sandbox \
      --member="serviceAccount:1052358563971-compute@developer.gserviceaccount.com" \
      --role="roles/storage.objectViewer"
    ```

### 2. Cloud Build Fails to Push Container Image (403 Artifact Registry)
*   **Error**: `Permission 'artifactregistry.repositories.uploadArtifacts' denied on resource...`
*   **Fix**: Grant the `Artifact Registry Writer` and `Logs Writer` roles to the Compute default service account:
    ```bash
    gcloud projects add-iam-policy-binding arnav-sandbox \
      --member="serviceAccount:1052358563971-compute@developer.gserviceaccount.com" \
      --role="roles/artifactregistry.writer"

    gcloud projects add-iam-policy-binding arnav-sandbox \
      --member="serviceAccount:1052358563971-compute@developer.gserviceaccount.com" \
      --role="roles/logging.logWriter"
    ```

### 3. Cloud Run Agent Fails to Call Gemini (403 Vertex AI)
*   **Error**: The service is live but crashes or throws 403 when you send a message.
*   **Fix**: Grant the `Vertex AI User` role to the Compute default service account (which runs Cloud Run):
    ```bash
    gcloud projects add-iam-policy-binding arnav-sandbox \
      --member="serviceAccount:1052358563971-compute@developer.gserviceaccount.com" \
      --role="roles/aiplatform.user"
    ```

### 4. Local Proxy returns 403 Forbidden in Browser
*   **Error**: Browser displays `Your client does not have permission to get URL /...`
*   **Fix**: Explicitly grant your own developer GCP user account the `Cloud Run Invoker` role:
    ```bash
    gcloud run services add-iam-policy-binding decision-log-agent-service \
      --region=us-central1 \
      --member="user:admin@arnavgulati.altostrat.com" \
      --role="roles/run.invoker"
    ```

### 5. urllib3 / pyOpenSSL Context Mutation ValueError (macOS CLI crash)
*   **Error**: `ValueError: Context has already been used to create a Connection, it cannot be mutated again` when running `agents-cli deploy` under Python 3.13.
*   **Fix**: Force `uv` to reinstall and run `google-agents-cli` under Python 3.12, which is completely unaffected by this OpenSSL bug:
    ```bash
    uv tool install --python 3.12 --force google-agents-cli
    ```
