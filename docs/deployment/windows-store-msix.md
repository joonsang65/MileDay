# MileDay MSIX Store migration

This guide covers moving the current Microsoft Store listing content from the
existing EXE/MSI product to an MSIX submission without rewriting the store
description, screenshots, or logo assets by hand.

The important constraint is simple: Partner Center does not expose a one-click
switch from EXE/MSI to MSIX in the same submission. Plan on either a new MSIX
product or a support-assisted package-type change if Microsoft enables that for
your account. In either case, keep the listing content by exporting and
re-importing it.

MSIX upload is the correct Store path for this repo because Microsoft Store can
sign the package during certification. Azure Trusted Signing is not part of the
Store path described here.

## What to preserve

Keep the existing Store listing content by exporting it first:

| Item | Keep by |
| --- | --- |
| Description | Store listing export/import |
| Screenshots | Store listing export/import |
| Store logo | Store listing export/import |
| Short description | Store listing export/import |
| Product features | Store listing export/import |
| Supported languages | Store listing export/import |

## Local Store build

Set the package identity values in your shell, then run the Store build.

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

The Store package file is written to `frontend/release-store` as a
`.msixupload` file.

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

The workflow intentionally uploads only a GitHub Actions artifact. It does not
create a GitHub Release, so the Store submission remains a manual Partner
Center step.

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

1. Export the current Store listing from the existing product.
2. Save the CSV and its asset folder as UTF-8.
3. Create or open the MSIX product in Partner Center. If the existing product still
   shows EXE/MSI, create the MSIX product first or use a support-assisted
   package-type change.
4. Import the exported Store listing CSV and assets.
5. Open the `Windows Store Package Release` workflow run on `main`.
6. Download the `mileday-store-package-X.Y.Z` artifact.
7. Confirm the Actions summary SHA256 matches the downloaded `.msixupload`.
8. Upload the `.msixupload` package in the Partner Center `Packages` page.
9. Submit for certification.
10. After certification, Microsoft Store signs and publishes the package.

If you are still on the EXE/MSI product screen, do not use the `Package URL`
field. That screen is for MSI/EXE submissions only. MSIX uses the file upload
path in the Packages page.

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
