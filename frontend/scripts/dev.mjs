import { spawn } from "node:child_process";

const env = { ...process.env };
delete env.ELECTRON_RUN_AS_NODE;

const command = process.platform === "win32" ? "cmd.exe" : "electron-vite";
const args =
  process.platform === "win32"
    ? ["/d", "/s", "/c", "electron-vite dev"]
    : ["dev"];

const child = spawn(command, args, {
  stdio: "inherit",
  env,
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 0);
});
