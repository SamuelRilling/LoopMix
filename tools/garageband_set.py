"""Arrange a GarageBand loop pack into a LoopMix layout.

Roles come from GarageBand's own tags (category, subcategory, key, descriptors),
read from Apple's .pkg files. Drums are split into beats and toppers by sound
(kick or no kick), since GarageBand files both as "Electronic Beats".

Every section is full: each part gets exactly ROWS loops per section, and the
number of sections is set by the smallest part. Loops that don't fit are left
out rather than leaving keys empty.

Usage:  python tools/garageband_set.py "<folder of WAVs>" <pkg> [<pkg> ...]
Output: sets/electro-house/layout.json + <settings.STAGED>/Electro House/<track>/*.wav
"""
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List

import numpy as np

import settings
from apple_loops import read_packages
from audio import features, rank, read_mono, spread
from render_loops import render

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sets" / "electro-house"
STAGED = Path(settings.STAGED) / "Electro House"

TEMPO = 128.0
RATE = 44100
ROWS = 13                     # white keys per section
BREAKS = FX = 5               # black keys per octave
DEFAULT_PRIMING = 2112        # AAC padding, for the few loops Apple's packages lack
END_PADDING = 449             # AAC padding after the audio (same encoder for the whole pack)
FX_TRACKS = tuple("FX %d" % (i + 1) for i in range(FX))   # one track per key: FX overlap
KICK_RATIO = 0.35             # share of energy under 120 Hz that marks a full beat
MAX_SHIFT = 5                 # semitones; GarageBand-style retune to the set key
BREAK_KEEPS = "[Bass, Part A, Part B]"   # drums drop out during a transition

LOOP_TRACKS = ("Drums", "Bass", "Part A", "Part B", "Part X")
SECTION_NAMES = {
    3: ("Warm-up", "Groove", "Peak"),
    4: ("Warm-up", "Groove", "Drive", "Peak"),
    5: ("Warm-up", "Groove", "Lift", "Drive", "Peak"),
}
NOTES = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6,
         "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def family(name: str) -> str:
    return re.sub(r"\s*\d+$", "", name)


def with_sibling_tags(names: List[str], tags: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    """Loops missing from Apple's packages take the tags of a numbered sibling."""
    by_family = {}
    for n, t in tags.items():
        if t.get("category"):
            by_family.setdefault(family(n), t)
    return {n: tags.get(n) if tags.get(n, {}).get("category") else by_family.get(family(n), {})
            for n in names}


def kick_ratio(path: Path) -> float:
    x, rate = read_mono(path)
    spec = np.abs(np.fft.rfft(x)) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / rate)
    return float(spec[(freqs > 30) & (freqs < 120)].sum() / spec[freqs > 30].sum())


def role(name: str, t: Dict[str, str], path: Path) -> str:
    cat, sub = t.get("category"), t.get("subcategory")
    if cat == "Sound Effect" and sub == "Impacts & Crashes":
        return "FX"
    if cat in (None, "Sound Effect"):
        return "Break"   # transitions, plus untagged risers and effects
    if cat == "Drums":
        return "Drums" if kick_ratio(path) >= KICK_RATIO else "Part X"
    return {"Bass": "Bass", "Keyboards": "Part A", "Mixed": "Part B"}.get(cat, "")


def shift_to(root: str, target: int) -> int:
    return (target - NOTES[root] + 6) % 12 - 6


