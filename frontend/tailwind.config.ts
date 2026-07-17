import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0b0f19",
        surface: "#141a29",
        textPrimary: "#f8fafc",
        primary: {
          DEFAULT: "#38bdf8",
          hover: "#0ea5e9",
        },
        "neutral-border": "#2a354c",
      },
      fontFamily: {
        serif: ["var(--font-eb-garamond)", "serif"],
        sans: ["var(--font-space-grotesk)", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "monospace"],
      },
      borderRadius: {
        sm: "2px",
        DEFAULT: "4px",
        md: "4px",
        lg: "4px",
        xl: "4px",
        "2xl": "4px",
        "3xl": "4px",
        full: "9999px",
      },
    },
  },
  plugins: [],
};
export default config;
