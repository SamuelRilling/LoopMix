"""Render loops to the set's key and tempo offline, so Live plays them without warping.

GarageBand retunes loops live; doing that in Live (Complex warp on dense mixes)
costs CPU and can glitch. Here each loop is rendered once with ffmpeg's
Rubber Band filter, at high quality, to exactly `beats` at the set tempo.

Seamless loops: the audio is processed three times in a row and the middle copy
is kept, so the stretcher sees the loop's real wrap-around at both edges.
"""
import subprocess
from pathlib import Path

RATE = 44100


def render(src: Path, dst: Path, priming: int, frames: int, beats: float, shift: int,
           tempo: float, ffmpeg: str = "ffmpeg") -> int:
    """Write dst: frames [priming, priming+frames) of src, `shift` semitones, `beats` long at `tempo`.

    Returns the number of frames written (= beats at tempo).
    """
    target = int(round(beats * 60 / tempo * RATE))
    stretch = frames / target                     # > 1 speeds up
    chain = ",".join([
        "atrim=start_sample=%d:end_sample=%d" % (priming, priming + frames),
        "asetpts=N/SR/TB",
        "aloop=loop=2:size=%d" % frames,          # three copies: wrap-around context at both edges
        "rubberband=tempo=%.10f:pitch=%.10f:pitchq=quality:transients=mixed:detector=compound:window=standard"
        % (stretch, 2 ** (shift / 12.0)),
        "atrim=start_sample=%d:end_sample=%d" % (target, 2 * target),   # the middle copy
        "asetpts=N/SR/TB",
    ])
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg, "-v", "error", "-y", "-i", str(src), "-af", chain,
                    "-ar", str(RATE), "-c:a", "pcm_s16le", str(dst)], check=True)
    return target
