/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        uma: {
          pink: '#FF6E91',
          gold: '#FFD700',
          green: '#2ECC71',
          blue: '#3498DB',
          dark: '#1A1A2E',
          card: '#24243E',
        }
      },
      fontFamily: {
        arcade: ['"Press Start 2P"', 'monospace'],
        anime: ['"Nunito"', 'sans-serif'],
      },
      animation: {
        'pulse-fast': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-subtle': 'bounce 2s infinite',
      }
    },
  },
  plugins: [],
}
