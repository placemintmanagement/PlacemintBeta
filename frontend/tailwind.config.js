/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],
    theme: {
        extend: {
            colors: {
                // Teal / lime / white design language (2026-10), strict
                // palette -- no red/orange/coral anywhere. "secondary" keeps
                // a semantic fail/attention role (test failures, cutoffs
                // missed, unverified badges) but is ink, not a hue: it reads
                // as "attention" by being the darkest/boldest text color,
                // since lime already means "highlight/positive" and no
                // other hue is in the approved palette.
                pm: {
                    bg: "#0F6F7A",
                    surface: "#FFFFFF",
                    muted: "#E3EFEF",
                    primary: "#0F6F7A",
                    "primary-dark": "#0A5760",
                    secondary: "#0B2A30",
                    text: "#0B2A30",
                    text2: "#52696E",
                    "text-muted": "#8CA3A8",
                    editor: "#0F111A",
                    border: "rgba(11,42,48,0.10)",
                    lime: "#C6F24E",
                    "lime-dark": "#AEDB3A",
                    ink: "#0B2A30",
                },
                background: "hsl(var(--background))",
                foreground: "hsl(var(--foreground))",
                card: {
                    DEFAULT: "hsl(var(--card))",
                    foreground: "hsl(var(--card-foreground))",
                },
                primary: {
                    DEFAULT: "hsl(var(--primary))",
                    foreground: "hsl(var(--primary-foreground))",
                },
                secondary: {
                    DEFAULT: "hsl(var(--secondary))",
                    foreground: "hsl(var(--secondary-foreground))",
                },
                muted: {
                    DEFAULT: "hsl(var(--muted))",
                    foreground: "hsl(var(--muted-foreground))",
                },
                accent: {
                    DEFAULT: "hsl(var(--accent))",
                    foreground: "hsl(var(--accent-foreground))",
                },
                destructive: {
                    DEFAULT: "hsl(var(--destructive))",
                    foreground: "hsl(var(--destructive-foreground))",
                },
                border: "hsl(var(--border))",
                input: "hsl(var(--input))",
                ring: "hsl(var(--ring))",
            },
            fontFamily: {
                // Reads --pm-font-display (index.css :root) so the typeface
                // has one definition, not one hardcoded here and another
                // hardcoded per component.
                display: ["var(--pm-font-display)", "system-ui", "sans-serif"],
                sans: ["Inter", "system-ui", "sans-serif"],
                mono: ["JetBrains Mono", "ui-monospace", "monospace"],
            },
            borderRadius: {
                xl: "16px",
                lg: "12px",
                md: "8px",
                sm: "6px",
            },
            keyframes: {
                shake: {
                    "0%, 100%": { transform: "translateX(0)" },
                    "20%": { transform: "translateX(-4px)" },
                    "40%": { transform: "translateX(4px)" },
                    "60%": { transform: "translateX(-3px)" },
                    "80%": { transform: "translateX(3px)" },
                },
            },
            animation: {
                shake: "shake 0.4s ease-in-out",
            },
        },
    },
    plugins: [require("tailwindcss-animate")],
};
