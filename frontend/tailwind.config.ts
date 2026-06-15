import type { Config } from 'tailwindcss'
import animate from 'tailwindcss-animate'

const config: Config = {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      colors: {
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        border: 'hsl(var(--border))',
        ring: 'hsl(var(--ring))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        'trend-down': {
          DEFAULT: 'hsl(var(--trend-down))',
          muted: 'hsl(var(--trend-down-muted))',
        },
        'trend-same': {
          DEFAULT: 'hsl(var(--trend-same))',
          muted: 'hsl(var(--trend-same-muted))',
        },
        'trend-up': {
          DEFAULT: 'hsl(var(--trend-up))',
          muted: 'hsl(var(--trend-up-muted))',
        },
      },
    },
  },
  plugins: [animate],
}

export default config
