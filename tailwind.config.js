/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './app/templates/**/*.html',
    './app/static/src/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        'primary': '#4A90E2',
        'primary-dark': '#3b82f6',
        'secondary': '#50E3C2',
        'secondary-dark': '#06b6d4',
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
