const defaultTheme = require('tailwindcss/defaultTheme');

/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './app/templates/**/*.html',
    './app/static/src/**/*.js',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', ...defaultTheme.fontFamily.sans],
      },
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#4A90E2',
          600: '#3b82f6',
          700: '#2563eb',
          800: '#1d4ed8',
          900: '#1e3a8a',
          DEFAULT: '#4A90E2',
          dark: '#3b82f6',
        },
        secondary: {
          50: '#ecfeff',
          100: '#cffafe',
          200: '#a5f3fc',
          300: '#67e8f9',
          400: '#22d3ee',
          500: '#50E3C2',
          600: '#06b6d4',
          700: '#0891b2',
          800: '#0e7490',
          900: '#155e75',
          DEFAULT: '#50E3C2',
          dark: '#06b6d4',
        },
        'background-light': '#F7F9FB',
        'background-dark': '#1A202C',
        'card-light': '#FFFFFF',
        'card-dark': '#2D3748',
        'text-light': '#2D3748',
        'text-dark': '#E2E8F0',
        'text-muted-light': '#A0AEC0',
        'text-muted-dark': '#718096',
        'border-light': '#E2E8F0',
        'border-dark': '#4A5568',
      },
    },
  },
  plugins: [],
}
