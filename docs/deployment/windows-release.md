# MileDay Windows release

This document describes the transitional Windows EXE release path for MileDay.
For Microsoft Store submission, use
`docs/deployment/windows-store-msix.md` first. The MSIX Store workflow is the
default path because Microsoft Store signs MSIX/AppX packages after
certification.

The release workflow runs only when `frontend/package.json` or
`frontend/package-lock.json` is pushed to the `main` branch. The workflow reads
`frontend/package.json` version `0.1.5`, creates tag `v0.1.5`, and publishes
that release.

## Local build

Local development and unsigned packaging do not require Azure credentials.

```powershell
cd frontend
npm ci
npm run build
npm run verify:package-api
npm run dist
```

The local installer is written to `frontend/release`.

## Production release

Production EXE release builds run on GitHub Actions with Windows, Azure
Trusted Signing, Authenticode verification, SHA256 generation, GitHub Release
upload, and optional Cloudflare R2 upload.

This workflow is manual fallback/debug infrastructure during the MSIX
transition. It does not run automatically on `main` push.

To release `0.1.5`, push the version change to `main`:

```powershell
cd frontend
npm version 0.1.5 --no-git-tag-version
cd ..
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: release v0.1.5"
git push origin main
```

Do not create the release tag manually. GitHub Actions creates `vX.Y.Z` after
the quality gate, signing, SHA256 generation, and optional R2 upload succeed.

## Required GitHub secrets

Set these in GitHub repository Settings > Secrets and variables > Actions >
Secrets:

| Name | Purpose |
| --- | --- |
| `AZURE_TENANT_ID` | Entra tenant for the signing service principal. |
| `AZURE_CLIENT_ID` | Client ID for the signing service principal. |
| `AZURE_CLIENT_SECRET` | Client secret for the signing service principal. |

Do not commit PFX files, credential JSON, private keys, or client secrets to
the repository.

## Required GitHub variables

Set these in GitHub repository Settings > Secrets and variables > Actions >
Variables. They may also be stored as secrets if preferred.

| Name | Purpose |
| --- | --- |
| `AZURE_TRUSTED_SIGNING_ENDPOINT` | Azure Trusted Signing endpoint for the account region. |
| `AZURE_TRUSTED_SIGNING_ACCOUNT_NAME` | Trusted Signing account name. |
| `AZURE_TRUSTED_SIGNING_CERTIFICATE_PROFILE` | Certificate profile name. |
| `WINDOWS_PUBLISHER_NAME` | Publisher subject expected in the signing certificate. |

## Optional Cloudflare R2 upload

R2 upload is enabled only when all of these settings are present. If only some
are configured, the workflow fails before publishing a GitHub Release.

Secrets:

| Name | Purpose |
| --- | --- |
| `R2_ACCESS_KEY_ID` | R2 S3-compatible access key ID. |
| `R2_SECRET_ACCESS_KEY` | R2 S3-compatible secret access key. |

Variables:

| Name | Purpose |
| --- | --- |
| `R2_ACCOUNT_ID` | Cloudflare account ID used in the R2 endpoint URL. |
| `R2_BUCKET` | Target R2 bucket. |
| `R2_PUBLIC_BASE_URL` | Public base URL mapped to the bucket. |

The workflow uploads immutable versioned files under:

```text
releases/MileDay-Setup-X.Y.Z-x64.exe
releases/MileDay-Setup-X.Y.Z-x64.exe.sha256.txt
```

## Azure Trusted Signing setup

1. Create or choose an Azure Trusted Signing account.
2. Create a certificate profile for MileDay.
3. Create an Entra app registration or service principal for GitHub Actions.
4. Grant the service principal the Trusted Signing Certificate Profile Signer
   role on the certificate profile or the minimum appropriate scope.
5. Add the GitHub secrets and variables listed above.

The paid EXE fallback workflow uses the current electron-builder Azure signing
configuration. The repository keeps the normal unsigned `npm run dist` path
intact and uses `npm run dist:signed` only in the manual EXE fallback workflow.

## Release quality gate

The release workflow runs these checks before publishing:

```text
npm ci
npm run verify:release-version
npm run lint
npm test
npm run dist:signed
Authenticode signature verification for the installer
Authenticode signature verification for win-unpacked/MileDay.exe
SHA256 generation from the final signed installer
optional R2 upload
GitHub Release creation
```

If lint, tests, package API verification, version matching, signing,
signature validation, installer discovery, SHA256 generation, or configured
R2 upload fails, the GitHub Release is not created.

## Outputs

The GitHub Actions summary prints:

| Field | Meaning |
| --- | --- |
| Version | Release version without the `v` prefix. |
| Artifact | Installer filename. |
| Signature | Authenticode verification result. |
| Signer | Signing certificate subject. |
| Signer thumbprint | Signing certificate thumbprint. |
| SHA256 | Final signed installer SHA256. |
| GitHub Release | Published GitHub Release URL. |
| R2 URL | Public installer URL when R2 is configured. |

For Microsoft Partner Center resubmission, use the R2 URL as the Package URL
when R2 is configured, and use the printed SHA256 value.

## Troubleshooting

Duplicate version:

Check whether tag `vX.Y.Z` or GitHub Release `vX.Y.Z` already exists. Bump
`frontend/package.json` before pushing `main` again.

Signing failure:

Check the Azure service principal, Trusted Signing account, certificate
profile, endpoint region, and Certificate Profile Signer role assignment.

Invalid signature:

Check that `WINDOWS_PUBLISHER_NAME` matches the certificate subject and that
the final installer was signed by Azure Trusted Signing.

R2 upload failure:

Check that all R2 secrets and variables are present, the access key can write
to the bucket, and the public base URL maps to the same bucket path.

Duplicate GitHub Release:

The workflow fails fast when a release or tag already exists for the package
version. Bump the package version before rerunning from `main`.
