import { readFileSync } from "node:fs";

const tagName =
  process.env.GITHUB_REF_NAME ?? process.env.RELEASE_TAG ?? process.argv[2];

if (!tagName) {
  fail("Release tag is required. Set GITHUB_REF_NAME, RELEASE_TAG, or pass it as an argument.");
}

if (!/^v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$/.test(tagName)) {
  fail(`Release tag must look like vX.Y.Z. Received: ${tagName}`);
}

const packageJson = JSON.parse(readFileSync("package.json", "utf8"));
const tagVersion = tagName.slice(1);

if (packageJson.version !== tagVersion) {
  fail(
    `Release version mismatch. Tag ${tagName} requires package.json version ${tagVersion}, but found ${packageJson.version}.`
  );
}

console.log(`Release version verified: ${tagName} matches package.json ${packageJson.version}.`);

function fail(message) {
  console.error(message);
  process.exit(1);
}
