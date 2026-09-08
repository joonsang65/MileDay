/* global process */

const packageJson = require("./package.json");

const requiredEnv = [
  "MSIX_IDENTITY_NAME",
  "MSIX_PUBLISHER",
  "MSIX_PUBLISHER_DISPLAY_NAME",
];

const optionalEnv = {
  applicationId: process.env.MSIX_APPLICATION_ID,
  backgroundColor: process.env.MSIX_BACKGROUND_COLOR,
};

const missing = requiredEnv.filter((name) => !process.env[name]);

if (missing.length > 0) {
  throw new Error(`Missing MSIX Store configuration: ${missing.join(", ")}`);
}

module.exports = {
  ...packageJson.build,
  directories: {
    ...packageJson.build.directories,
    output: "release-store",
  },
  win: {
    ...packageJson.build.win,
    target: [
      {
        target: "msix",
        arch: ["x64"],
      },
    ],
    artifactName: "${productName}-Store-${version}-${arch}.${ext}",
  },
  msix: {
    identityName: process.env.MSIX_IDENTITY_NAME,
    publisher: process.env.MSIX_PUBLISHER,
    publisherDisplayName: process.env.MSIX_PUBLISHER_DISPLAY_NAME,
    displayName: packageJson.productName,
    languages: ["ko-KR", "en-US"],
    createMsixupload: true,
    artifactName: "${productName}-Store-${version}-${arch}.${ext}",
    ...(optionalEnv.applicationId
      ? { applicationId: optionalEnv.applicationId }
      : {}),
    ...(optionalEnv.backgroundColor
      ? { backgroundColor: optionalEnv.backgroundColor }
      : {}),
  },
};
