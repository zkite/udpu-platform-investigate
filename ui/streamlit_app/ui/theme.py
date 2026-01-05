THEMES = {
    "dark": {
        "primary": "#6AD1E3",
        "background": "#0E1117",
        "surface": "#1B2430",
        "text": "#E5E7EB",
        "muted": "#9CA3AF",
        "border": "#2D3748",
        "danger": "#EF4444",
        "success": "#10B981"
    },
    "light": {
        "primary": "#2A8C9D",
        "background": "#F6F7FB",
        "surface": "#FFFFFF",
        "text": "#1F2937",
        "muted": "#6B7280",
        "border": "#E5E7EB",
        "danger": "#DC2626",
        "success": "#059669"
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
  --max-width: 1280px;
  --primary: {colors['primary']};
  --surface: {colors['surface']};
  --background: {colors['background']};
  --text: {colors['text']};
  --muted: {colors['muted']};
  --border: {colors['border']};
  --danger: {colors['danger']};
  --success: {colors['success']};
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
