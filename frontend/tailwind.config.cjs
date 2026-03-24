/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        apple: {
          bg: '#F5F5F7',
          text: '#1D1D1F',
          blue: '#0066CC',
          gray: '#86868B',
          card: '#FFFFFF',
          border: '#D2D2D7',
        },
        tv: {
          deep: '#131722',
          panel: '#1E222D',
          card: '#2A2E39',
          blue: '#2962FF',
          green: '#089981',
          red: '#F23645',
          text: '#D1D4DC',
          label: '#787B86',
          border: '#363A45',
        }
      },
      fontFamily: {
        sans: ['Inter', 'SF Pro Text', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'apple-soft': '0 8px 32px 0 rgba(0, 0, 0, 0.08)',
      }
    },
  },
  plugins: [],
}
