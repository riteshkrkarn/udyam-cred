/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  corePlugins: {
    preflight: false,
  },
  theme: {
    extend: {
      colors: {
        pine: { DEFAULT: "#244A3D", deep: "#1B3A30" },
        sage: "#E8EADB",
        paper: "#F7F6EE",
        wine: { DEFAULT: "#7A2431", deep: "#5E1B26" },
        ink: "#1E2A24",
        moss: "#46594F",
        rule: "#CBD0BC",
        ochre: { DEFAULT: "#9A6A17", tint: "#F1E6C8" },
      },
      fontFamily: {
        display: ['"Young Serif"', 'Georgia', 'serif'],
        sans: ['"Hanken Grotesk"', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
