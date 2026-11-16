"""Arrange an ordinary song construction kit into a LoopMix layout.

kit.json is the only per-kit input (see sets/prog-rock-1/kit.json). Sections are the
kit's own song sections: the id comes from each file name via `section_pattern`
(one regex group), because loops of one song section share harmony. Within a section
a part's loops run mellow -> busy over the keys. Sections are not padded.

Usage:  python tools/kit_set.py sets/<kit>/kit.json
Output: sets/<kit>/layout.json + <settings.STAGED>/<name>/<track>/*.wav
"""
import json
import re
import shutil
import sys
import wave
from pathlib import Path
from typing import Callable, Dict, List, Optional

import settings
from audio import features, rank
from render_loops import RATE, render

ROWS_PER_SECTION = 13        # white keys per section
BREAKS = FX = 5              # black keys per octave
LOOP_TRACKS = ("Drums", "Bass", "Part A", "Part B", "Part X")
FX_TRACKS = tuple("FX %d" % (i + 1) for i in range(FX))
TOLERANCE = 0.001            # seconds; a loop further off its bar length gets rendered


def wav_files(source: Path, folders: List[str]) -> List[Path]:
    paths = []
    for f in folders:
        found = sorted((source / f).glob("*.wav"))
        if not found:
            raise SystemExit("no .wav files in %s" % (source / f))
        paths += found
    return paths


def section_id(path: Path, pattern: str) -> Optional[str]:
    m = re.search(pattern, path.name)
    return m.group(1) if m else None


def group_by_section(paths: List[Path], pattern: str) -> Dict[str, List[Path]]:
    groups: Dict[str, List[Path]] = {}
    for p in paths:
        sid = section_id(p, pattern)
        if sid is None:
            raise SystemExit("%s does not match section_pattern %r" % (p.name, pattern))
        groups.setdefault(sid, []).append(p)
    return groups


def sort_key(sid: str):
    return (0, int(sid), "") if sid.isdigit() else (1, 0, sid)


def by_energy(paths: List[Path], energy: Callable[[Path], tuple]) -> List[tuple]:
    """[(path, energy 0..1)] mellow -> busy: mean rank of loudness and onset rate."""
    feats = [energy(p) for p in paths]
    score = (rank([f[0] for f in feats]) + rank([f[1] for f in feats])) / (2 * max(len(paths) - 1, 1))
    return sorted(zip(paths, (float(s) for s in score)), key=lambda t: t[1])


def thin(items: list, count: int) -> list:
    """Keep `count` items evenly spread over an ordered list."""
    if len(items) <= count:
        return items
    return [items[round(i * (len(items) - 1) / (count - 1))] for i in range(count)] if count > 1 else items[:1]


def clip(path: Path, row: int, tempo: float, frames: int, *, energy: float = 0.0,
         one_shot: bool = False, suffix: str = "", bars: bool = False, instant: bool = False) -> dict:
    """`audio_beats` = the sound's own length; `beats` = the clip's: whole bars for loops
    and breaks, the sound itself for other one-shots."""
    audio_beats = round(frames / RATE * tempo / 60, 3)
    beats = audio_beats
    if bars or not one_shot:
        beats = float(max(4, 4 * round(audio_beats / 4)))
    return dict(row=row, name=path.stem + suffix, file=str(path), beats=beats, audio_beats=audio_beats,
                priming=0, frames=frames, shift=0, root=None, energy=round(energy, 3),
                loop=not one_shot, instant=instant)


