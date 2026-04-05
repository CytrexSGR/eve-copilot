/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#0d1117',
        foreground: '#e6edf3',
        card: {
          DEFAULT: '#161b22',
          foreground: '#e6edf3',
        },
        popover: {
          DEFAULT: '#161b22',
          foreground: '#e6edf3',
        },
        primary: {
          DEFAULT: '#58a6ff',
          foreground: '#0d1117',
        },
        secondary: {
          DEFAULT: '#21262d',
          foreground: '#e6edf3',
        },
        muted: {
          DEFAULT: '#21262d',
          foreground: '#8b949e',
        },
        accent: {
          DEFAULT: '#21262d',
          foreground: '#e6edf3',
        },
        destructive: {
          DEFAULT: '#f85149',
          foreground: '#e6edf3',
        },
        success: {
          DEFAULT: '#3fb950',
          foreground: '#0d1117',
        },
        warning: {
          DEFAULT: '#d29922',
          foreground: '#0d1117',
        },
        border: '#30363d',
        input: '#21262d',
        ring: '#58a6ff',
      },
      borderRadius: {
        lg: '0.5rem',
        md: '0.375rem',
        sm: '0.25rem',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}
