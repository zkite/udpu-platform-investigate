THEMES = {
    "dark": {
        "primary": "#22d3ee",
        "background": "#0a0f1a",
        "surface": "#0d1524",
        "surface_alt": "#111a2b",
        "text": "#e4e7ec",
        "muted": "#8b95a7",
        "border": "#182132",
        "danger": "#f06b68",
        "success": "#3dd598",
        "glow": "0 0 20px rgba(34,211,238,0.25)",
        "accent": "#3a7bff"
    },
    "light": {
        "primary": "#0ea5e9",
        "background": "#f8fafc",
        "surface": "#ffffff",
        "surface_alt": "#f1f5f9",
        "text": "#0f172a",
        "muted": "#475569",
        "border": "#e2e8f0",
        "danger": "#ef4444",
        "success": "#10b981",
        "glow": "0 0 12px rgba(14,165,233,0.2)",
        "accent": "#22d3ee"
    }
}

SPACING = {
    "xs": "8px",
    "sm": "12px",
    "md": "16px",
    "lg": "24px"
}

RADII = {
    "sm": "6px",
    "md": "12px"
}

SHADOWS = {
    "card": "0 8px 24px rgba(0,0,0,0.15)"
}


def get_colors(theme):
    return THEMES.get(theme, THEMES["dark"])


def theme_style(theme):
    colors = get_colors(theme)
    surface_alt = colors.get("surface_alt", colors["surface"])
    accent = colors.get("accent", colors["primary"])
    glow = colors.get("glow", "0 0 20px rgba(0,0,0,0.15)")
    is_dark = theme == "dark"
    return f"""
<style>
:root {{
  --max-width: 1240px;
  --primary: {colors['primary']};
  --surface: {colors['surface']};
  --surface-strong: {surface_alt};
  --background: {colors['background']};
  --text: {colors['text']};
  --muted: {colors['muted']};
  --border: {colors['border']};
  --danger: {colors['danger']};
  --success: {colors['success']};
  --accent: {accent};
    --panel: {"rgba(255,255,255,0.04)" if is_dark else "rgba(15,23,42,0.03)"};
  --panel-strong: {"rgba(255,255,255,0.06)" if is_dark else "rgba(15,23,42,0.05)"};
  --code-bg: {"#0b1220" if is_dark else "#edf2f7"};
  --code-border: {"#1e293b" if is_dark else "#e2e8f0"};
  --shadow-soft: {"0 18px 40px rgba(0,0,0,0.38)" if is_dark else "0 14px 38px rgba(15,23,42,0.14)"};
  --shadow-strong: {"0 26px 70px rgba(0,0,0,0.46)" if is_dark else "0 24px 72px rgba(15,23,42,0.18)"};
  --shadow-glow: {glow};
  --glass: {"rgba(15,23,42,0.7)" if is_dark else "rgba(255,255,255,0.9)"};
  --glass-border: {"rgba(255,255,255,0.06)" if is_dark else "rgba(15,23,42,0.06)"};
  --gradient-1: {colors['background']};
  --gradient-2: {colors['background']};
  --ring: {"rgba(139,123,255,0.35)" if is_dark else "rgba(59,130,246,0.35)"};
  --spacing-xs: {SPACING['xs']};
  --spacing-sm: {SPACING['sm']};
  --spacing-md: {SPACING['md']};
  --spacing-lg: {SPACING['lg']};
  --radius-sm: {RADII['sm']};
  --radius-md: {RADII['md']};
  --shadow-card: {SHADOWS['card']};
}}
</style>
"""
