import os
import tempfile


class AudioPlayer:
    def __init__(self):
        self._ready = False
        self._wav = None
        self._fps = 30.0
        self._pygame = None
        try:
            import pygame
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            self._pygame = pygame
            self._ready = True
        except Exception as exc:
            print(f"[audio] pygame unavailable: {exc}")

    def load(self, video_path: str, fps: float) -> bool:
        self._fps = fps
        self._cleanup_wav()
        if not self._ready:
            return False
        try:
            from moviepy import VideoFileClip
        except ImportError:
            try:
                from moviepy.editor import VideoFileClip
            except ImportError:
                print("[audio] moviepy not found — no audio")
                return False

        try:
            clip = VideoFileClip(video_path)
            if clip.audio is None:
                clip.close()
                print("[audio] No audio track in this video")
                return False

            tmp = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
            tmp.close()

            clip.audio.write_audiofile(tmp.name, codec="libvorbis", logger=None)
            clip.close()

            self._wav = tmp.name
            self._pygame.mixer.music.load(self._wav)
            return True
        except Exception as exc:
            print(f"[audio] Extraction failed: {exc}")
            return False

    def play_from(self, frame_idx: int):
        if not self._ready or not self._wav:
            return

        pos = frame_idx / self._fps
        try:
            self._pygame.mixer.music.stop()
            self._pygame.mixer.music.play()
            if pos > 0.01:
                self._pygame.mixer.music.set_pos(pos)
        except Exception as exc:
            print(f"[audio] play failed: {exc}")

    def pause(self):
        if self._ready:
            try:
                self._pygame.mixer.music.pause()
            except Exception:
                pass

    def resume(self):
        if self._ready:
            try:
                self._pygame.mixer.music.unpause()
            except Exception:
                pass

    def stop(self):
        if self._ready:
            try:
                self._pygame.mixer.music.stop()
            except Exception:
                pass

    def set_volume(self, value: float):
        if self._ready:
            try:
                self._pygame.mixer.music.set_volume(max(0.0, min(1.0, value)))
            except Exception:
                pass

    def _cleanup_wav(self):
        self.stop()
        if self._wav:
            try:
                os.remove(self._wav)
            except Exception:
                pass
            self._wav = None

    def close(self):
        self._cleanup_wav()