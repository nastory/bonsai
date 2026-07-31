import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  // Course.thumbnailUrl is a Tailwind gradient class pair (e.g.
  // "from-emerald-950 to-emerald-800") chosen server-side (backend/seed.py,
  // course_generation.py), so it never appears literally in any file this
  // config's `content` glob scans. Tailwind's JIT can't generate CSS for a
  // class it never sees in source, so every value currently in use has to
  // be listed here explicitly, or the thumbnail renders as blank/transparent.
  safelist: [
    'from-emerald-950',
    'to-emerald-800',
    'from-violet-950',
    'to-indigo-900',
    'from-stone-500',
    'to-stone-700',
  ],
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
