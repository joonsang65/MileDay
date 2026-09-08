param(
  [Parameter(Mandatory = $true)]
  [string] $InstallerPath,

  [Parameter(Mandatory = $false)]
  [string] $ExpectedPublisher
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $InstallerPath -PathType Leaf)) {
  throw "Installer not found: $InstallerPath"
}

$signature = Get-AuthenticodeSignature -LiteralPath $InstallerPath

if ($signature.Status -ne "Valid") {
  throw "Invalid Authenticode signature for $InstallerPath. Status: $($signature.Status)"
}

if ($null -eq $signature.SignerCertificate) {
  throw "Installer signature is valid but SignerCertificate is missing."
}

if ($ExpectedPublisher -and ($signature.SignerCertificate.Subject -notlike "*$ExpectedPublisher*")) {
  throw "Signer subject does not contain expected publisher '$ExpectedPublisher'. Subject: $($signature.SignerCertificate.Subject)"
}

Write-Output "SignatureStatus=$($signature.Status)"
Write-Output "SignerSubject=$($signature.SignerCertificate.Subject)"
Write-Output "SignerThumbprint=$($signature.SignerCertificate.Thumbprint)"
