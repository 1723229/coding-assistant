/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Custom dark theme colors
        'editor-bg': '#1e1e2e',
        'editor-sidebar': '#181825',
        'editor-panel': '#11111b',
        'editor-border': '#313244',
        'editor-text': '#cdd6f4',
        'editor-muted': '#6c7086',
        'editor-accent': '#89b4fa',
        'editor-success': '#a6e3a1',
        'editor-warning': '#f9e2af',
        'editor-error': '#f38ba8',
      },
      fontFamily: {
        'mono': ['JetBrains Mono', 'Fira Code', 'monospace'],
        'sans': ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

