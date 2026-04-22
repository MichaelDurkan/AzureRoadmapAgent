# Azure Roadmap Agent — Azure Container Apps Deployment

This directory contains the **Azure Container Apps** variant of the Azure Roadmap Agent.

> The AKS variant lives in [`k8s/`](../k8s/) and is completely independent.
> Both share the same Docker images built by [`ci-build-push.yml`](../.github/workflows/ci-build-push.yml).

---

## How it differs from the AKS deployment

| Concern | AKS (`k8s/`) | Container Apps (`aca/`) |
|---|---|---|
| Infrastructure definition | Kubernetes YAML + Kustomize | Bicep (IaC) |
| API hosting | Deployment + LoadBalancer Service | Container App (HTTPS ingress built-in) |
| Scheduling | Kubernetes CronJob | Container App Job (`ScheduleTriggerConfig`) |
| Autoscaling | HPA manifest | ACA HTTP scaling rules (built-in) |
| TLS certificate | Manual / ingress controller | Automatic (ACA-managed) |
| Secrets management | Kubernetes Secret | Container App native secrets |
| Node management | You manage nodes | Fully serverless (consumption plan) |
| Deploy tool | `kubectl` + `kustomize` | `az deployment group create` (Bicep) |
| GitHub Actions workflow | `cd-deploy-aks.yml` | `cd-deploy-aca.yml` |
| Extra GitHub secrets needed | `AKS_RESOURCE_GROUP`, `AKS_CLUSTER_NAME` | `ACA_RESOURCE_GROUP` |

---

## Resources provisioned by Bicep

```
Resource Group  (e.g. rg-azure-roadmap-aca)
  ├── Log Analytics Workspace        law-azure-roadmap-prod
  ├── Container Apps Environment     cae-azure-roadmap-prod
  ├── Container App — API            ca-azure-roadmap-api-prod
  │     HTTPS endpoint: https://ca-azure-roadmap-api-prod.<unique>.uksouth.azurecontainerapps.io
  └── Container App Job — Scheduler  caj-azure-roadmap-scheduler-prod
        Cron: 0 8 * * 1  (every Monday 08:00 UTC)
```

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Azure subscription | Any tier (Consumption plan = pay per use, very low cost) |
| Azure CLI ≥ 2.57 | `az upgrade` to update |
| Bicep CLI ≥ 0.25 | Installed automatically with Azure CLI 2.20+ |
| GitHub account | Public repo for free ghcr.io packages |
| Same SMTP server as AKS | The same credentials work for both deployments |

---

## Quick Start

### Step 1 — Create the ACA resource group

```bash
az group create \
  --name rg-azure-roadmap-aca \
  --location uksouth
```

### Step 2 — Grant the GitHub Actions service principal access

Use the same service principal you created for AKS (or create a new one):

```bash
SP_ID=$(az ad sp show --id $APP_ID --query id -o tsv)

az role assignment create \
  --role "Contributor" \
  --assignee $SP_ID \
  --scope $(az group show --name rg-azure-roadmap-aca --query id -o tsv)
```

### Step 3 — Add the one new GitHub secret

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|---|---|
| `ACA_RESOURCE_GROUP` | `rg-azure-roadmap-aca` |

All other secrets (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `SMTP_*`, `RECIPIENT_EMAIL`) are **already set** from the AKS setup — no duplication needed.

### Step 4 — (Optional) Set a location variable

If you want a region other than `uksouth`, add a **repository variable** (not a secret):

| Variable | Example value |
|---|---|
| `ACA_LOCATION` | `westeurope` |

### Step 5 — Replace the placeholder username

The `main.bicepparam` file ships with `GITHUB_USERNAME` as a placeholder.
The CD workflow patches this automatically at runtime, but if you want to deploy
locally you need to update it first:

