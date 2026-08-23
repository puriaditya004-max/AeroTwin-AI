/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "#0A0E13",
        panel: "#121820",
        "panel-raised": "#1A222C",
        hairline: "#26303C",
        "text-primary": "#E8EDF2",
        "text-muted": "#7C8B9B",
        safe: "#3DDC84",
        caution: "#FFB020",
        warn: "#FF4D4D",
        data: "#4FD1E8",
      },
      fontFamily: {
        display: ["Space Grotesk", "sans-serif"],
        body: ["IBM Plex Sans", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
