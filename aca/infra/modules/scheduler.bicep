// ── Container App Job — Weekly Digest Scheduler ───────────────────────────────
// Replaces: Kubernetes CronJob
//
// Uses ACA's native ScheduleTriggerConfig with a cron expression.
// Runs the send_digest.py script on the configured schedule,
// retries up to 2 times on failure, and keeps history for 5 runs.

@description('Name of the Container App Job (prefix: caj-)')
param name string

@description('Azure region')
param location string

@description('Resource ID of the Container Apps Environment')
param environmentId string

@description('Fully-qualified container image reference (ghcr.io/owner/repo:tag)')
param containerImage string

// ── Schedule ──────────────────────────────────────────────────────────────────
@description('Cron expression for the schedule. Default: Monday 08:00 UTC.')
param cronSchedule string = '0 8 * * 1'

// ── Non-sensitive config ──────────────────────────────────────────────────────
param smtpHost string
param smtpPort string = '587'
param lookbackDays string = '7'
param logLevel string = 'INFO'

// ── Sensitive config ──────────────────────────────────────────────────────────
@secure()
param smtpUser string
@secure()
param smtpPassword string
@secure()
param smtpFrom string
@secure()
param recipientEmail string

@description('Resource tags')
param tags object = {}

// ── Container App Job resource ────────────────────────────────────────────────
resource schedulerJob 'Microsoft.App/jobs@2024-03-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    environmentId: environmentId

    configuration: {
      triggerType: 'Schedule'

      // Each execution gets up to 10 minutes to complete
      replicaTimeout: 600

      // Retry up to 2 times before marking the execution as failed
      replicaRetryLimit: 2

      scheduleTriggerConfig: {
        // Standard 5-field cron expression (UTC)
        cronExpression: cronSchedule
        // One pod per execution — the digest script is not parallelisable
        replicaCompletionCount: 1
        parallelism: 1
      }

      // Secrets referenced in env vars below
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
          name: 'scheduler'
          image: containerImage
          env: [
            { name: 'SMTP_HOST',       value: smtpHost      }
            { name: 'SMTP_PORT',       value: smtpPort      }
            { name: 'LOOKBACK_DAYS',   value: lookbackDays  }
            { name: 'LOG_LEVEL',       value: logLevel      }
            { name: 'SMTP_USER',       secretRef: 'smtp-user'       }
            { name: 'SMTP_PASSWORD',   secretRef: 'smtp-password'   }
            { name: 'SMTP_FROM',       secretRef: 'smtp-from'       }
            { name: 'RECIPIENT_EMAIL', secretRef: 'recipient-email' }
          ]
          // Valid ACA resource combination: 0.25 vCPU / 0.5 Gi
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
    }
  }
}

// ── Outputs ───────────────────────────────────────────────────────────────────
@description('Resource name of the Container App Job')
output jobName string = schedulerJob.name
