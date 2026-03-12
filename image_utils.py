import cv2
from PIL import Image, ImageTk


def bgr_to_photoimage(frame, width, height):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return ImageTk.PhotoImage(Image.fromarray(rgb).resize((width, height), Image.LANCZOS))


def hsv_channels(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    h_scaled = cv2.convertScaleAbs(h, alpha=255.0 / 179.0)
    return (
        cv2.applyColorMap(h_scaled, cv2.COLORMAP_HSV),
        cv2.applyColorMap(s, cv2.COLORMAP_SUMMER),
        cv2.applyColorMap(v, cv2.COLORMAP_HOT),
    )


def preprocess(frame, mode: str):
    if mode == "gray":
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    if mode == "gaussian":
        return cv2.GaussianBlur(frame, (21, 21), 0)
    if mode == "median":
        return cv2.medianBlur(frame, 21)
    if mode == "hsv":
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    return frame.copy()