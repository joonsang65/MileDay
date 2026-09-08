param(
  [Parameter(Mandatory = $true)]
  [string] $InstallerPath
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $InstallerPath -PathType Leaf)) {
  throw "Installer not found: $InstallerPath"
}

$hash = Get-FileHash -LiteralPath $InstallerPath -Algorithm SHA256
$shaPath = "$InstallerPath.sha256.txt"
$line = "$($hash.Hash)  $(Split-Path -Leaf $InstallerPath)"

Set-Content -LiteralPath $shaPath -Value $line -Encoding UTF8

if ($env:GITHUB_OUTPUT) {
  Add-Content -LiteralPath $env:GITHUB_OUTPUT -Value "sha256=$($hash.Hash)"
  Add-Content -LiteralPath $env:GITHUB_OUTPUT -Value "sha256_path=$shaPath"
}

Write-Output "SHA256=$($hash.Hash)"
Write-Output "SHA256Path=$shaPath"
