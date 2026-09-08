# Registers a Windows Scheduled Task to run the WhatsApp Digest daily
param(
    [string]$Time = "20:00", # 8:00 PM default daily
    [string]$TaskName = "DeanEmailAutomationDigest"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$batPath = Join-Path $scriptDir "run_daily_digest.bat"

Write-Host "Creating Windows Scheduled Task: '$TaskName' to run daily at $Time..." -ForegroundColor Cyan
Write-Host "Target script: $batPath"

# Check if task already exists and unregister it first
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Updating existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

$action = New-ScheduledTaskAction -Execute $batPath -WorkingDirectory $scriptDir
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Sends daily categorized email summaries directly to WhatsApp."

Write-Host "`n✅ Scheduled Task '$TaskName' successfully registered!" -ForegroundColor Green
Write-Host "It will automatically run every day at $Time and send your email digest to WhatsApp."
