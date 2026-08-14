import { defineConfig } from "electron-vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

const rootDir = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  main: {
    build: {
      externalizeDeps: true,
      rollupOptions: {
        input: {
          main: resolve(rootDir, "electron/main.ts"),
        },
      },
    },
  },
  preload: {
    build: {
      externalizeDeps: true,
      rollupOptions: {
        input: {
          preload: resolve(rootDir, "electron/preload.ts"),
        },
      },
    },
  },
  renderer: {
    root: ".",
    plugins: [react()],
    build: {
      rollupOptions: {
        input: resolve(rootDir, "index.html"),
      },
    },
    resolve: {
      alias: {
        "@": resolve(rootDir, "src"),
      },
    },
    server: {
      port: 5173,
    },
  },
});
