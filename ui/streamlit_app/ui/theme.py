THEMES = {
    "dark": {
        "primary": "#8B7BFF",
        "background": "#070B14",
        "surface": "#0F1729",
        "surface_alt": "#101C33",
        "text": "#E8EDF7",
        "muted": "#95A4C4",
        "border": "#1E2A43",
        "danger": "#FF6B6B",
        "success": "#4ADE80",
        "glow": "0 0 30px rgba(139,123,255,0.35)",
        "accent": "#14D8C6"
    },
    "light": {
        "primary": "#3B82F6",
        "background": "#F5F7FB",
        "surface": "#FFFFFF",
        "surface_alt": "#F0F4FF",
        "text": "#0F172A",
        "muted": "#64748B",
        "border": "#D8E2F2",
        "danger": "#E11D48",
        "success": "#10B981",
        "glow": "0 0 20px rgba(59,130,246,0.25)",
        "accent": "#0EA5E9"
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
  --panel-strong: {"rgba(255,255,255,0.06)" if is_dark else "rgba(15,23,42,0.06)"};
  --code-bg: {"#0C1324" if is_dark else "#ECF2FF"};
  --code-border: {"#1E2A3D" if is_dark else "#D5DEEA"};
  --shadow-soft: {"0 18px 50px rgba(0,0,0,0.4)" if is_dark else "0 18px 50px rgba(15,27,42,0.16)"};
  --shadow-strong: {"0 28px 80px rgba(0,0,0,0.48)" if is_dark else "0 28px 80px rgba(15,27,42,0.22)"};
  --shadow-glow: {glow};
  --glass: {"rgba(17,24,39,0.55)" if is_dark else "rgba(255,255,255,0.78)"};
  --glass-border: {"rgba(255,255,255,0.08)" if is_dark else "rgba(15,23,42,0.08)"};
  --gradient-1: {"linear-gradient(135deg, #0E172C 0%, #101B33 50%, #0A1222 100%)" if is_dark else "linear-gradient(135deg, #FFFFFF 0%, #F6F9FF 60%, #ECF2FF 100%)"};
  --gradient-2: {"linear-gradient(120deg, rgba(139,123,255,0.2), rgba(20,216,198,0.1))" if is_dark else "linear-gradient(120deg, rgba(59,130,246,0.14), rgba(14,165,233,0.08))"};
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
