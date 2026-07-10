param(
    [string]$BackendHost = "127.0.0.1",
    [int]$BackendPort = 8000,
    [int]$HealthTimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RootDir "backend\app"
$FrontendDir = Join-Path $RootDir "frontend"
$LogDir = Join-Path $RootDir "logs"
$BackendOutLog = Join-Path $LogDir "dev_backend.out.log"
$BackendErrLog = Join-Path $LogDir "dev_backend.err.log"
$HealthUrl = "http://${BackendHost}:${BackendPort}/health"
$DbHealthUrl = "http://${BackendHost}:${BackendPort}/health/db"

function Assert-PathExists {
    param(
        [string]$Path,
        [string]$Message
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw $Message
    }
}

function Wait-HttpOk {
    param(
        [string]$Url,
        [int]$TimeoutSeconds,
        [string]$Description
    )

    $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $Deadline) {
        try {
            $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($Response.StatusCode -eq 200) {
                return
            }
        }
        catch {
            Start-Sleep -Milliseconds 700
        }
    }

    throw "${Description} did not pass within ${TimeoutSeconds}s. Check log: $BackendErrLog"
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

function Stop-ProcessTree {
    param(
        [int]$ProcessId
    )

    $ChildProcesses = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId"
    foreach ($ChildProcess in $ChildProcesses) {
        Stop-ProcessTree -ProcessId $ChildProcess.ProcessId
    }

    $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($Process) {
        Stop-Process -Id $ProcessId -Force
    }
}

Assert-PathExists -Path $BackendDir -Message "backend/app directory was not found."
Assert-PathExists -Path $FrontendDir -Message "frontend directory was not found."
Assert-PathExists -Path (Join-Path $FrontendDir "package.json") -Message "frontend/package.json was not found."

if (-not (Test-Path -LiteralPath $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$OriginalPythonPath = $env:PYTHONPATH
if ([string]::IsNullOrWhiteSpace($OriginalPythonPath)) {
    $env:PYTHONPATH = $BackendDir
}
else {
    $env:PYTHONPATH = "$BackendDir;$OriginalPythonPath"
}

$BackendProcess = $null
$StartedBackend = $false

try {
    if (Test-HttpOk -Url $HealthUrl) {
        Write-Host "Backend is already healthy: $HealthUrl"
    }
    else {
        Write-Host "Starting backend: $HealthUrl"
        $BackendProcess = Start-Process `
            -FilePath "python" `
            -ArgumentList @("-m", "uvicorn", "main:app", "--host", $BackendHost, "--port", "$BackendPort", "--reload") `
            -WorkingDirectory $BackendDir `
            -RedirectStandardOutput $BackendOutLog `
            -RedirectStandardError $BackendErrLog `
            -WindowStyle Hidden `
            -PassThru
        $StartedBackend = $true

        Wait-HttpOk -Url $HealthUrl -TimeoutSeconds $HealthTimeoutSeconds -Description "Backend health check"
    }

    Write-Host "Checking backend DB health: $DbHealthUrl"
    Wait-HttpOk -Url $DbHealthUrl -TimeoutSeconds $HealthTimeoutSeconds -Description "Backend DB health check"

    Write-Host "Backend and DB health checks passed. Starting frontend."

    Push-Location $FrontendDir
    try {
        $OriginalElectronRunAsNode = $env:ELECTRON_RUN_AS_NODE
        Remove-Item Env:ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue
        npm run dev
    }
    finally {
        if ([string]::IsNullOrWhiteSpace($OriginalElectronRunAsNode)) {
            Remove-Item Env:ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue
        }
        else {
            $env:ELECTRON_RUN_AS_NODE = $OriginalElectronRunAsNode
        }
        Pop-Location
    }
}
finally {
    $env:PYTHONPATH = $OriginalPythonPath

    if ($StartedBackend -and $BackendProcess -and -not $BackendProcess.HasExited) {
        Write-Host "Stopping backend process tree. PID: $($BackendProcess.Id)"
        Stop-ProcessTree -ProcessId $BackendProcess.Id
    }
}
