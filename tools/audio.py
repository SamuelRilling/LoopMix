"""Generic audio helpers: read a WAV as mono, score a loop's energy, rank and thin pools.

Energy = loudness (RMS) and busyness (onsets per second from spectral flux).
"""
import struct
import wave
from pathlib import Path
from typing import List, Tuple

import numpy as np

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


ACID_ONE_SHOT, ACID_ROOT_SET = 0x01, 0x02   # flags of the `acid` chunk


def read_loop_meta(path: Path) -> dict:
    """Loop metadata embedded in a WAV: `acid` (ACIDized: one-shot flag, root note,
    beats, tempo) and `smpl` (unity note). Keys present only when the file has them:
    root (MIDI note), beats, tempo, one_shot."""
    data = Path(path).read_bytes()
    meta, p = {}, 12
    while p + 8 <= len(data):
        kind, size = data[p:p + 4], struct.unpack("<I", data[p + 4:p + 8])[0]
        body = data[p + 8:p + 8 + size]
        if kind == b"acid" and size >= 24:
            flags, root, _, _, beats, _, _, tempo = struct.unpack("<IHHfIHHf", body[:24])
            meta["one_shot"] = bool(flags & ACID_ONE_SHOT)
            if flags & ACID_ROOT_SET:
                meta["root"] = root
            if beats:
                meta["beats"] = beats
            if tempo > 0:
                meta["tempo"] = round(tempo, 3)
        elif kind == b"smpl" and size >= 36 and "root" not in meta:
            meta["root"] = struct.unpack("<I", body[12:16])[0]
        p += 8 + size + (size & 1)
    if "root" in meta:
        meta["root"] %= 128
    return meta


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
