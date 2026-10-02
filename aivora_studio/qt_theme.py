"""Centralized theme tokens for the PySide6 interface."""


THEME = {
    "background": "#101218",
    "surface": "#181b22",
    "surface_raised": "#20242d",
    "text": "#F3F4F6",
    "muted": "#9CA3AF",
    "accent": "#7957FF",
    "accent_hover": "#9278FF",
    "border": "#303541",
}


def build_stylesheet():

    return f"""
        QWidget {{
            color: {THEME["text"]};
            font-family: "Segoe UI";
            font-size: 10pt;
        }}
        QMainWindow, QWidget#appRoot {{
            background: {THEME["background"]};
        }}
        QFrame[card="true"] {{
            background: {THEME["surface"]};
            border: 1px solid {THEME["border"]};
            border-radius: 14px;
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
        QLineEdit {{
            background: {THEME["surface_raised"]};
            border: 1px solid {THEME["border"]};
            border-radius: 8px;
            padding: 10px 12px;
            selection-background-color: {THEME["accent"]};
        }}
        QLineEdit:focus {{
            border-color: {THEME["accent"]};
        }}
        QComboBox, QSpinBox {{
            background: {THEME["surface_raised"]};
            border: 1px solid {THEME["border"]};
            border-radius: 8px;
            padding: 8px 10px;
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
            border-radius: 9px;
            padding: 9px 14px;
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
            border-radius: 8px;
            padding: 8px 12px;
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
            border-radius: 14px;
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
    """
