DISPLAY_W = 1280
DISPLAY_H = 460
PANEL_W = DISPLAY_W // 2
HSV_ROW_H = 200
HSV_PANE_W = DISPLAY_W // 3

MODES = ["gray", "gaussian", "median", "hsv"]
MODE_LABELS = {
    "gray": "1: Grayscale",
    "gaussian": "2: Gaussian Blur",
    "median": "3: Median Blur",
    "hsv": "4: HSV",
}

BG = "#fff4fb"
BG_DARK = "#ffe6f4"
PANEL_BG = "#fffafd"
BTN_BG = "#f7cfe4"
BTN_FG = "#6b2d52"
ACC = "#e78ab5"
ACC_HOVER = "#d96aa0"
SEP = "#f0bfd8"
TEXT_SOFT = "#8b5b76"
TEXT_DARK = "#5f2e49"
TITLE_LEFT = "#c05d8f"
TITLE_RIGHT = "#9b4d76"
MODE_DEFAULTS = {
    "gray": "#f8d7e8",
    "gaussian": "#edd7f8",
    "median": "#f8d7f1",
    "hsv": "#f8e3d7",
}

HSV_LABELS = ["H  —  Hue", "S  —  Saturation", "V  —  Value"]
HSV_COLORS = ["#c05d8f", "#8f7ac0", "#d28b5c"]
