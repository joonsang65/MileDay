param(
  [Parameter(Mandatory = $true)]
  [string] $Version
)

$ErrorActionPreference = "Stop"

$releaseDir = Join-Path $PSScriptRoot "..\release-store"
$expectedPattern = "MileDay-Store-$Version-x64.msixupload"
$expectedPath = Join-Path $releaseDir $expectedPattern

if (-not (Test-Path -LiteralPath $releaseDir -PathType Container)) {
  throw "Store release directory was not found: $releaseDir"
}

if (-not (Test-Path -LiteralPath $expectedPath -PathType Leaf)) {
  $found = Get-ChildItem -LiteralPath $releaseDir -File |
    Where-Object { $_.Extension -in @(".appx", ".msix", ".msixupload") } |
    Select-Object -ExpandProperty Name
  throw "Expected Store package was not found: $expectedPath. Found: $($found -join ', ')"
}

$storePackageFullPath = (Resolve-Path -LiteralPath $expectedPath).Path

if ($env:GITHUB_OUTPUT) {
  Add-Content -LiteralPath $env:GITHUB_OUTPUT -Value "store_package_path=$storePackageFullPath"
  Add-Content -LiteralPath $env:GITHUB_OUTPUT -Value "store_package_name=$expectedPattern"
}

Write-Output "StorePackagePath=$storePackageFullPath"
