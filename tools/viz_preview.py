"""Preview a set on the live key map page, without Live: layout.json instead of Live's clips.

Usage:  python tools/viz_preview.py <layout.json> [--port 9891] [--section N] [--part N] [--mode loop|play]
Serves LoopMix/viz.html through LoopMix/viz.py; the snapshot has the fields loop_mix.py `_snapshot` produces.
Section and part are 0-based. Stop with Ctrl+C.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from LoopMix import config  # noqa: E402
from LoopMix.logic import BREAK_KEYS, FX_KEYS, LOOP_KEYS  # noqa: E402
from LoopMix.viz import Viz  # noqa: E402


def label(clip) -> str:
    return re.sub(r"\s*\[[^\]]*\]", "", clip["name"]) if clip else ""


def build_snapshot(layout: dict, section: int = 0, part: int = 0, mode: str = "loop") -> dict:
    rows = layout["rows_per_section"]
    first = section * rows

    def clip(track, row):
        return next((c for c in layout["tracks"].get(track, []) if c["row"] == row), None)

    def keys(track, offsets, kind, row_of):
        return [dict(key=k, kind=kind, label=label(clip(track(i), row_of(i))), playing=False)
                for i, k in enumerate(offsets)]

    part_track = layout["parts"][part]
    return dict(
        mode=mode, octave=0, section=section, tempo=round(float(layout["tempo"]), 2),
        is_playing=False, song_time=0.0, bar=4.0, phrase=False, phrase_beats=4.0, pending_start=None,
        sections=list(layout["sections"]),
        parts=[dict(name=n, selected=i == part, playing="", position=None, length=None, pending="")
               for i, n in enumerate(layout["parts"])],
        rows=rows,
        keys=keys(lambda i: part_track, LOOP_KEYS, "loop", lambda i: first + i)
        + keys(lambda i: config.BREAK_TRACK, BREAK_KEYS, "break", lambda i: first + i)
        + keys(lambda i: config.FX_TRACKS[i], FX_KEYS, "fx", lambda i: first),
    )


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("layout")
    ap.add_argument("--port", type=int, default=9891)
    ap.add_argument("--section", type=int, default=0)
    ap.add_argument("--part", type=int, default=0)
    ap.add_argument("--mode", choices=("loop", "play"), default="loop")
    a = ap.parse_args(argv)
    layout = json.loads(Path(a.layout).read_text(encoding="utf-8"))
    if not 0 <= a.section < len(layout["sections"]) or not 0 <= a.part < len(layout["parts"]):
        ap.error("section must be 0..%d and part 0..%d" % (len(layout["sections"]) - 1, len(layout["parts"]) - 1))
    viz = Viz(a.port)
    viz.state = build_snapshot(layout, a.section, a.part, a.mode)
    print("key map preview on http://127.0.0.1:%d  (Ctrl+C to stop)" % a.port, flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        viz.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
