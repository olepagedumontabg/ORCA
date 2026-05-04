module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js",
  ],
  safelist: [
    'rotate-180', 'hidden', 'block', 'fa-bars', 'fa-times',
    'text-gray-300', 'cursor-not-allowed', 'text-text-light',
    'hover:text-text-dark', 'cursor-pointer',
    'bg-blue-50',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#001A70',
        'text-dark': '#2A314C',
        'text-light': '#4B5563',
      },
    },
  },
  plugins: [],
};
