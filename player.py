import os
import threading
import time
import tkinter as tk
from tkinter import filedialog, ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

from audio_helper import AudioPlayer
from image_utils import bgr_to_photoimage, hsv_channels, preprocess
from ui_styles import (
    ACC,
    ACC_HOVER,
    BG,
    BG_DARK,
    BTN_BG,
    BTN_FG,
    DISPLAY_H,
    DISPLAY_W,
    HSV_COLORS,
    HSV_LABELS,
    HSV_PANE_W,
    HSV_ROW_H,
    MODE_DEFAULTS,
    MODE_LABELS,
    MODES,
    PANEL_BG,
    PANEL_W,
    SEP,
    TEXT_DARK,
    TEXT_SOFT,
    TITLE_LEFT,
    TITLE_RIGHT,
)


class VideoPlayer:
    def __init__(self, root: tk.Tk, initial_path: str = ""):
        self.root = root
        self.root.title("Video Processing Player")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self.cap = None
        self.total_frames = 0
        self.native_fps = 30.0
        self.frame_idx = 0
        self.paused = True
        self.mode = "gray"
        self.last_orig = None
        self.last_hsv = (None, None, None)

        self._stop_flag = threading.Event()
        self._play_thread = None
        self._dragging = False
        self._fps_t = time.time()
        self._fps_n = 0
        self._cur_fps = 0.0

        self.audio = AudioPlayer()
        self.audio_loaded = False

        self._build_ui()
        self._bind_keys()

        if initial_path and os.path.isfile(initial_path):
            self._load_file(initial_path)

    def _build_ui(self):
        self._main_row = tk.Frame(self.root, bg=BG, width=DISPLAY_W, height=DISPLAY_H)
        self._main_row.pack_propagate(False)
        self._main_row.pack(padx=10, pady=(10, 6))

        self._cv_orig = self._make_canvas(self._main_row, 0, PANEL_W, DISPLAY_H)
        self._cv_proc = self._make_canvas(self._main_row, PANEL_W, PANEL_W, DISPLAY_H)
        self._ci_orig = self._cv_orig.create_image(0, 0, anchor=tk.NW)
        self._ci_proc = self._cv_proc.create_image(0, 0, anchor=tk.NW)

        tk.Frame(self._main_row, bg=SEP, width=2, height=DISPLAY_H).place(x=PANEL_W - 1, y=0)

        self._lbl_orig_title = tk.Label(
            self._main_row,
            text="Original",
            bg=BG,
            fg=TITLE_LEFT,
            font=("Segoe UI", 11, "bold"),
        )
        self._lbl_orig_title.place(x=10, y=8)

        self._proc_title = tk.StringVar(value="Processed")
        tk.Label(
            self._main_row,
            textvariable=self._proc_title,
            bg=BG,
            fg=TITLE_RIGHT,
            font=("Segoe UI", 11, "bold"),
        ).place(x=PANEL_W + 10, y=8)

        self._show_placeholder_main()

        self._hsv_row = tk.Frame(self.root, bg=BG, width=DISPLAY_W, height=HSV_ROW_H)
        self._hsv_row.pack_propagate(False)

        self._cv_hsv = []
        self._ci_hsv = []
        for index in range(3):
            canvas = self._make_canvas(self._hsv_row, index * HSV_PANE_W, HSV_PANE_W, HSV_ROW_H)
            image_id = canvas.create_image(0, 0, anchor=tk.NW)
            self._cv_hsv.append(canvas)
            self._ci_hsv.append(image_id)
            tk.Label(
                self._hsv_row,
                text=HSV_LABELS[index],
                bg=BG,
                fg=HSV_COLORS[index],
                font=("Segoe UI", 10, "bold"),
            ).place(x=index * HSV_PANE_W + 8, y=6)
            if index > 0:
                tk.Frame(self._hsv_row, bg=SEP, width=2, height=HSV_ROW_H).place(x=index * HSV_PANE_W - 1, y=0)

        self._show_placeholder_hsv()

        progress_wrap = tk.Frame(self.root, bg=BG)
        progress_wrap.pack(fill=tk.X, padx=18, pady=(0, 6))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Pink.Horizontal.TScale",
            background=BG,
            troughcolor="#f6d7e8",
            sliderlength=14,
            sliderrelief="flat",
            gripcount=0,
        )
        style.map("Pink.Horizontal.TScale", background=[("active", BG)])

        self._prog_var = tk.DoubleVar(value=0)
        progress = ttk.Scale(
            progress_wrap,
            from_=0,
            to=1000,
            orient=tk.HORIZONTAL,
            variable=self._prog_var,
            style="Pink.Horizontal.TScale",
            command=self._on_progress_move,
        )
        progress.pack(fill=tk.X)
        progress.bind("<ButtonPress-1>", lambda event: self._drag_start())
        progress.bind("<ButtonRelease-1>", lambda event: self._drag_end())

        self._info_var = tk.StringVar(value="No file loaded")
        tk.Label(
            self.root,
            textvariable=self._info_var,
            bg=BG,
            fg=TEXT_SOFT,
            font=("Segoe UI", 9),
        ).pack(pady=(0, 6))

        controls = tk.Frame(self.root, bg=BG)
        controls.pack(fill=tk.X, padx=18, pady=(0, 8))

        left = tk.Frame(controls, bg=BG)
        left.pack(side=tk.LEFT)

        center = tk.Frame(controls, bg=BG)
        center.pack(side=tk.LEFT, padx=18)

        right = tk.Frame(controls, bg=BG)
        right.pack(side=tk.RIGHT)

        self._btn_play = self._make_button(left, "▶ Play", self._toggle_play, bg=ACC, fg="#ffffff", activebackground=ACC_HOVER)
        self._make_button(left, "Open", self._open_file).pack(side=tk.LEFT, padx=(0, 6))
        self._make_button(left, "◀ Frame", self._step_back).pack(side=tk.LEFT, padx=6)
        self._btn_play.pack(side=tk.LEFT, padx=6)
        self._make_button(left, "Frame ▶", self._step_forward).pack(side=tk.LEFT, padx=6)

        self._mode_btns = {}
        for mode in MODES:
            button = self._make_button(center, MODE_LABELS[mode], lambda current=mode: self._set_mode(current), bg=MODE_DEFAULTS[mode])
            button.pack(side=tk.LEFT, padx=5)
            self._mode_btns[mode] = button
        self._update_mode_btns()

        tk.Label(right, text="Volume", bg=BG, fg=TEXT_DARK, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        self._vol_var = tk.DoubleVar(value=80)
        volume = ttk.Scale(
            right,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self._vol_var,
            length=120,
            style="Pink.Horizontal.TScale",
            command=self._on_volume,
        )
        volume.pack(side=tk.LEFT)
        self.audio.set_volume(0.8)

        self._status_var = tk.StringVar(value="No file loaded — click Open")
        tk.Label(
            self.root,
            textvariable=self._status_var,
            bg=BG_DARK,
            fg=TEXT_SOFT,
            font=("Segoe UI", 8),
            anchor=tk.W,
            padx=10,
            pady=6,
        ).pack(fill=tk.X, padx=12, pady=(0, 10))

    def _make_button(self, parent, text, command, **kwargs):
        params = dict(
            bg=BTN_BG,
            fg=BTN_FG,
            relief=tk.FLAT,
            font=("Segoe UI", 10),
            padx=10,
            pady=6,
            activebackground="#efbdd8",
            activeforeground=BTN_FG,
            cursor="hand2",
            borderwidth=0,
        )
        params.update(kwargs)
        return tk.Button(parent, text=text, command=command, **params)

    def _make_canvas(self, parent, x, width, height):
        canvas = tk.Canvas(parent, width=width, height=height, bg=PANEL_BG, highlightthickness=0)
        canvas.place(x=x, y=0, width=width, height=height)
        return canvas

    def _show_placeholder_main(self):
        image = Image.new("RGB", (PANEL_W, DISPLAY_H), (255, 250, 253))
        photo = ImageTk.PhotoImage(image)
        for canvas, image_id in ((self._cv_orig, self._ci_orig), (self._cv_proc, self._ci_proc)):
            canvas.itemconfig(image_id, image=photo)
            canvas._img = photo

    def _show_placeholder_hsv(self):
        image = Image.new("RGB", (HSV_PANE_W, HSV_ROW_H), (255, 250, 253))
        photo = ImageTk.PhotoImage(image)
        for canvas, image_id in zip(self._cv_hsv, self._ci_hsv):
            canvas.itemconfig(image_id, image=photo)
            canvas._img = photo

    def _bind_keys(self):
        self.root.bind("<space>", lambda event: self._toggle_play())
        self.root.bind("<Left>", lambda event: self._step_back())
        self.root.bind("<Right>", lambda event: self._step_forward())
        self.root.bind("<Escape>", lambda event: self._on_close())
        self.root.bind("<q>", lambda event: self._on_close())
        for key, mode in (("1", "gray"), ("2", "gaussian"), ("3", "median"), ("4", "hsv")):
            self.root.bind(key, lambda event, current=mode: self._set_mode(current))

    def _open_file(self):
        path = filedialog.askopenfilename(
            title="Select video",
            filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv *.wmv *.webm *.m4v"), ("All", "*.*")],
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str):
        self._stop_playback()
        if self.cap:
            self.cap.release()

        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            self._status_var.set(f"Error opening: {path}")
            return

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.native_fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.frame_idx = 0
        self.paused = True
        self._btn_play.config(text="▶ Play")

        filename = os.path.basename(path)
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.root.title(f"Video Processing Player — {filename}")
        self._status_var.set(f"{filename} | {width}x{height} | {self.total_frames} frames | {self.native_fps:.2f} fps")

        ok, frame = self.cap.read()
        if ok:
            self.frame_idx = 1
            self.last_orig = frame
            self.last_hsv = hsv_channels(frame)
            self._render()
            self._update_info()

        self.audio_loaded = False
        threading.Thread(target=self._load_audio, args=(path,), daemon=True).start()

    def _load_audio(self, path: str):
        loaded = self.audio.load(path, self.native_fps)
        self.audio_loaded = loaded

        vol = self._vol_var.get() / 100.0
        self.audio.set_volume(vol)

        if loaded and self.cap is not None and not self.paused:
            current_frame = self.frame_idx
            self.root.after(0, lambda: self.audio.play_from(current_frame))

    def _toggle_play(self):
        if self.cap is None:
            return
        self.paused = not self.paused
        self._btn_play.config(text="⏸ Pause" if not self.paused else "▶ Play")
        if not self.paused:
            if self.audio_loaded:
                self.audio.play_from(self.frame_idx)
            self._start_playback()
        else:
            self.audio.pause()

    def _start_playback(self):
        self._stop_flag.clear()
        self._fps_t = time.time()
        self._fps_n = 0
        self._play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self._play_thread.start()

    def _stop_playback(self):
        self._stop_flag.set()
        if self._play_thread and self._play_thread.is_alive():
            self._play_thread.join(timeout=1.0)

    def _play_loop(self):
        interval = 1.0 / self.native_fps
        while not self._stop_flag.is_set() and not self.paused:
            started = time.time()
            ok, frame = self.cap.read()
            if not ok:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.frame_idx = 0
                if self.audio_loaded:
                    self.audio.play_from(0)
                continue

            self.frame_idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            self.last_orig = frame
            self.last_hsv = hsv_channels(frame)

            self._fps_n += 1
            elapsed = time.time() - self._fps_t
            if elapsed >= 1.0:
                self._cur_fps = self._fps_n / elapsed
                self._fps_n = 0
                self._fps_t = time.time()

            self.root.after(0, self._render)
            self.root.after(0, self._update_info)

            delay = interval - (time.time() - started)
            if delay > 0:
                time.sleep(delay)

    def _seek_to(self, index: int):
        if self.cap is None:
            return
        index = max(0, min(index, self.total_frames - 1))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = self.cap.read()
        if ok:
            self.frame_idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            self.last_orig = frame
            self.last_hsv = hsv_channels(frame)
            self._render()
            self._update_info()

    def _pause_and_seek(self, index: int):
        was_playing = not self.paused
        if was_playing:
            self._stop_playback()
            self.paused = True
            self._btn_play.config(text="▶ Play")
            self.audio.pause()
        self._seek_to(index)

    def _step_back(self):
        self._pause_and_seek(self.frame_idx - 2)

    def _step_forward(self):
        self._pause_and_seek(self.frame_idx)

    def _drag_start(self):
        self._dragging = True
        if not self.paused:
            self._stop_playback()
            self.paused = True
            self._btn_play.config(text="▶ Play")
            self.audio.pause()

    def _drag_end(self):
        self._dragging = False
        if self.total_frames > 0:
            percent = self._prog_var.get() / 1000.0
            self._seek_to(int(percent * self.total_frames))

    def _on_progress_move(self, value):
        if self._dragging and self.total_frames > 0:
            self._seek_to(int(float(value) / 1000.0 * self.total_frames))

    def _on_volume(self, value):
        self.audio.set_volume(float(value) / 100.0)

    def _set_mode(self, mode: str):
        previous = self.mode
        self.mode = mode
        self._proc_title.set("" if mode == "hsv" else MODE_LABELS[mode])
        self._update_mode_btns()

        if mode == "hsv" and previous != "hsv":
            self._hsv_row.pack(after=self._main_row, padx=10, pady=(0, 6))
            self.root.after(10, self._fix_window_size)
        elif mode != "hsv" and previous == "hsv":
            self._hsv_row.pack_forget()
            self.root.after(10, self._fix_window_size)

        if self.last_orig is not None:
            self._render()

    def _fix_window_size(self):
        self.root.update_idletasks()
        self.root.geometry(f"{DISPLAY_W + 20}x{self.root.winfo_reqheight()}")

    def _update_mode_btns(self):
        for mode, button in self._mode_btns.items():
            button.config(bg=ACC if mode == self.mode else MODE_DEFAULTS[mode], fg="#ffffff" if mode == self.mode else BTN_FG)

    def _render(self):
        if self.last_orig is None:
            return

        orig_tk = bgr_to_photoimage(self.last_orig, PANEL_W, DISPLAY_H)
        self._cv_orig.itemconfig(self._ci_orig, image=orig_tk)
        self._cv_orig._img = orig_tk

        proc_frame = preprocess(self.last_orig, self.mode)
        proc_tk = bgr_to_photoimage(proc_frame, PANEL_W, DISPLAY_H)
        self._cv_proc.itemconfig(self._ci_proc, image=proc_tk)
        self._cv_proc._img = proc_tk

        if self.mode == "hsv":
            self._hsv_row.pack(padx=10, pady=(0, 6))
            h, s, v = hsv_channels(self.last_orig)
            for canvas, image_id, frame in zip(self._cv_hsv, self._ci_hsv, (h, s, v)):
                image = bgr_to_photoimage(frame, HSV_PANE_W, HSV_ROW_H)
                canvas.itemconfig(image_id, image=image)
                canvas._img = image
        else:
            self._hsv_row.pack_forget()

        proc_name = {
            "gray": "Grayscale",
            "gaussian": "Gaussian Blur",
            "median": "Median Blur",
            "hsv": "HSV",
        }.get(self.mode, "Processed")
        self._proc_title.set(proc_name)

    def _update_info(self):
        if self.total_frames > 0:
            self._prog_var.set(self.frame_idx / self.total_frames * 1000)

        def format_seconds(seconds):
            minutes, seconds = divmod(int(seconds), 60)
            return f"{minutes:02d}:{seconds:02d}"

        current = self.frame_idx / self.native_fps if self.native_fps else 0
        total = self.total_frames / self.native_fps if self.native_fps and self.total_frames else 0
        total_frames = str(self.total_frames) if self.total_frames else "?"

        self._info_var.set(
            f"Frame: {self.frame_idx} / {total_frames}   "
            f"{format_seconds(current)} / {format_seconds(total)}   "
            f"{self._cur_fps:.1f} fps   "
            f"Mode: {MODE_LABELS[self.mode]}"
        )

    def _on_close(self):
        self._stop_playback()
        self.audio.close()
        if self.cap:
            self.cap.release()
        self.root.destroy()
