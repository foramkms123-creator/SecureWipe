"""Notification sounds. Three built-in tones are generated once as WAV files in data/sounds and
played with Windows' own player (winsound), so no audio library is needed. Elsewhere: silent."""
import math
import struct
import wave

from config import DATA_DIR
from services.app_log import log_exception
from services.system_service import is_windows

SOUND_DIR = DATA_DIR / "sounds"
RATE = 22050

# name -> list of (frequency in Hz, seconds); 0 Hz = a pause
TONES = {
    "chime": [(1318.5, 0.45), (1760.0, 0.75)],                        # two bell notes
    "success": [(784.0, 0.12), (988.0, 0.12), (1318.5, 0.32)],        # rising three notes
    "alert": [(880.0, 0.16), (0, 0.07), (880.0, 0.16), (0, 0.07), (660.0, 0.35)],
}


def _write_wav(name: str, notes) -> object:
    path = SOUND_DIR / f"{name}.wav"
    if path.exists():
        return path
    SOUND_DIR.mkdir(parents=True, exist_ok=True)
    frames = bytearray()
    for freq, seconds in notes:
        n = int(RATE * seconds)
        for i in range(n):
            t = i / RATE
            fade_in = min(1.0, i / (RATE * 0.01))          # no click at the start
            fade_out = (1 - i / n) ** 1.5                  # smooth decay
            value = math.sin(2 * math.pi * freq * t) * fade_in * fade_out * 0.5 if freq else 0.0
            frames += struct.pack("<h", int(value * 32767))
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(bytes(frames))
    return path


def play(name: str) -> None:
    """Plays a built-in sound ('chime', 'success', 'alert'). 'off' or anything else: silent."""
    if name not in TONES or not is_windows():
        return
    try:
        import winsound
        winsound.PlaySound(str(_write_wav(name, TONES[name])),
                           winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception:
        log_exception(f"Playing sound '{name}' failed")
