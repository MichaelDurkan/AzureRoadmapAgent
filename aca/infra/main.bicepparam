// ── Azure Roadmap Agent — Container Apps deployment parameters ────────────────
// Non-sensitive defaults only.
//
// Sensitive parameters (smtpUser, smtpPassword, smtpFrom, recipientEmail) are
// intentionally omitted here and injected at deploy time from GitHub Actions
// repository secrets.  NEVER add credential values to this file.
//
// To override any parameter for a specific environment, pass it on the
// `az deployment group create --parameters` command line (see the GitHub
// Actions workflow or the README for examples).

using './main.bicep'

// ── Identity ──────────────────────────────────────────────────────────────────
// Replace with your actual GitHub username before pushing
param githubUsername = 'GITHUB_USERNAME'

// ── Environment ───────────────────────────────────────────────────────────────
param environmentName = 'prod'

// Azure region — change to your preferred region
// Full list: az account list-locations --query "[].name" -o tsv
param location = 'uksouth'

// ── Email / digest config ─────────────────────────────────────────────────────
// Office 365: smtp.office365.com  port 587
// Gmail:      smtp.gmail.com      port 587  (requires App Password)
// SendGrid:   smtp.sendgrid.net   port 587  (user=apikey, password=SG.xxx)
param smtpHost = 'smtp.office365.com'
param smtpPort = '587'

// Days of history included in each digest (1–90)
param lookbackDays = '7'

// Cron schedule (UTC).  Default: every Monday at 08:00.
// Format: "minute hour day-of-month month day-of-week"
param cronSchedule = '0 8 * * 1'

// ── Logging ───────────────────────────────────────────────────────────────────
param logLevel = 'INFO'

// ── API scaling ───────────────────────────────────────────────────────────────
// Set apiMinReplicas to 0 to enable scale-to-zero (saves cost, adds cold-start latency)
param apiMinReplicas = 1
param apiMaxReplicas = 5
