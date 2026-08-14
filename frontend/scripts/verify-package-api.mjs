import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const outDir = join(process.cwd(), "out");
const productionApiBaseUrl = "https://mileday.onrender.com";
const blockedPatterns = [
  "http://localhost:8000",
  "http://127.0.0.1:8000",
  "https://localhost:8000",
  "https://127.0.0.1:8000",
];

if (!existsSync(outDir)) {
  fail("frontend/out does not exist. Run npm run build first.");
}

const files = listFiles(outDir);
const matches = {
  production: [],
  blocked: [],
};

for (const file of files) {
  const content = readFileSync(file, "utf8");

  if (content.includes(productionApiBaseUrl)) {
    matches.production.push(file);
  }

  for (const pattern of blockedPatterns) {
    if (content.includes(pattern)) {
      matches.blocked.push(`${file} -> ${pattern}`);
    }
  }
}

if (matches.blocked.length > 0) {
  fail(`Local API URL found in package output:\n${matches.blocked.join("\n")}`);
}

if (matches.production.length === 0) {
  fail(`Production API URL was not found in package output: ${productionApiBaseUrl}`);
}

console.log("Package API check passed.");

function listFiles(dir) {
  const entries = readdirSync(dir);
  const files = [];

  for (const entry of entries) {
    const path = join(dir, entry);
    const stats = statSync(path);

    if (stats.isDirectory()) {
      files.push(...listFiles(path));
    } else if (stats.isFile() && /\.(js|mjs|html|css|json)$/i.test(path)) {
      files.push(path);
    }
  }

  return files;
}

function fail(message) {
  console.error(message);
  process.exit(1);
}
