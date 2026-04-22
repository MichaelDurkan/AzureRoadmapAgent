# Azure Roadmap Copilot Agent

A self-hosted agent that monitors the [Azure Updates feed](https://azure.microsoft.com/en-us/updates/) and:

- **Sends a weekly email** every Monday with all new Azure product changes categorised into GA, Public Preview, Private Preview, Retirements, and SKU/Pricing changes.
- **Exposes a REST API** on AKS that the **Microsoft 365 Copilot declarative agent** calls to answer questions like *"What's new in Azure this week?"* or *"Are there any Azure retirements I should know about?"*

Everything runs inside your AKS cluster. The only external dependency is a standard SMTP server (Office 365, Gmail, or SendGrid).

---

## Architecture

```
GitHub Actions
  ├── CI: builds Docker images → pushes to ghcr.io
  └── CD: deploys to AKS via kustomize

AKS Cluster  (namespace: azure-roadmap-agent)
  ├── Deployment: api          FastAPI service (2 replicas, HPA 1–5)
  │     └── Service: LoadBalancer  ← public IP
  └── CronJob: weekly-digest   Runs every Monday 08:00 UTC

Microsoft 365 Copilot
  └── Declarative Agent        Calls the AKS API via OpenAPI plugin
```

**Container images** (built automatically by CI):

| Image | Description | Base |
|---|---|---|
| `ghcr.io/<you>/azure-roadmap-agent-api` | FastAPI REST API | `python:3.12-slim` |
| `ghcr.io/<you>/azure-roadmap-agent-scheduler` | Weekly email CronJob | `python:3.12-slim` |

**Data source**: [`https://azurecomcdn.azureedge.net/en-us/updates/feed/`](https://azurecomcdn.azureedge.net/en-us/updates/feed/) — Microsoft's official public Azure Updates RSS feed, updated multiple times daily. No API key required.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| AKS cluster (any node size) | `az aks create` — see step 1 below |
| GitHub account | Repository must be public for free ghcr.io packages |
| SMTP server | Office 365, Gmail (App Password), or SendGrid SMTP relay |
| Microsoft 365 Copilot licence | Only required for the Copilot Agent feature; the scheduled email works without it |

---

## Quick Start

### 1 — Fork and clone this repository

```bash
# Fork via GitHub UI, then:
git clone https://github.com/YOUR_USERNAME/azure-roadmap-agent.git
cd azure-roadmap-agent
```

### 2 — Create an AKS cluster (skip if you already have one)

```bash
az group create --name rg-azure-roadmap --location uksouth
az aks create \
  --resource-group rg-azure-roadmap \
  --name aks-azure-roadmap \
  --node-count 2 \
  --node-vm-size Standard_B2s \
  --enable-managed-identity \
  --generate-ssh-keys
```

### 3 — Create an Azure service principal for GitHub Actions (OIDC)

```bash
# Get your subscription ID
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

# Create a federated credential for GitHub Actions
az ad app create --display-name "github-azure-roadmap-agent"
APP_ID=$(az ad app list --display-name "github-azure-roadmap-agent" --query "[0].appId" -o tsv)
az ad sp create --id $APP_ID
SP_ID=$(az ad sp show --id $APP_ID --query id -o tsv)

az role assignment create \
  --role "Azure Kubernetes Service Cluster User Role" \
  --assignee $SP_ID \
  --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-azure-roadmap

# Add federated credential (replace YOUR_GITHUB_USERNAME and YOUR_REPO_NAME)
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-actions-deploy",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:YOUR_GITHUB_USERNAME/azure-roadmap-agent:environment:production",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

### 4 — Add GitHub repository secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret name | Value |
|---|---|
| `AZURE_CLIENT_ID` | App ID from step 3 (`$APP_ID`) |
| `AZURE_TENANT_ID` | `az account show --query tenantId -o tsv` |
| `AZURE_SUBSCRIPTION_ID` | `az account show --query id -o tsv` |
| `AKS_RESOURCE_GROUP` | `rg-azure-roadmap` |
| `AKS_CLUSTER_NAME` | `aks-azure-roadmap` |
| `SMTP_USER` | Your SMTP login (e.g. `you@company.com`) |
| `SMTP_PASSWORD` | App password / SMTP relay key |
| `SMTP_FROM` | Display name + address (e.g. `Azure Roadmap <you@company.com>`) |
| `RECIPIENT_EMAIL` | Who gets the weekly email |

> **Office 365** — use `smtp.office365.com:587`. `SMTP_USER` and `SMTP_PASSWORD` are your M365 credentials (or a shared mailbox with an app password).
> **Gmail** — enable 2FA, create an [App Password](https://myaccount.google.com/apppasswords), use `smtp.gmail.com:587`.
> **SendGrid** — `smtp.sendgrid.net:587`, `SMTP_USER=apikey`, `SMTP_PASSWORD=SG.xxxx`.

### 5 — Configure image names

Replace `GITHUB_USERNAME` with your actual GitHub username in these files:

```bash
# macOS / Linux
sed -i 's/GITHUB_USERNAME/YOUR_ACTUAL_USERNAME/g' \
  k8s/api/deployment.yaml \
  k8s/scheduler/cronjob.yaml \
  k8s/kustomization.yaml \
  src/api/Dockerfile \
  src/scheduler/Dockerfile \
  copilot-agent/manifest.json

# Windows PowerShell
Get-ChildItem -Recurse -Include *.yaml,*.json,Dockerfile | ForEach-Object {
  (Get-Content $_) -replace 'GITHUB_USERNAME', 'YOUR_ACTUAL_USERNAME' | Set-Content $_
}
```

### 6 — Push to main to trigger CI/CD

```bash
git add .
git commit -m "chore: configure for my environment"
git push origin main
```

GitHub Actions will:
1. Build and push both Docker images to `ghcr.io`
2. Deploy all Kubernetes manifests to your AKS cluster
3. Print the LoadBalancer IP in the deploy log

### 7 — Note your API endpoint

After the deploy workflow completes, run:

```bash
kubectl get service api -n azure-roadmap-agent
```

Copy the `EXTERNAL-IP`. You'll need it in the next step.

---

## Installing the Copilot Agent

### Step 1 — Update the OpenAPI spec

Edit [copilot-agent/openapi.yaml](copilot-agent/openapi.yaml) and replace the server URL:

```yaml
servers:
  - url: http://YOUR_EXTERNAL_IP   # ← paste your AKS LoadBalancer IP here
```

Also update `validDomains` in [copilot-agent/manifest.json](copilot-agent/manifest.json).

### Step 2 — Generate a unique app ID

Replace the placeholder `id` in `manifest.json` with a fresh GUID:

```bash
python -c "import uuid; print(uuid.uuid4())"
```

### Step 3 — Add app icons

Add two PNG files to the `copilot-agent/` directory:
- `color.png` — 192×192 px full-colour icon
- `outline.png` — 32×32 px white outline icon on transparent background

### Step 4 — Package and upload

```bash
cd copilot-agent
zip -r ../azure-roadmap-agent.zip manifest.json declarativeAgent.json openapi.yaml color.png outline.png
```

Upload `azure-roadmap-agent.zip` to the [Teams Developer Portal](https://dev.teams.microsoft.com/apps):
1. **Apps → Import app** → select the ZIP
2. **Publish → Publish to your org**
3. Your M365 admin approves it in the [Teams Admin Centre](https://admin.teams.microsoft.com)
4. The agent then appears in Microsoft 365 Copilot Chat

---

## Adjusting the schedule

Edit the `CRON_SCHEDULE` value in [k8s/configmap.yaml](k8s/configmap.yaml) and re-deploy.

The CronJob manifest's `schedule` field is also patched from this value. Default is `0 8 * * 1` (Monday 08:00 UTC).

To trigger a one-off send immediately:

```bash
kubectl create job --from=cronjob/weekly-digest manual-test \
  -n azure-roadmap-agent
kubectl logs -l job-name=manual-test -n azure-roadmap-agent -f
```

---

## API reference

Once deployed, interactive docs are available at `http://YOUR_IP/docs`.

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Liveness probe |
| `/ready` | GET | Readiness probe |
| `/api/digest` | GET | Full digest grouped by category |
| `/api/updates?category=ga` | GET | Items for a single category |
| `/api/summary` | GET | Markdown summary (used by Copilot) |
| `/api/send-digest` | POST | Trigger an immediate email send |

---

## Repository structure

```
.
├── .github/workflows/
│   ├── ci-build-push.yml        # Build & push Docker images on every push to main
│   └── cd-deploy-aks.yml        # Deploy to AKS after CI succeeds
├── src/
│   ├── shared/                  # Business logic shared by both containers
│   │   ├── rss_fetcher.py       # Fetches & normalises the Azure Updates RSS feed
│   │   ├── classifier.py        # Categorises items (GA / Preview / Retirement / SKU)
│   │   ├── email_builder.py     # Builds the HTML email
│   │   └── email_sender.py      # Sends via SMTP
│   ├── api/                     # FastAPI service
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── health.py
│   │   │   └── digest.py
│   │   └── services/            # Placeholder — filled by Dockerfile COPY
│   └── scheduler/               # Weekly CronJob script
│       ├── Dockerfile
│       ├── requirements.txt
│       └── send_digest.py
├── k8s/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.example.yaml      # Template only — real values set by GitHub Actions
│   ├── api/
│   │   ├── deployment.yaml
│   │   ├── service.yaml         # LoadBalancer (public IP)
│   │   ├── hpa.yaml             # Autoscale 1–5 replicas
│   │   └── ingress.yaml         # Optional NGINX ingress alternative
│   ├── scheduler/
│   │   └── cronjob.yaml
│   └── kustomization.yaml
└── copilot-agent/
    ├── manifest.json            # Teams / M365 Copilot app manifest
    ├── declarativeAgent.json    # Agent instructions & conversation starters
    └── openapi.yaml             # API plugin spec — update server URL after deploy
```
