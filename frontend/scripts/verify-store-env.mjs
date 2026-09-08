const required = [
  "MSIX_IDENTITY_NAME",
  "MSIX_PUBLISHER",
  "MSIX_PUBLISHER_DISPLAY_NAME",
];

const optionalValidators = [
  [
    "MSIX_APPLICATION_ID",
    /^[A-Za-z][A-Za-z0-9]*(?:\.[A-Za-z][A-Za-z0-9]*)*$/,
    "must contain alphanumeric dot-separated segments, each starting with a letter",
  ],
  [
    "MSIX_BACKGROUND_COLOR",
    /^#[0-9A-Fa-f]{6}$/,
    "must be a #RRGGBB color",
  ],
];

const missing = required.filter((name) => !process.env[name]);

if (missing.length > 0) {
  fail(`Missing MSIX Store environment variables: ${missing.join(", ")}`);
}

for (const [name, pattern, help] of optionalValidators) {
  const value = process.env[name];
  if (value && !pattern.test(value)) {
    fail(`${name} ${help}. Received: ${value}`);
  }
}

if (!/^[A-Za-z0-9.-]{3,50}$/.test(process.env.MSIX_IDENTITY_NAME)) {
  fail("MSIX_IDENTITY_NAME must be 3-50 characters and contain only letters, numbers, dots, or hyphens.");
}

if (!process.env.MSIX_PUBLISHER.startsWith("CN=")) {
  fail("MSIX_PUBLISHER must be the Partner Center package publisher subject, usually starting with CN=.");
}

console.log("MSIX Store environment variables are present.");

function fail(message) {
  console.error(message);
  process.exit(1);
}
