/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
          subtle: "hsl(var(--card-subtle))",
        },
        ai: "hsl(var(--color-ai))",
        status: {
          extracted: "hsl(var(--status-extracted))",
          matched: "hsl(var(--status-matched))",
          unmatched: "hsl(var(--status-unmatched))",
          review: "hsl(var(--status-review))",
          validated: "hsl(var(--status-validated))",
          approved: "hsl(var(--status-approved))",
          rejected: "hsl(var(--status-rejected))",
          hold: "hsl(var(--status-hold))",
          warning: "hsl(var(--status-warning))",
          error: "hsl(var(--status-error))",
          corroborates: "hsl(var(--status-corroborates))",
          contradicts: "hsl(var(--status-contradicts))",
        },
        prov: {
          ai: "hsl(var(--prov-ai))",
          schedule: "hsl(var(--prov-schedule))",
          engineer: "hsl(var(--prov-engineer))",
          supervisor: "hsl(var(--prov-supervisor))",
        },
        disc: {
          civil: "hsl(var(--disc-civil))",
          piping: "hsl(var(--disc-piping))",
          equip: "hsl(var(--disc-equip))",
          elec: "hsl(var(--disc-elec))",
          inst: "hsl(var(--disc-inst))",
          hse: "hsl(var(--disc-hse))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [],
}