def build_layout(kit: dict, energy: Callable[[Path], tuple], frames_of: Callable[[Path], int]) -> dict:
    """Pure placement of every clip; `file` is still the source WAV (stage() fixes paths)."""
    source, tempo, pattern = Path(kit["source"]), float(kit["tempo"]), kit["section_pattern"]
    parts = {t: group_by_section(wav_files(source, kit["parts"][t]), pattern)
             for t in LOOP_TRACKS if t in kit["parts"]}
    brk = kit.get("break")
    break_groups = group_by_section(wav_files(source, brk["folders"]), pattern) if brk else {}
    ids = sorted({sid for g in [*parts.values(), break_groups] for sid in g}, key=sort_key)
    names = ["Section %d" % int(i) if i.isdigit() else i for i in ids]

    layout = {"tempo": tempo, "key": kit.get("key", ""), "rows_per_section": ROWS_PER_SECTION,
              "sections": names, "tracks": {}, "left_out": {}}
    for track, groups in parts.items():
        clips, left = [], 0
        for s, sid in enumerate(ids):
            ordered = by_energy(groups.get(sid, []), energy)
            kept = thin(ordered, ROWS_PER_SECTION)
            left += len(ordered) - len(kept)
            clips += [clip(p, s * ROWS_PER_SECTION + i, tempo, frames_of(p), energy=e)
                      for i, (p, e) in enumerate(kept)]
        layout["tracks"][track], layout["left_out"][track] = clips, left

    if brk:
        suffix = " [%s]" % ", ".join(brk["keep"])
        clips, left = [], 0
        for s, sid in enumerate(ids):
            ordered = by_energy(break_groups.get(sid, []), energy)[:BREAKS]
            left += max(len(break_groups.get(sid, [])) - BREAKS, 0)
            clips += [clip(p, s * ROWS_PER_SECTION + k, tempo, frames_of(p), energy=e, one_shot=True,
                           suffix=suffix, bars=True) for k, (p, e) in enumerate(ordered)]
        layout["tracks"]["Break"], layout["left_out"]["Break"] = clips, left

    if kit.get("fx"):
        hits = wav_files(source, kit["fx"]["folders"])   # FX ignore section_pattern
        for k, track in enumerate(FX_TRACKS):
            own = hits[k::FX] or hits
            layout["tracks"][track] = [
                clip(own[s % len(own)], s * ROWS_PER_SECTION, tempo, frames_of(own[s % len(own)]),
                     one_shot=True, instant=True) for s in range(len(ids))]
    return layout


def needs_render(c: dict, tempo: float) -> bool:
    """A loop whose file isn't exactly its whole-bar length: rendered so Live never warps it."""
    return c["loop"] and abs(c["frames"] / RATE - c["beats"] * 60 / tempo) > TOLERANCE


def stage(layout: dict, name: str) -> None:
    """Copy (or render) each clip's WAV to STAGED/<name>/<track>/ and set `path`."""
    ffmpeg = shutil.which("ffmpeg")
    for track, clips in layout["tracks"].items():
        dst = Path(settings.STAGED) / name / track
        dst.mkdir(parents=True, exist_ok=True)
        for c in clips:
            src = Path(c.pop("file"))
            target = dst / src.name
            if needs_render(c, layout["tempo"]):
                if ffmpeg is None:
                    raise RuntimeError("ffmpeg (with the rubberband filter) is needed to render loops")
                render(src, target, 0, c["frames"], c["beats"], 0, layout["tempo"], ffmpeg)
                c["frames"] = int(round(c["beats"] * 60 / layout["tempo"] * RATE))
            elif not target.exists():
                shutil.copy2(src, target)
            c["path"] = str(target).replace("\\", "/")


def wav_frames(path: Path) -> int:
    with wave.open(str(path)) as w:
        if w.getframerate() != RATE:
            raise SystemExit("%s: expected %d Hz, got %d" % (path.name, RATE, w.getframerate()))
        return w.getnframes()


def main(kit_file: Path) -> int:
    kit = json.loads(kit_file.read_text(encoding="utf-8"))
    layout = build_layout(kit, features, wav_frames)
    stage(layout, kit["name"])
    out = kit_file.parent / "layout.json"
    out.write_text(json.dumps(layout, indent=1), encoding="utf-8")
    print("key %s, %d sections: %s" % (layout["key"], len(layout["sections"]), ", ".join(layout["sections"])))
    for t, rows in layout["tracks"].items():
        print("  %-7s %3d clips, %s left out" % (t, len(rows), layout["left_out"].get(t, "-")))
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
