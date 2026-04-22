// ── Container Apps Environment + Log Analytics Workspace ─────────────────────
// Provisions the shared infrastructure layer that Container Apps and Jobs
// both attach to.  One environment per deployment target (prod / staging / etc.).

@description('Name of the Container Apps Environment (prefix: cae-)')
param name string

@description('Azure region for all resources')
param location string

@description('Resource tags')
param tags object = {}

@description('Log retention in days (7–730)')
param logRetentionDays int = 30

// ── Log Analytics Workspace ──────────────────────────────────────────────────
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'law-${name}'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: logRetentionDays
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// ── Container Apps Environment ───────────────────────────────────────────────
resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
    zoneRedundant: false   // set true if using a Premium SKU ACA environment
    peerAuthentication: {
      mtls: {
        enabled: false
      }
    }
  }
}

// ── Outputs ──────────────────────────────────────────────────────────────────
@description('Resource ID of the Container Apps Environment')
output environmentId string = environment.id

@description('Name of the Container Apps Environment')
output environmentName string = environment.name

@description('Default domain of the environment (used for constructing FQDNs)')
output defaultDomain string = environment.properties.defaultDomain
