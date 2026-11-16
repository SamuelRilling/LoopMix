import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from viz_preview import build_snapshot  # noqa: E402

LAYOUT = {
    "tempo": 128.0, "key": "A minor", "rows_per_section": 13, "sections": ["Warm-up", "Peak"],
    "tracks": {
        "Drums": [dict(row=0, name="Kick A"), dict(row=13, name="Kick B"), dict(row=15, name="Kick C")],
        "Break": [dict(row=14, name="Riser [Bass, Part A]")],
        "FX 2": [dict(row=13, name="Impact")],
    },
}


def test_snapshot_fields_and_keys():
    s = build_snapshot(LAYOUT, section=1)
    assert {"mode", "octave", "section", "tempo", "is_playing", "song_time", "bar", "phrase", "phrase_beats",
            "pending_start", "sections", "parts", "rows", "keys"} <= set(s)
    assert s["section"] == 1 and s["tempo"] == 128.0 and s["is_playing"] is False
    assert [p["selected"] for p in s["parts"]] == [True, False, False, False, False]
    assert len(s["keys"]) == 23
    loops = [k for k in s["keys"] if k["kind"] == "loop"]
    assert [k["label"] for k in loops[:3]] == ["Kick B", "", "Kick C"]     # rows 13, 14, 15
    breaks = [k for k in s["keys"] if k["kind"] == "break"]
    assert breaks[1]["label"] == "Riser" and breaks[1]["key"] == 3          # suffix dropped, D#3
    fx = [k for k in s["keys"] if k["kind"] == "fx"]
    assert [k["label"] for k in fx] == ["", "Impact", "", "", ""]