```bash
# macOS / Linux
sed -i 's/GITHUB_USERNAME/your-actual-username/g' aca/infra/main.bicepparam

# Windows PowerShell
(Get-Content aca\infra\main.bicepparam) -replace 'GITHUB_USERNAME','your-actual-username' |
  Set-Content aca\infra\main.bicepparam
```

### Step 6 — Push to main

Pushing to `main` triggers the CI workflow (builds images) which on completion
triggers `cd-deploy-aca.yml` automatically.

Alternatively, run it manually:
**Actions → CD — Deploy to Azure Container Apps → Run workflow**

### Step 7 — Note your API URL

The deploy job prints it at the end:

```
✅  Azure Container Apps deployment complete
   API URL : https://ca-azure-roadmap-api-prod.<hash>.uksouth.azurecontainerapps.io
   API docs: https://ca-azure-roadmap-api-prod.<hash>.uksouth.azurecontainerapps.io/docs
```

---

## Updating the Copilot Agent to use the ACA endpoint

After deployment, update [copilot-agent/openapi.yaml](../copilot-agent/openapi.yaml):

```yaml
servers:
  - url: https://ca-azure-roadmap-api-prod.<hash>.uksouth.azurecontainerapps.io
```

Then repackage and re-upload the agent ZIP to Teams Developer Portal
(see the main [README](../README.md#installing-the-copilot-agent)).

---

## Customising the deployment

### Change the schedule

Edit `cronSchedule` in [main.bicepparam](infra/main.bicepparam):

```bicep
param cronSchedule = '0 9 * * 5'   // Every Friday at 09:00 UTC
```

Push to main — the next deploy will update the Container App Job.

### Enable scale-to-zero (lowest cost)

```bicep
param apiMinReplicas = 0   // API shuts down when idle (adds ~3 s cold-start)
```

### Deploy to a staging environment

Trigger the workflow manually with `environment_name = staging`.
This creates a parallel set of resources suffixed `-staging` in the same resource group.

### Trigger the digest job manually

```bash
az containerapp job start \
  --name caj-azure-roadmap-scheduler-prod \
  --resource-group rg-azure-roadmap-aca
```

### View job execution logs

```bash
# List recent executions
az containerapp job execution list \
  --name caj-azure-roadmap-scheduler-prod \
  --resource-group rg-azure-roadmap-aca \
  --output table

# Stream logs for a specific execution
az containerapp logs show \
  --name caj-azure-roadmap-scheduler-prod \
  --resource-group rg-azure-roadmap-aca \
  --type system \
  --follow
```

### View API logs

```bash
az containerapp logs show \
  --name ca-azure-roadmap-api-prod \
  --resource-group rg-azure-roadmap-aca \
  --follow
```

---

## Deploying locally (without GitHub Actions)

```bash
# Login
az login
az account set --subscription YOUR_SUBSCRIPTION_ID

# Deploy
az deployment group create \
  --resource-group rg-azure-roadmap-aca \
  --template-file  aca/infra/main.bicep \
  --parameters     aca/infra/main.bicepparam \
  --parameters \
    githubUsername="your-github-username" \
    apiImageTag="latest" \
    schedulerImageTag="latest" \
    smtpUser="you@domain.com" \
    smtpPassword="your-app-password" \
    smtpFrom="Azure Roadmap <you@domain.com>" \
    recipientEmail="you@domain.com"
```

---

## File structure

```
aca/
├── infra/
│   ├── main.bicep              Orchestrator — calls all three modules
│   ├── main.bicepparam         Non-sensitive parameter defaults
│   └── modules/
│       ├── environment.bicep   Log Analytics + Container Apps Environment
│       ├── api.bicep           Container App (FastAPI, HTTPS ingress, autoscaling)
│       └── scheduler.bicep     Container App Job (cron-triggered weekly digest)
└── README.md                   This file
```

The GitHub Actions workflow is at [`.github/workflows/cd-deploy-aca.yml`](../.github/workflows/cd-deploy-aca.yml).
