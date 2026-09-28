/** @type {import('tailwindcss').Config} */
// Endfield-style system: paper panels, black type, one yellow accent.
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        paper: { DEFAULT: '#f1f1ee', 2: '#e6e6e2', 3: '#d9d9d4' },
        ink: { DEFAULT: '#141517', 2: '#1d1e21', 3: '#2a2b2f' },
        sub: '#5e6065',
        faint: '#96989d',
        hair: 'rgba(20,21,23,0.12)',
        acc: { DEFAULT: '#ffe100', dim: '#d9bf00' },
        ok: '#1f9d55',
        bad: '#e5484d',
        info: '#2a9fbf',
      },
      fontFamily: {
        sans: ['Barlow', 'system-ui', 'sans-serif'],
        cond: ['"Barlow Condensed"', 'Barlow', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      keyframes: {
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in': {
          from: { opacity: '0', transform: 'translateX(12px)' },
          to: { opacity: '1', transform: 'translateX(0)' },
        },
        'cut-in': {
          '0%': { opacity: '0', transform: 'translateX(-80px)' },
          '14%': { opacity: '1', transform: 'translateX(0)' },
          '86%': { opacity: '1', transform: 'translateX(0)' },
          '100%': { opacity: '0', transform: 'translateX(80px)' },
        },
        blink: { '0%, 100%': { opacity: '1' }, '50%': { opacity: '0.25' } },
        scan: { from: { transform: 'translateX(-100%)' }, to: { transform: 'translateX(100%)' } },
        draw: { from: { strokeDashoffset: '1' }, to: { strokeDashoffset: '0' } },
        'pop-in': {
          from: { opacity: '0', transform: 'scale(0.96)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
      },
      animation: {
        'fade-up': 'fade-up 0.25s ease-out both',
        'slide-in': 'slide-in 0.25s ease-out both',
        'cut-in': 'cut-in 1.9s cubic-bezier(.2,.8,.2,1) both',
        blink: 'blink 1.1s steps(2) infinite',
        scan: 'scan 1.4s linear infinite',
        draw: 'draw 1.4s cubic-bezier(.3,.7,.2,1) both',
        'pop-in': 'pop-in 0.22s ease-out both',
      },
    },
  },
  plugins: [],
};
