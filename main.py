import sys
import tkinter as tk

from player import VideoPlayer
from ui_styles import DISPLAY_W


def main():
    root = tk.Tk()
    app = VideoPlayer(root, initial_path=sys.argv[1] if len(sys.argv) > 1 else "")
    root.protocol("WM_DELETE_WINDOW", app._on_close)
    root.update_idletasks()
    root.geometry(f"{DISPLAY_W + 20}x{root.winfo_reqheight()}")
    root.resizable(False, False)
    root.mainloop()


if __name__ == "__main__":
    main()
