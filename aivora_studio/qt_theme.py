"""Shared, runtime-adjustable theme and density tokens for the Qt preview."""


THEME_PRESETS = {
    "Sombre · Violet": {
        "background": "#101218",
        "surface": "#181B22",
        "surface_raised": "#20242D",
        "text": "#F3F4F6",
        "muted": "#9CA3AF",
        "accent": "#7957FF",
        "accent_hover": "#9278FF",
        "border": "#303541",
    },
    "Sombre · Bleu": {
        "background": "#10151B",
        "surface": "#19212B",
        "surface_raised": "#232E3B",
        "text": "#F3F6FA",
        "muted": "#A2AFBE",
        "accent": "#3988FF",
        "accent_hover": "#6BA6FF",
        "border": "#354354",
    },
    "Clair · Violet": {
        "background": "#F2F3F7",
        "surface": "#FFFFFF",
        "surface_raised": "#E9EAF0",
        "text": "#20222A",
        "muted": "#686D7A",
        "accent": "#6848E8",
        "accent_hover": "#8065F0",
        "border": "#D5D7E0",
    },
    "Clair · Vert": {
        "background": "#F1F5F2",
        "surface": "#FFFFFF",
        "surface_raised": "#E6EEE8",
        "text": "#202822",
        "muted": "#65736A",
        "accent": "#258454",
        "accent_hover": "#399967",
        "border": "#D1DDD4",
    },
}

THEME = dict(THEME_PRESETS["Sombre · Violet"])

DENSITY_PRESETS = {
    "Confortable": {
        "scale": 1.0,
        "radius": 12,
        "control_padding": 9,
        "field_padding": 10,
    },
    "Compacte": {
        "scale": 0.78,
        "radius": 8,
        "control_padding": 6,
        "field_padding": 7,
    },
}

DENSITY = dict(DENSITY_PRESETS["Confortable"])


def apply_theme(name):

    if name not in THEME_PRESETS:
        raise ValueError(f"Thème inconnu : {name}")
    THEME.clear()
    THEME.update(THEME_PRESETS[name])


def apply_density(name):

    if name not in DENSITY_PRESETS:
        raise ValueError(f"Densité inconnue : {name}")
    DENSITY.clear()
    DENSITY.update(DENSITY_PRESETS[name])


def build_stylesheet():

    return f"""
        QWidget {{
            color: {THEME["text"]};
            font-family: "Segoe UI";
            font-size: 10pt;
        }}
        QMainWindow, QWidget#appRoot, QDialog {{
            background: {THEME["background"]};
        }}
        QFrame[card="true"] {{
            background: {THEME["surface"]};
            border: 1px solid {THEME["border"]};
            border-radius: {DENSITY["radius"]}px;
        }}
        QLabel[role="muted"] {{
            color: {THEME["muted"]};
        }}
        QLabel[role="eyebrow"] {{
            color: {THEME["muted"]};
            font-size: 8pt;
            font-weight: 700;
            letter-spacing: 1px;
        }}
        QLabel[role="title"] {{
            font-size: 18pt;
            font-weight: 700;
        }}
        QLabel[role="subtitle"] {{
            font-size: 11pt;
            font-weight: 600;
        }}
        QLabel[role="coverPlaceholder"] {{
            background: {THEME["surface_raised"]};
            border-radius: {DENSITY["radius"]}px;
            color: {THEME["muted"]};
            font-weight: 600;
        }}
        QLineEdit {{
            background: {THEME["surface_raised"]};
            border: 1px solid {THEME["border"]};
            border-radius: {max(5, DENSITY["radius"] - 3)}px;
            padding: {DENSITY["field_padding"]}px 12px;
            selection-background-color: {THEME["accent"]};
        }}
        QLineEdit:focus {{
            border-color: {THEME["accent"]};
        }}
        QComboBox, QSpinBox {{
            background: {THEME["surface_raised"]};
            border: 1px solid {THEME["border"]};
            border-radius: {max(5, DENSITY["radius"] - 3)}px;
            padding: {DENSITY["control_padding"]}px 10px;
            min-height: 20px;
        }}
        QComboBox:hover, QSpinBox:hover {{
            border-color: {THEME["accent_hover"]};
        }}
        QComboBox QAbstractItemView {{
            background: {THEME["surface_raised"]};
            border: 1px solid {THEME["border"]};
            selection-background-color: {THEME["accent"]};
        }}
        QCheckBox {{
            spacing: 9px;
            padding: 4px 2px;
        }}
        QCheckBox::indicator {{
            width: 17px;
            height: 17px;
            border: 1px solid {THEME["border"]};
            border-radius: 5px;
            background: {THEME["surface_raised"]};
        }}
        QCheckBox::indicator:checked {{
            background: {THEME["accent"]};
            border-color: {THEME["accent"]};
        }}
        QPushButton {{
            background: {THEME["surface_raised"]};
            border: 1px solid {THEME["border"]};
            border-radius: {max(5, DENSITY["radius"] - 2)}px;
            padding: {DENSITY["control_padding"]}px 14px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            border-color: {THEME["accent_hover"]};
            background: {THEME["surface"]};
        }}
        QPushButton[primary="true"] {{
            background: {THEME["accent"]};
            border-color: {THEME["accent"]};
            color: white;
        }}
        QPushButton[primary="true"]:hover {{
            background: {THEME["accent_hover"]};
        }}
        QToolButton[trackType="true"] {{
            background: {THEME["surface_raised"]};
            border: 1px solid {THEME["border"]};
            border-radius: {max(5, DENSITY["radius"] - 3)}px;
            padding: {DENSITY["control_padding"]}px 12px;
            font-weight: 700;
        }}
        QToolButton[trackType="true"]:checked {{
            background: {THEME["accent"]};
            border-color: {THEME["accent"]};
            color: white;
        }}
        QFrame#dropZone {{
            background: {THEME["surface"]};
            border: 1px dashed {THEME["accent"]};
            border-radius: {DENSITY["radius"]}px;
        }}
        QScrollArea {{
            background: transparent;
        }}
        QScrollBar:vertical {{
            background: {THEME["background"]};
            width: 9px;
            margin: 3px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {THEME["border"]};
            min-height: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {THEME["muted"]};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QSlider::groove:horizontal {{
            height: 5px;
            background: {THEME["surface_raised"]};
            border-radius: 2px;
        }}
        QSlider::sub-page:horizontal {{
            background: {THEME["accent"]};
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            width: 13px;
            margin: -5px 0;
            border-radius: 6px;
            background: {THEME["text"]};
        }}
    """
