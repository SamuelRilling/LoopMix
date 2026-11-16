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
    exact = dict(loop=True, frames=round(4 * BAR), beats=16.0, shift=0)
    assert not needs_render(exact, 138)
    assert needs_render(dict(exact, frames=exact["frames"] + 100), 138)
    assert not needs_render(dict(exact, loop=False, frames=5), 138)
    assert needs_render(dict(exact, shift=2), 138)   # retuned loops are rendered too


def meta_layout(tmp_path, meta, **kit_extra):
    files = {"Drums": ["d-01.wav"], "GA": ["a-01.wav", "a-02.wav", "a-03.wav"], "GB": ["b-01.wav"]}
    kit = dict(make_kit(tmp_path, files), **kit_extra)
    del kit["break"], kit["fx"]
    return build_layout(kit, lambda p: (0, 0), lambda p: round(4 * BAR), lambda p: meta.get(p.name, {}))


def test_loops_retune_to_most_common_root_and_far_ones_are_left_out(tmp_path):
    meta = {"a-01.wav": {"root": 57}, "a-02.wav": {"root": 59}, "a-03.wav": {"root": 63}, "b-01.wav": {"root": 57}}
    lay = meta_layout(tmp_path, meta)
    clips = {c["name"]: c for c in lay["tracks"]["Guitars"]}
    assert lay["key"] == "G"                                  # kit.json key wins the label ...
    assert (clips["a-01"]["shift"], clips["a-02"]["shift"], clips["b-01"]["shift"]) == (0, -2, 0)  # ... A is the mode
    assert "a-03" not in clips and lay["left_out"]["Guitars"] == 1  # 63 -> 57 is 6 semitones


def test_embedded_beats_and_tempo_beat_file_name_guesses(tmp_path):
    meta = {"a-01.wav": {"beats": 6, "tempo": 100.0}}
    lay = meta_layout(tmp_path, meta, tempo=0)
    assert lay["tempo"] == 100.0
    clip = lay["tracks"]["Guitars"][0]
    assert clip["beats"] == 6.0 and clip["loop"]


def test_acid_one_shot_flag_makes_a_one_shot(tmp_path):
    lay = meta_layout(tmp_path, {"a-01.wav": {"one_shot": True}})
    assert not lay["tracks"]["Guitars"][0]["loop"]


def test_drum_parts_are_the_parts_without_root_notes(tmp_path):
    lay = meta_layout(tmp_path, {"a-01.wav": {"root": 57}, "b-01.wav": {"root": 57}})
    assert lay["drum_parts"] == ["Drums"]


def test_drum_parts_from_kit_json_win(tmp_path):
    assert meta_layout(tmp_path, {"a-01.wav": {"root": 57}}, drum_parts=["Guitars"])["drum_parts"] == ["Guitars"]


def test_no_metadata_means_no_drum_parts(tmp_path):
    assert meta_layout(tmp_path, {})["drum_parts"] == []
