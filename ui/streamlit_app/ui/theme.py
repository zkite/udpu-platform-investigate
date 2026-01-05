THEMES = {
    "dark": {
        "primary": "#6DC7FF",
        "background": "#0B111A",
        "surface": "#111926",
        "text": "#E7EDF5",
        "muted": "#9BA6B7",
        "border": "#1E2A3A",
        "danger": "#F87171",
        "success": "#34D399"
    },
    "light": {
        "primary": "#1F7FD1",
        "background": "#F6F8FC",
        "surface": "#FFFFFF",
        "text": "#0D1B2A",
        "muted": "#69748A",
        "border": "#D5DEEA",
        "danger": "#DC2626",
        "success": "#0EA371"
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
    return f"""
<style>
:root {{
  --max-width: 1320px;
  --primary: {colors['primary']};
  --surface: {colors['surface']};
  --background: {colors['background']};
  --text: {colors['text']};
  --muted: {colors['muted']};
  --border: {colors['border']};
  --danger: {colors['danger']};
  --success: {colors['success']};
  --panel: rgba(255,255,255,0.02);
  --code-bg: {"#0D1624" if theme == "dark" else "#F0F4FA"};
  --code-border: {"#1E2A3D" if theme == "dark" else "#D5DEEA"};
  --shadow-soft: {"0 20px 60px rgba(0,0,0,0.35)" if theme == "dark" else "0 20px 60px rgba(15,27,42,0.18)"};
  --shadow-strong: {"0 25px 80px rgba(0,0,0,0.45)" if theme == "dark" else "0 25px 80px rgba(15,27,42,0.22)"};
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
