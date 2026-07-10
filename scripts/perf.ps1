param(
    [ValidateSet("all", "goal", "milestone", "setting", "date")]
    [string[]]$Prefix = @("all"),
    [string]$BackendHost = "127.0.0.1",
    [int]$BackendPort = 8000,
    [string]$FrontendUrl = "http://localhost:5173",
    [int]$StartupTimeoutSeconds = 60,
    [switch]$SkipCleanup
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
$FrontendDir = Join-Path $RootDir "frontend"
$DevScript = Join-Path $PSScriptRoot "dev.ps1"
$BackendHealthUrl = "http://${BackendHost}:${BackendPort}/health"
$BackendDbHealthUrl = "http://${BackendHost}:${BackendPort}/health/db"

function Assert-PathExists {
    param(
        [string]$Path,
        [string]$Message
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw $Message
    }
}

function Test-HttpOk {
    param(
        [string]$Url
    )

    try {
        $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        return $Response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Wait-HttpOk {
    param(
        [string]$Url,
        [int]$TimeoutSeconds,
        [string]$Description,
        [System.Diagnostics.Process]$ProcessToWatch = $null
    )

    $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $Deadline) {
        if ($ProcessToWatch -and $ProcessToWatch.HasExited) {
            throw "$Description 대기 중 dev.ps1 프로세스가 종료되었습니다. exit code: $($ProcessToWatch.ExitCode)"
        }

        if (Test-HttpOk -Url $Url) {
            return
        }

        Start-Sleep -Milliseconds 700
    }

    throw "$Description did not pass within ${TimeoutSeconds}s. Url: $Url"
}

function Get-PerfCommands {
    param(
        [string[]]$SelectedPrefixes
    )

    $CommandMap = [ordered]@{
        goal = @("perf:goal:create")
        milestone = @("perf:milestone:create", "perf:milestone:toggle")
        setting = @("perf:settings:update")
        date = @("perf:date:select")
    }

    if ($SelectedPrefixes -contains "all") {
        return @(
            $CommandMap.goal +
            $CommandMap.milestone +
            $CommandMap.setting +
            $CommandMap.date
        )
    }

    $Commands = New-Object System.Collections.Generic.List[string]
    foreach ($SelectedPrefix in $SelectedPrefixes) {
        foreach ($Command in $CommandMap[$SelectedPrefix]) {
            if (-not $Commands.Contains($Command)) {
                $Commands.Add($Command)
            }
        }
    }

    return $Commands.ToArray()
}

Assert-PathExists -Path $DevScript -Message "scripts/dev.ps1 was not found."
Assert-PathExists -Path $FrontendDir -Message "frontend directory was not found."
Assert-PathExists -Path (Join-Path $FrontendDir "package.json") -Message "frontend/package.json was not found."

$BackendReady = (Test-HttpOk -Url $BackendHealthUrl) -and (Test-HttpOk -Url $BackendDbHealthUrl)
$FrontendReady = Test-HttpOk -Url $FrontendUrl
$DevProcess = $null

if ($BackendReady -and $FrontendReady) {
    Write-Host "Backend, DB, frontend are already running. Skip dev.ps1."
}
else {
    Write-Host "Starting dev server through scripts/dev.ps1."
    $DevProcess = Start-Process `
        -FilePath "powershell" `
        -ArgumentList @(
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            $DevScript,
            "-BackendHost",
            $BackendHost,
            "-BackendPort",
            "$BackendPort",
            "-HealthTimeoutSeconds",
            "$StartupTimeoutSeconds"
        ) `
        -WorkingDirectory $RootDir `
        -WindowStyle Hidden `
        -PassThru

    Write-Host "Waiting for backend health: $BackendHealthUrl"
    Wait-HttpOk -Url $BackendHealthUrl -TimeoutSeconds $StartupTimeoutSeconds -Description "Backend health" -ProcessToWatch $DevProcess

    Write-Host "Waiting for backend DB health: $BackendDbHealthUrl"
    Wait-HttpOk -Url $BackendDbHealthUrl -TimeoutSeconds $StartupTimeoutSeconds -Description "Backend DB health" -ProcessToWatch $DevProcess

    Write-Host "Waiting for frontend dev server: $FrontendUrl"
    Wait-HttpOk -Url $FrontendUrl -TimeoutSeconds $StartupTimeoutSeconds -Description "Frontend dev server" -ProcessToWatch $DevProcess
}

$Commands = Get-PerfCommands -SelectedPrefixes $Prefix
if ($Commands.Count -eq 0) {
    throw "실행할 perf command가 없습니다. Prefix: $($Prefix -join ', ')"
}

$FailedCommands = New-Object System.Collections.Generic.List[string]

Push-Location $FrontendDir
try {
    foreach ($Command in $Commands) {
        Write-Host ""
        Write-Host "Running npm run $Command"
        npm run $Command
        if ($LASTEXITCODE -ne 0) {
            $Failure = "$Command exited with code $LASTEXITCODE"
            $FailedCommands.Add($Failure)
            Write-Warning $Failure
        }
    }

    if (-not $SkipCleanup) {
        Write-Host ""
        Write-Host "Running npm run perf:cleanup"
        npm run perf:cleanup
        if ($LASTEXITCODE -ne 0) {
            $Failure = "perf:cleanup exited with code $LASTEXITCODE"
            $FailedCommands.Add($Failure)
            Write-Warning $Failure
        }
    }
    else {
        Write-Host ""
        Write-Host "Skipping performance test data cleanup."
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Performance command summary"
Write-Host "total: $($Commands.Count)"
Write-Host "failed: $($FailedCommands.Count)"

if ($FailedCommands.Count -gt 0) {
    foreach ($Failure in $FailedCommands) {
        Write-Host "- $Failure"
    }
    exit 1
}

exit 0
