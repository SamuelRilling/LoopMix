"""Rank loops by energy and stage them as numbered copies, mellow -> busy.

Energy = average of two per-part ranks: loudness (RMS) and busyness
(onsets per second from spectral flux). Your ears have the final word:
reorder by dragging clips in Live; this only gives a starting order.

Usage:  python tools/rank_energy.py
Output: samples/staged/<style>/<part>/01 <file>.wav ... plus ranking.txt
"""
import shutil
import sys
import wave
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "samples" / "prog-rock" / "musicradar-prog-rock-samples"
STAGED = ROOT / "samples" / "staged"

# style name -> (kit folder, {track name: source folder}). Order = octave shift 0, +1, +2.
STYLES: Dict[str, Tuple[str, Dict[str, str]]] = {
    "Rock 1 - 138bpm G": ("Loopkit 1 138bpm", {
        "Drums": "Drums", "Bass": "Bass", "Part A": "Guitar A",
        "Part B": "Organ", "Part X": "PhaseRhodes", "Break": "Lead Guitar",
    }),
    "Rock 2 - 150bpm D": ("Loopkit 2 150bpm", {
        "Drums": "Drums", "Bass": "Bass", "Part A": "Guitar A",
        "Part B": "Organ", "Part X": "AtmoGuitar", "Break": "Lead Guitar",
    }),
    "Rock 3 - 132bpm A": ("Loopkit 3 132bpm", {
        "Drums": "Drums", "Bass": "Bass", "Part A": "Rhythm Guitar Mix",
        "Part B": "Acoustic Guitar Mix", "Part X": "Lead Guitar A", "Break": "Lead Guitar B",
    }),
}

LOOPS_PER_PART = 6   # white keys D..B
BREAKS = 5           # black keys C# D# F# G# A#
# Breaks on F# G# A# keep the drums playing; the script reads "[Drums]" from the clip name.
KEEP_DRUMS_FROM = 3

FRAME = 2048
HOP = 512
ONSET_THRESHOLD = 1.5  # flux peaks above mean + 1.5 * std count as onsets


def read_mono(path: Path) -> Tuple[np.ndarray, int]:
    with wave.open(str(path)) as w:
        width, channels, rate = w.getsampwidth(), w.getnchannels(), w.getframerate()
        raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.uint8)
    if width == 2:
        ints = raw.view("<i2").astype(np.int32)
    elif width == 3:
        b = raw.reshape(-1, 3).astype(np.int32)
        ints = (b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)) << 8 >> 8  # sign-extend
    else:
        raise ValueError(f"{path.name}: expected 16- or 24-bit PCM, got {width * 8}-bit")
    samples = ints.reshape(-1, channels).mean(axis=1) / float(1 << (8 * width - 1))
    return samples, rate


def features(path: Path) -> Tuple[float, float]:
    x, rate = read_mono(path)
    rms = float(np.sqrt(np.mean(x ** 2)))
    frames = np.lib.stride_tricks.sliding_window_view(x, FRAME)[::HOP]
    mags = np.abs(np.fft.rfft(frames * np.hanning(FRAME), axis=1))
    flux = np.maximum(np.diff(mags, axis=0), 0).sum(axis=1)
    limit = flux.mean() + ONSET_THRESHOLD * flux.std()
    peaks = (flux[1:-1] > limit) & (flux[1:-1] >= flux[:-2]) & (flux[1:-1] >= flux[2:])
    return rms, float(peaks.sum()) / (len(x) / rate)


def rank(values: List[float]) -> np.ndarray:
    return np.argsort(np.argsort(values)).astype(float)


def spread(order: List[int], count: int) -> List[int]:
    """Keep `count` items evenly spread from mellowest to busiest."""
    if len(order) <= count:
        return order
    return [order[round(i)] for i in np.linspace(0, len(order) - 1, count)]


def stage_part(src: Path, dst: Path, is_break: bool) -> List[str]:
    files = sorted(src.glob("*.wav"))
    if not files:
        raise FileNotFoundError(f"No .wav files in {src}")
    feats = [features(f) for f in files]
    energy = rank([f[0] for f in feats]) + rank([f[1] for f in feats])
    order = sorted(range(len(files)), key=lambda i: (energy[i], feats[i][0]))
    order = spread(order, BREAKS if is_break else LOOPS_PER_PART)
    dst.mkdir(parents=True, exist_ok=True)
    names = []
    lines = []
    for n, i in enumerate(order, start=1):
        tag = " [Drums]" if is_break and n >= KEEP_DRUMS_FROM else ""
        name = f"{n:02d} {files[i].stem}{tag}.wav"
        names.append(name)
        if not (dst / name).exists():  # never overwrite: a saved Live Set may use it
            shutil.copy2(files[i], dst / name)
        lines.append(f"  {n:2d}  {name:40s} rms={feats[i][0]:.3f} onsets/s={feats[i][1]:.2f}")
    for stale in dst.glob("*.wav"):
        if stale.name not in names:
            stale.unlink()
    return lines


def main() -> int:
    for style, (kit, parts) in STYLES.items():
        report = [style]
        for part, folder in parts.items():
            report.append(f"{part}  <- {folder}")
            report += stage_part(PACK / kit / folder, STAGED / style / part, part == "Break")
        text = "\n".join(report)
        (STAGED / style / "ranking.txt").write_text(text + "\n", encoding="utf-8")
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
