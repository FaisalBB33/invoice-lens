import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#17211b",
        cream: "#f5f1e8",
        sage: "#dce7d7",
        forest: "#246247",
        coral: "#e96b4b",
      },
      boxShadow: {
        card: "0 24px 70px rgba(23, 33, 27, 0.10)",
      },
    },
  },
  plugins: [],
};

export default config;

