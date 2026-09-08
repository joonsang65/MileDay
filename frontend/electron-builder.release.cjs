/* global process */

const packageJson = require("./package.json");

const requiredEnv = [
  "AZURE_TRUSTED_SIGNING_ENDPOINT",
  "AZURE_TRUSTED_SIGNING_ACCOUNT_NAME",
  "AZURE_TRUSTED_SIGNING_CERTIFICATE_PROFILE",
  "WINDOWS_PUBLISHER_NAME",
];

const missing = requiredEnv.filter((name) => !process.env[name]);

if (missing.length > 0) {
  throw new Error(
    `Missing Azure Trusted Signing configuration: ${missing.join(", ")}`
  );
}

module.exports = {
  ...packageJson.build,
  win: {
    ...packageJson.build.win,
    sign: {
      type: "azure",
      endpoint: process.env.AZURE_TRUSTED_SIGNING_ENDPOINT,
      codeSigningAccountName: process.env.AZURE_TRUSTED_SIGNING_ACCOUNT_NAME,
      certificateProfileName:
        process.env.AZURE_TRUSTED_SIGNING_CERTIFICATE_PROFILE,
      publisherName: process.env.WINDOWS_PUBLISHER_NAME,
    },
  },
};
