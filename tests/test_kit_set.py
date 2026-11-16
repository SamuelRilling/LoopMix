import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from kit_set import build_layout, needs_render, section_id  # noqa: E402

BAR = 76695.65            # frames per bar at 138 bpm
PATTERN = r"-(\d+)\.wav$"


def make_kit(tmp_path, files):
    """files: {folder: [file names]} -> kit dict over empty placeholder files."""
    for folder, names in files.items():
        (tmp_path / folder).mkdir()
        for n in names:
            (tmp_path / folder / n).touch()
    return {"source": str(tmp_path), "tempo": 138, "section_pattern": PATTERN, "key": "G",
            "parts": {"Drums": ["Drums"], "Guitars": ["GA", "GB"]},
            "break": {"folders": ["Lead"], "keep": ["Drums"]}, "fx": {"folders": ["Hits"]}}


def layout(tmp_path, energy=lambda p: (0, 0), frames=lambda p: round(4 * BAR)):
    files = {"Drums": ["d-02.wav", "d-01.wav"], "GA": ["a-01.wav", "a-02.wav"], "GB": ["b-01.wav"],
             "Lead": ["l-01.wav", "l-01b-01.wav", "l-02.wav"], "Hits": ["h-%02d.wav" % i for i in range(1, 8)]}
    return build_layout(make_kit(tmp_path, files), energy, frames)


def test_section_id_from_file_name():
    assert section_id(Path("ProgK1Drums138-03.wav"), PATTERN) == "03"
    assert section_id(Path("x.wav"), PATTERN) is None


def test_sections_and_rows(tmp_path):
    lay = layout(tmp_path)
    assert lay["sections"] == ["Section 1", "Section 2"]
    assert [c["row"] for c in lay["tracks"]["Drums"]] == [0, 13]
    assert lay["parts"] == ["Drums", "Guitars"]
    assert [c["row"] for c in lay["tracks"]["Guitars"]] == [0, 1, 13]   # section 1: a-01 + b-01; section 2: a-02


def test_loops_ordered_mellow_to_busy(tmp_path):
    busy = {"a-01.wav": (0.9, 9), "b-01.wav": (0.1, 1)}
    lay = layout(tmp_path, energy=lambda p: busy.get(p.name, (0, 0)))
    assert [c["name"] for c in lay["tracks"]["Guitars"][:2]] == ["b-01", "a-01"]


def test_break_rows_and_names(tmp_path):
    clips = layout(tmp_path)["tracks"]["Break"]
    assert [c["row"] for c in clips] == [0, 1, 13]
    assert all(c["name"].endswith(" [Drums]") and not c["loop"] for c in clips)


def test_fx_one_clip_per_section_instant(tmp_path):
    lay = layout(tmp_path)
    for k in range(1, 6):
        clips = lay["tracks"]["FX %d" % k]
        assert [c["row"] for c in clips] == [0, 13]
        assert all(c["instant"] and not c["loop"] for c in clips)
    assert lay["tracks"]["FX 1"][0]["name"] == "h-01" and lay["tracks"]["FX 2"][0]["name"] == "h-02"


def test_only_off_length_loops_are_rendered():
    exact = dict(loop=True, frames=round(4 * BAR), beats=16.0)
    assert not needs_render(exact, 138)
    assert needs_render(dict(exact, frames=exact["frames"] + 100), 138)
    assert not needs_render(dict(exact, loop=False, frames=5), 138)
