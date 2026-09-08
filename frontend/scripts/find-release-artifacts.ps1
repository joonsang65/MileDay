param(
  [Parameter(Mandatory = $true)]
  [string] $Version
)

$ErrorActionPreference = "Stop"

$releaseDir = Join-Path $PSScriptRoot "..\release"
$installerName = "MileDay-Setup-$Version-x64.exe"
$installerPath = Join-Path $releaseDir $installerName
$unpackedPath = Join-Path $releaseDir "win-unpacked\MileDay.exe"

if (-not (Test-Path -LiteralPath $installerPath -PathType Leaf)) {
  throw "Expected installer was not found: $installerPath"
}

if (-not (Test-Path -LiteralPath $unpackedPath -PathType Leaf)) {
  throw "Expected unpacked executable was not found: $unpackedPath"
}

$installerFullPath = (Resolve-Path -LiteralPath $installerPath).Path
$unpackedFullPath = (Resolve-Path -LiteralPath $unpackedPath).Path

if ($env:GITHUB_OUTPUT) {
  Add-Content -LiteralPath $env:GITHUB_OUTPUT -Value "installer_path=$installerFullPath"
  Add-Content -LiteralPath $env:GITHUB_OUTPUT -Value "installer_name=$installerName"
  Add-Content -LiteralPath $env:GITHUB_OUTPUT -Value "unpacked_exe_path=$unpackedFullPath"
}

Write-Output "InstallerPath=$installerFullPath"
Write-Output "UnpackedExePath=$unpackedFullPath"
