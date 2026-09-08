# MileDay Windows Store package release

MileDay uses the Microsoft Store package path as the default Store submission
path. This avoids the paid Azure Trusted Signing dependency for Store
submissions because the Microsoft Store signs MSIX/AppX packages after
certification.

Current tooling note: MSIX support currently requires the `electron-builder`
`next` prerelease line because the stable npm `latest` tag is still v26. The
project pins `electron-builder` to the v27 prerelease so the Store workflow can
emit `.msixupload` packages.

The existing NSIS EXE build remains available during the transition as a
fallback/debug artifact. It is not the default Store submission artifact.

## Why MSIX

Microsoft Store handles final signing for MSIX/AppX packages submitted through
Partner Center. That means Store submission does not require Azure Trusted
Signing, a PFX certificate, or a hardware token.

EXE/MSI submissions are different. The submitter must Authenticode-sign the
installer and every PE file with a certificate that chains to the Microsoft
Trusted Root Program. Unsigned NSIS installers are rejected as unsigned
packages.

## Transition plan

Current transition state:

| Path | Purpose | Status |
| --- | --- | --- |
| MSIX upload | Microsoft Store submission | Default automated Store artifact |
| NSIS EXE | Local direct install, fallback, debug | Kept during transition |
| Azure Trusted Signing EXE | Direct-distribution signed EXE | Manual fallback only |

After the Store package is accepted by Partner Center and runtime behavior is
verified, the NSIS/Azure EXE release path can be removed or left as a manual
debug-only path.

## Local Store build

Set the Store package identity values in your shell, then run the Store build.

```powershell
$env:MSIX_IDENTITY_NAME="your-partner-center-package-identity"
$env:MSIX_PUBLISHER="CN=your-partner-center-publisher-id"
$env:MSIX_PUBLISHER_DISPLAY_NAME="Your Publisher Display Name"
$env:MSIX_APPLICATION_ID="MileDay"
$env:MSIX_BACKGROUND_COLOR="#ffffff"

cd frontend
npm ci
npm run dist:store
```

The Store package file is written to `frontend/release-store`.

## GitHub Actions Store build

The Store workflow runs only on `main` branch pushes that change Store release
inputs:

```text
frontend/package.json
frontend/package-lock.json
frontend/electron-builder.store.cjs
frontend/scripts/verify-store-env.mjs
frontend/scripts/find-store-artifacts.ps1
.github/workflows/release-store-msix.yml
```

Workflow:

```text
checkout
npm ci
npm run lint
npm test
npm run build
npm run verify:package-api
npm run dist:store
find Store package artifact
write SHA256
upload GitHub Actions artifact
write Actions summary
```

The first Store workflow intentionally uploads only a GitHub Actions artifact.
It does not create a GitHub Release, so it cannot collide with the existing EXE
release process.

## Required GitHub variables

Set these in GitHub repository Settings > Secrets and variables > Actions >
Variables:

| Name | Purpose |
| --- | --- |
| `MSIX_IDENTITY_NAME` | Partner Center package identity name. |
| `MSIX_PUBLISHER` | Partner Center package publisher subject, usually starting with `CN=`. |
| `MSIX_PUBLISHER_DISPLAY_NAME` | Friendly publisher name shown to users. |
| `MSIX_APPLICATION_ID` | Optional app manifest application ID. Defaults from identity if omitted. |
| `MSIX_BACKGROUND_COLOR` | Optional tile background color in `#RRGGBB` format. |

No Azure Trusted Signing secrets are required for the MSIX Store workflow.

## Partner Center manual upload

1. Push a version change to `main`.
2. Open the `Windows Store Package Release` workflow run.
3. Download the `mileday-store-package-X.Y.Z` artifact.
4. Confirm the Actions summary SHA256 matches the downloaded Store package.
5. Upload the `.msixupload` package in Partner Center.
6. Submit for certification.
7. After certification, Microsoft Store signs and publishes the package.

## Store review notes

Validate these before submission:

| Area | Check |
| --- | --- |
| Package identity | Matches the reserved Partner Center app identity. |
| Publisher | Matches the Partner Center publisher string. |
| Icons | Store tile/logo assets render correctly. |
| App data | Settings, auth token storage, and window bounds persist correctly. |
| Auto launch | Confirm behavior in packaged MSIX; keep disabled if Store policy rejects it. |
| Tray/menu | Confirm tray and window menu behavior after install. |

## EXE fallback

Local EXE packaging remains:

```powershell
cd frontend
npm run dist
```

The Azure Trusted Signing EXE workflow is manual fallback only. It should not
run on `main` push and should not be used for Microsoft Store submission unless
you choose to pay for trusted EXE signing later.

## Troubleshooting

Missing Store variables:

Set `MSIX_IDENTITY_NAME`, `MSIX_PUBLISHER`, and
`MSIX_PUBLISHER_DISPLAY_NAME` in GitHub Actions Variables.

Store package creation failure:

Check the electron-builder Store package config, Windows runner logs, and generated
manifest values.

Identity mismatch:

Use the package identity and publisher values shown in Partner Center for the
reserved MileDay app.

Store upload rejection:

Check Partner Center package identity, Store logo requirements, restricted
capabilities, and any Electron features that behave differently under MSIX.

Electron runtime difference:

Test app data persistence, safeStorage, tray/menu behavior, frameless window
behavior, and auto launch after installing the MSIX package.
