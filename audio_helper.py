import os
import tempfile
from datetime import datetime


def _log(message: str):
    try:
        with open("audio_log.txt", "a", encoding="utf-8") as f:
            now = datetime.now().strftime("%H:%M:%S")
            f.write(f"[{now}] {message}\n")
    except Exception:
        pass


class AudioPlayer:
    def __init__(self):
        self._ready = False
        self._audio_path = None
        self._fps = 30.0
        self._pygame = None

        try:
            import pygame
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._pygame = pygame
            self._ready = True
            _log("pygame mixer initialized")
        except Exception as exc:
            _log(f"pygame unavailable: {exc}")

    def load(self, video_path: str, fps: float) -> bool:
        self._fps = fps
        self._cleanup_audio()

        if not self._ready:
            _log("load skipped: mixer not ready")
            return False

        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_exe
            os.environ["FFMPEG_BINARY"] = ffmpeg_exe
            _log(f"ffmpeg resolved: {ffmpeg_exe}")
        except Exception as exc:
            _log(f"imageio_ffmpeg failed: {exc}")
            return False

        try:
            from moviepy import VideoFileClip
        except ImportError:
            try:
                from moviepy.editor import VideoFileClip
            except ImportError as exc:
                _log(f"moviepy import failed: {exc}")
                return False

        try:
            clip = VideoFileClip(video_path)
            if clip.audio is None:
                clip.close()
                _log("video has no audio track")
                return False

            tmp = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
            tmp.close()

            clip.audio.write_audiofile(
                tmp.name,
                codec="libvorbis",
                logger=None,
            )
            clip.close()

            self._audio_path = tmp.name
            self._pygame.mixer.music.load(self._audio_path)
            _log(f"temp audio loaded: {self._audio_path}")
            return True

        except Exception as exc:
            _log(f"audio extraction failed: {exc}")
            return False

    def play_from(self, frame_idx: int):
        pos = frame_idx / self._fps
        self.play_from_seconds(pos)

    def play_from_seconds(self, pos: float):
        if not self._ready or not self._audio_path:
            _log("play skipped: audio not ready")
            return

        try:
            self._pygame.mixer.music.stop()
            self._pygame.mixer.music.play()
            if pos > 0.01:
                self._pygame.mixer.music.set_pos(pos)
            _log(f"play from {pos:.3f}s")
        except Exception as exc:
            _log(f"play failed: {exc}")

    def pause(self):
        if self._ready:
            try:
                self._pygame.mixer.music.pause()
            except Exception as exc:
                _log(f"pause failed: {exc}")

    def resume(self):
        if self._ready:
            try:
                self._pygame.mixer.music.unpause()
            except Exception as exc:
                _log(f"resume failed: {exc}")

    def stop(self):
        if self._ready:
            try:
                self._pygame.mixer.music.stop()
            except Exception as exc:
                _log(f"stop failed: {exc}")

    def set_volume(self, value: float):
        if self._ready:
            try:
                self._pygame.mixer.music.set_volume(max(0.0, min(1.0, value)))
            except Exception as exc:
                _log(f"set_volume failed: {exc}")

    def _cleanup_audio(self):
        self.stop()
        if self._audio_path:
            try:
                os.remove(self._audio_path)
            except Exception as exc:
                _log(f"temp delete failed: {exc}")
            self._audio_path = None

    def close(self):
        self._cleanup_audio()