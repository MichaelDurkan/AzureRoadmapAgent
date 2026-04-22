// ── Container App — FastAPI REST API ─────────────────────────────────────────
// Replaces: AKS Deployment + LoadBalancer Service + HPA
//
// Exposes the API publicly over HTTPS via ACA's built-in ingress.
// The FQDN is automatically assigned as <name>.<env-default-domain>.

@description('Name of the Container App (prefix: ca-)')
param name string

@description('Azure region')
param location string

@description('Resource ID of the Container Apps Environment')
param environmentId string

@description('Fully-qualified container image reference (ghcr.io/owner/repo:tag)')
param containerImage string

// ── Non-sensitive config ──────────────────────────────────────────────────────
param smtpHost string
param smtpPort string = '587'
param lookbackDays string = '7'
param logLevel string = 'INFO'

// ── Sensitive config (stored as Container App secrets) ───────────────────────
@secure()
param smtpUser string
@secure()
param smtpPassword string
@secure()
param smtpFrom string
@secure()
param recipientEmail string

// ── Scaling ───────────────────────────────────────────────────────────────────
@description('Minimum replica count (0 = scale to zero when idle)')
param minReplicas int = 1

@description('Maximum replica count')
param maxReplicas int = 5

@description('Concurrent HTTP requests per replica before scaling out')
param httpConcurrentRequests int = 20

@description('Resource tags')
param tags object = {}

// ── Container App resource ────────────────────────────────────────────────────
resource api 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    environmentId: environmentId

    configuration: {
      // External HTTPS ingress — ACA provisions the TLS cert automatically
      ingress: {
        external: true
        targetPort: 8080
        transport: 'http'
        allowInsecure: false
        corsPolicy: {
          allowedOrigins: ['*']
          allowedMethods: ['GET', 'POST', 'OPTIONS']
          allowedHeaders: ['*']
          allowCredentials: false
        }
      }

      // Secrets — referenced by name in env vars below
      secrets: [
        { name: 'smtp-user',       value: smtpUser       }
        { name: 'smtp-password',   value: smtpPassword   }
        { name: 'smtp-from',       value: smtpFrom       }
        { name: 'recipient-email', value: recipientEmail }
      ]
    }

    template: {
      containers: [
        {
          name: 'api'
          image: containerImage
          env: [
            // Non-sensitive — set as plain values
            { name: 'SMTP_HOST',      value: smtpHost      }
            { name: 'SMTP_PORT',      value: smtpPort      }
            { name: 'LOOKBACK_DAYS',  value: lookbackDays  }
            { name: 'LOG_LEVEL',      value: logLevel      }
            // Sensitive — pulled from secrets above
            { name: 'SMTP_USER',      secretRef: 'smtp-user'       }
            { name: 'SMTP_PASSWORD',  secretRef: 'smtp-password'   }
            { name: 'SMTP_FROM',      secretRef: 'smtp-from'       }
            { name: 'RECIPIENT_EMAIL',secretRef: 'recipient-email' }
          ]
          // Valid ACA resource combination: 0.25 vCPU / 0.5 Gi
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          // Liveness and readiness probes
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8080
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 30
              failureThreshold: 3
              successThreshold: 1
              timeoutSeconds: 5
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/ready'
                port: 8080
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
              periodSeconds: 10
              failureThreshold: 3
              successThreshold: 1
              timeoutSeconds: 3
            }
          ]
        }
      ]

      // HTTP-based autoscaling
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: string(httpConcurrentRequests)
              }
            }
          }
        ]
      }
    }
  }
}

// ── Outputs ───────────────────────────────────────────────────────────────────
@description('Fully-qualified domain name assigned by ACA (no https:// prefix)')
output fqdn string = api.properties.configuration.ingress.fqdn

@description('Full HTTPS URL of the API')
output url string = 'https://${api.properties.configuration.ingress.fqdn}'

@description('Resource name of the Container App')
output name string = api.name
