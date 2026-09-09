# Registers a Windows Scheduled Task to run the WhatsApp Digest daily
param(
    [string]$Time = "20:00",
    [string]$TaskName = "DeanEmailAutomationDigest"
)

$cleanTime = $Time.Trim()

# Auto-detect if user entered 12h time like "2:28" or "2:28 PM"
if ($cleanTime -match '^(?<hour>[1-9]|1[0-2]):(?<min>[0-5][0-9])\s*(?<meridiem>AM|PM)?$') {
    $h = [int]$matches['hour']
    $m = $matches['min']
    $ampm = $matches['meridiem']
    
    if ($ampm -eq 'PM' -and $h -lt 12) {
        $h += 12
    } elseif ($ampm -eq 'AM' -and $h -eq 12) {
        $h = 0
    } elseif (-not $ampm -and (Get-Date).Hour -ge 12 -and $h -lt 12) {
        # If user didn't specify AM/PM and current time is afternoon, default to PM
        $h += 12
    }
    $formattedTime = "{0:D2}:{1}" -f $h, $m
} else {
    $formattedTime = $cleanTime
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$batPath = Join-Path $scriptDir "run_daily_digest.bat"

Write-Host "Creating Windows Scheduled Task: '$TaskName' to run daily at $formattedTime (Silent Background)..." -ForegroundColor Cyan
Write-Host "Target script: $batPath"

# Check if task already exists and unregister it first
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Updating existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-WindowStyle Hidden -ExecutionPolicy Bypass -Command `"Start-Process -FilePath '$batPath' -WindowStyle Hidden`"" -WorkingDirectory $scriptDir
$trigger = New-ScheduledTaskTrigger -Daily -At $formattedTime
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Sends daily categorized email summaries directly to WhatsApp."

Write-Host "`n✅ Scheduled Task '$TaskName' successfully registered!" -ForegroundColor Green
Write-Host "It will automatically run every day at $formattedTime and send your email digest to WhatsApp."
