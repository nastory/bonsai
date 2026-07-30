import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bonsai: {
          green: '#1B4332',
          'green-hover': '#2D6A4F',
          cream: '#FAF8F5',
          border: '#E8E4DC',
          text: '#1F2421',
          'text-muted': '#6B7280',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'sans-serif',
        ],
      },
    },
  },
  plugins: [],
} satisfies Config;
