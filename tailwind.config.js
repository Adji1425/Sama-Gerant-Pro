/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './apps/**/templates/**/*.html',
  ],
  prefix: 'tw-',
  corePlugins: {
    preflight: false, // Bootstrap fournit déjà le reset CSS de base
  },
  theme: {
    extend: {},
  },
  plugins: [],
};