def main(src: Path, pkgs: List[str]) -> int:
    wavs = {p.stem: p for p in sorted(src.glob("*.wav"))}
    tags = with_sibling_tags(list(wavs), read_packages(pkgs))
    loops = []
    for name, path in wavs.items():
        t = tags[name]
        r = role(name, t, path)
        desc = t.get("descriptors", "")
        if not r or ("Arrhythmic" in desc and r in LOOP_TRACKS):
            continue
        if t.get("key signature") and t.get("key type") not in ("minor", "both"):
            continue  # the set is in a minor key; GarageBand hides major-only loops there
        if t.get("key signature") and t["key signature"] not in NOTES:
            continue
        rms, onsets = features(path)
        priming = int(t.get("priming frames", DEFAULT_PRIMING))
        frames = int(t.get("valid frames", 0)) or None
        loops.append(dict(name=name, path=path, role=r, root=t.get("key signature"),
                          beats=float(t["beat count"]) if t.get("beat count") else None,
                          priming=priming, valid=frames, rms=rms, onsets=onsets,
                          lean=1 if "Intense" in desc else -1 if "Relaxed" in desc else 0))

    tonal_roots = Counter(l["root"] for l in loops if l["root"])
    key = tonal_roots.most_common(1)[0][0]
    for l in loops:
        l["shift"] = shift_to(l["root"], NOTES[key]) if l["root"] else 0
    loops = [l for l in loops if abs(l["shift"]) <= MAX_SHIFT]

    for r in set(l["role"] for l in loops):
        group = [l for l in loops if l["role"] == r]
        energy = (rank([l["rms"] for l in group]) + rank([l["onsets"] for l in group])) / (2 * max(len(group) - 1, 1))
        for l, e in zip(group, energy):
            l["energy"] = float(e) + 0.25 * l["lean"]

    pools = {r: sorted([l for l in loops if l["role"] == r], key=lambda l: l["energy"]) for r in LOOP_TRACKS}
    sections = min(len(p) for p in pools.values()) // ROWS
    names = SECTION_NAMES.get(sections) or tuple(f"Level {i + 1}" for i in range(sections))

    layout = {"tempo": TEMPO, "key": f"{key} minor", "rows_per_section": ROWS,
              "sections": list(names), "tracks": {}, "left_out": {}}
    for r, pool in pools.items():
        need = sections * ROWS
        if pool[0]["root"]:   # tonal: least retuning first, then energy order
            chosen = sorted(sorted(pool, key=lambda l: abs(l["shift"]))[:need], key=lambda l: l["energy"])
        else:
            chosen = [pool[i] for i in spread(list(range(len(pool))), need)]
        layout["tracks"][r] = [clip(l, row) for row, l in enumerate(chosen)]
        layout["left_out"][r] = len(pool) - need

    breaks = sorted([l for l in loops if l["role"] == "Break"], key=lambda l: l["energy"])
    layout["tracks"]["Break"] = [
        clip(breaks[(s * BREAKS + k) % len(breaks)], s * ROWS + k, one_shot=True,
             suffix=" " + BREAK_KEEPS, bars=True)
        for s in range(sections) for k in range(BREAKS)]
    layout["left_out"]["Break"] = max(len(breaks) - sections * BREAKS, 0)

    # FX: key k of every section lives on track "FX k", in the section's first row.
    fx = sorted([l for l in loops if l["role"] == "FX"], key=lambda l: l["energy"])
    for k, track in enumerate(FX_TRACKS):
        layout["tracks"][track] = [clip(fx[(s * FX + k) % len(fx)], s * ROWS, one_shot=True, instant=True)
                                   for s in range(sections)]
    layout["left_out"]["FX"] = max(len(fx) - sections * FX, 0)

    stage(layout, src)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "layout.json").write_text(json.dumps(layout, indent=1), encoding="utf-8")
    print(f"key {layout['key']}, {sections} sections: {', '.join(names)}")
    for r, rows in layout["tracks"].items():
        print(f"  {r:7s} {len(rows):3d} clips, {layout['left_out'].get(r, '-')} left out")
    return 0


def clip(l: dict, row: int, one_shot: bool = False, suffix: str = "", bars: bool = False,
         instant: bool = False) -> dict:
    """`audio_beats` = the sound's own length (warp markers, no stretching);
    `beats` = the clip's length: tagged loop length, the sound itself, or whole bars."""
    frames = l["valid"] or audio_frames(l["path"], l["priming"])
    audio_beats = round(frames / RATE * TEMPO / 60, 3)
    beats = l["beats"] or audio_beats
    if bars:  # breaks last whole bars, so stopped parts come back on the bar
        beats = max(4, 4 * round(audio_beats / 4))
    return dict(row=row, name=l["name"] + suffix, file=l["name"] + ".wav", beats=beats,
                audio_beats=audio_beats, priming=l["priming"], frames=frames, shift=l["shift"],
                root=l["root"], energy=round(l["energy"], 3), loop=not one_shot, instant=instant)


def audio_frames(path: Path, priming: int) -> int:
    """Untagged files: WAV length minus the decoder's padding at both ends."""
    x, _ = read_mono(path)
    return len(x) - priming - END_PADDING


def needs_render(c: dict) -> bool:
    """A loop GarageBand would retune or re-tempo: done offline, so Live never warps it."""
    stretched = abs(c["frames"] / RATE - c["beats"] * 60 / TEMPO) > 0.001
    return c["loop"] and (c["shift"] != 0 or stretched)


def stage(layout: dict, src: Path) -> None:
    """Put the chosen WAVs under the User Library junction (samples/staged).

    Loops needing a new key or tempo are rendered (exactly `beats` long, no
    decoder padding); everything else is copied as-is.
    """
    ffmpeg = shutil.which("ffmpeg")
    for r, rows in layout["tracks"].items():
        dst = STAGED / r
        dst.mkdir(parents=True, exist_ok=True)
        for c in rows:
            if needs_render(c):
                target = dst / ("%s (%s %g).wav" % (c["name"], layout["key"].split()[0], TEMPO))
                if not target.exists():
                    if ffmpeg is None:
                        raise RuntimeError("ffmpeg (with the rubberband filter) is needed to render loops")
                    render(src / c["file"], target, c["priming"], c["frames"], c["beats"], c["shift"], TEMPO, ffmpeg)
                c.update(rendered_from=c["shift"], shift=0, priming=0,
                         frames=int(round(c["beats"] * 60 / TEMPO * RATE)), file=target.name)
            else:
                target = dst / c["file"]
                if not target.exists():
                    shutil.copy2(src / c["file"], target)
            c["path"] = str(target).replace("\\", "/")


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), sys.argv[2:]))
