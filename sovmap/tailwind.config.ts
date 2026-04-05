import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{js,ts,jsx,tsx,mdx}', './components/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        gray: {
          800: '#1e293b',
          900: '#0f172a',
        },
      },
    },
  },
  plugins: [],
};

export default config;
