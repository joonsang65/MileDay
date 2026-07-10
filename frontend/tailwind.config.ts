import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter",
          "Pretendard",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
      },
      colors: {
        ink: "#17202A",
        line: "#D8DEE8",
        paper: "#F7F8FA",
        field: "#FFFFFF",
        mint: "#0F766E",
        coral: "#E11D48",
        amber: "#D97706",
      },
    },
  },
  plugins: [],
} satisfies Config;
