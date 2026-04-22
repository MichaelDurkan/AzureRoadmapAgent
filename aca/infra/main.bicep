// ── Azure Roadmap Agent — Azure Container Apps deployment ─────────────────────
// Orchestrates all ACA resources for one environment (prod / staging / etc.).
//
// Resources provisioned:
//   • Log Analytics Workspace     (law-azure-roadmap-<env>)
//   • Container Apps Environment  (cae-azure-roadmap-<env>)
//   • Container App — API         (ca-azure-roadmap-api-<env>)
//   • Container App Job — Digest  (caj-azure-roadmap-scheduler-<env>)
//
// Sensitive parameters (SMTP credentials, recipient) are passed at deploy time
// by GitHub Actions from repository secrets and are NEVER stored in source control.

targetScope = 'resourceGroup'

// ── Deployment identity ───────────────────────────────────────────────────────
@description('Short name of the target environment, used in all resource names.')
@allowed(['prod', 'staging', 'dev'])
param environmentName string = 'prod'

@description('Azure region. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('Your GitHub username (lowercase). Used to build the ghcr.io image paths.')
param githubUsername string

// ── Image tags ────────────────────────────────────────────────────────────────
@description('Tag for the API container image. Set to the git-SHA by CI.')
param apiImageTag string = 'latest'

@description('Tag for the scheduler container image. Set to the git-SHA by CI.')
param schedulerImageTag string = 'latest'

// ── Non-sensitive application config ─────────────────────────────────────────
@description('SMTP server hostname.')
param smtpHost string = 'smtp.office365.com'

@description('SMTP server port (STARTTLS).')
param smtpPort string = '587'

@description('Number of days of history included in each digest.')
param lookbackDays string = '7'

@description('Python log level (DEBUG / INFO / WARNING / ERROR).')
param logLevel string = 'INFO'

@description('Cron expression for the weekly email schedule (UTC).')
param cronSchedule string = '0 8 * * 1'

// ── API scaling ───────────────────────────────────────────────────────────────
@description('Minimum API replicas. Set to 0 to allow scale-to-zero.')
param apiMinReplicas int = 1

@description('Maximum API replicas.')
param apiMaxReplicas int = 5

// ── Sensitive parameters (injected at deploy time, never committed) ───────────
@secure()
@description('SMTP login / username.')
param smtpUser string

@secure()
@description('SMTP password or app-password.')
param smtpPassword string

@secure()
@description('From address shown in sent emails (e.g. "Azure Roadmap <you@domain.com>").')
param smtpFrom string

@secure()
@description('Email address that receives the weekly digest.')
param recipientEmail string

// ── Common tags ───────────────────────────────────────────────────────────────
var tags = {
  application: 'azure-roadmap-agent'
  environment: environmentName
  'managed-by': 'bicep'
  repository: 'https://github.com/${githubUsername}/azure-roadmap-agent'
}

// ── Modules ───────────────────────────────────────────────────────────────────

module env 'modules/environment.bicep' = {
  name: 'deploy-environment'
  params: {
    name: 'cae-azure-roadmap-${environmentName}'
    location: location
    tags: tags
  }
}

module api 'modules/api.bicep' = {
  name: 'deploy-api'
  params: {
    name: 'ca-azure-roadmap-api-${environmentName}'
    location: location
    environmentId: env.outputs.environmentId
    containerImage: 'ghcr.io/${githubUsername}/azure-roadmap-agent-api:${apiImageTag}'
    smtpHost: smtpHost
    smtpPort: smtpPort
    lookbackDays: lookbackDays
    logLevel: logLevel
    smtpUser: smtpUser
    smtpPassword: smtpPassword
    smtpFrom: smtpFrom
    recipientEmail: recipientEmail
    minReplicas: apiMinReplicas
    maxReplicas: apiMaxReplicas
    tags: tags
  }
}

module scheduler 'modules/scheduler.bicep' = {
  name: 'deploy-scheduler'
  params: {
    name: 'caj-azure-roadmap-scheduler-${environmentName}'
    location: location
    environmentId: env.outputs.environmentId
    containerImage: 'ghcr.io/${githubUsername}/azure-roadmap-agent-scheduler:${schedulerImageTag}'
    cronSchedule: cronSchedule
    smtpHost: smtpHost
    smtpPort: smtpPort
    lookbackDays: lookbackDays
    logLevel: logLevel
    smtpUser: smtpUser
    smtpPassword: smtpPassword
    smtpFrom: smtpFrom
    recipientEmail: recipientEmail
    tags: tags
  }
}

// ── Outputs ───────────────────────────────────────────────────────────────────
@description('Full HTTPS URL of the deployed API.')
output apiUrl string = api.outputs.url

@description('FQDN only — use this in copilot-agent/openapi.yaml server URL.')
output apiFqdn string = api.outputs.fqdn

@description('Container Apps Environment name.')
output environmentName string = env.outputs.environmentName

@description('Container App Job name for the scheduler.')
output schedulerJobName string = scheduler.outputs.jobName
