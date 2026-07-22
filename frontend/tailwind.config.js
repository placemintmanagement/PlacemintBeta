/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],
    theme: {
        extend: {
            colors: {
                pm: {
                    bg: "#FAF8F3",
                    surface: "#FFFFFF",
                    muted: "#F3F0E6",
                    primary: "#0FAE73",
                    "primary-dark": "#0C8B5C",
                    secondary: "#FF6F4D",
                    text: "#0A0A0A",
                    text2: "#4B5563",
                    editor: "#0F111A",
                    border: "rgba(10,10,10,0.10)",
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
                display: ["Outfit", "system-ui", "sans-serif"],
                sans: ["Inter", "system-ui", "sans-serif"],
                mono: ["JetBrains Mono", "ui-monospace", "monospace"],
            },
            borderRadius: {
                xl: "16px",
                lg: "12px",
                md: "8px",
                sm: "6px",
            },
        },
    },
    plugins: [require("tailwindcss-animate")],
};
