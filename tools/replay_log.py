"""Replay the last Live session's LoopMix log through logic.py: which clip each press launched.

Usage: python tools/replay_log.py [sets/<kit>/layout.json]
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from LoopMix import config  # noqa: E402
from tools import settings  # noqa: E402
from LoopMix.logic import Layout, State, on_cc, on_note  # noqa: E402

LOG = settings.LIVE_LOG
LAYOUT = Layout(config.MODE_CC, tuple(config.PART_CCS), config.OCTAVE_UP_CC, config.OCTAVE_DOWN_CC,
                config.PHRASE_CC, config.BASE_NOTE, config.BUTTONS_LATCH, config.ROWS_PER_SECTION,
                tuple(config.SAME_VALUE_CCS))


def main(layout_path: str) -> int:
    layout = json.loads(Path(layout_path).read_text(encoding="utf-8"))
    clips = {t: {c["row"]: c for c in rows} for t, rows in layout["tracks"].items()}
    sections, parts = len(layout["sections"]), layout["parts"]
    lines = LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    start = max(i for i, l in enumerate(lines) if "Started: Live" in l)
    state = State()
    for line in lines[start:]:
        m = re.search(r"T(\d\d:\d\d:\d\d)\.\d+: info: RemoteScriptMessage: \(LoopMix\) LoopMix (CC|note) (\d+) (?:=|vel) (\d+)", line)
        if not m:
            continue
        clock, kind, number, value = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
        if kind == "CC":
            state, actions = on_cc(state, number, value, LAYOUT, sections, len(parts))
        else:
            state, actions = on_note(state, number, value, LAYOUT)
        for a in actions:
            track = {"fire": parts[a.part], "breakdown": "Break",
                     "fx": config.FX_TRACKS[a.part] if a.kind == "fx" else None}.get(a.kind)
            c = clips.get(track, {}).get(a.row) if track else None
            detail = ""
            if c:
                tempo = round(c["beats"] / (c["frames"] / 44100) * 60, 1)
                detail = "%s | %s beats, recorded at %s BPM, shift %+d" % (c["name"], c["beats"], tempo, c["shift"])
            print("%s S%d %-9s %-6s %s %s" % (clock, state.section + 1, a.kind, track or parts[a.part]
                                              if a.kind in ("fire", "stop", "select") else "", a.row if c else "", detail))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "sets/electro-house/layout.json"))
