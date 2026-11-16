import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from garageband_set import assign, fit, matches, needs_render, options  # noqa: E402

AT_128 = 8 * 60 / 128 * 44100
AT_125 = 8 * 60 / 125 * 44100


def clip(frames, shift=0, loop=True):
    return dict(frames=frames, beats=8.0, shift=shift, loop=loop)


def test_retuned_or_off_tempo_loops_are_rendered():
    assert needs_render(clip(AT_128, shift=3), 128)
    assert needs_render(clip(AT_125), 128)


def test_one_shots_are_rendered_only_to_retune():
    assert not needs_render(clip(AT_125, loop=False), 128)
    assert needs_render(clip(AT_125, shift=-2, loop=False), 128)


def test_native_loops_are_copied():
    assert not needs_render(clip(AT_128), 128)


PACK = {"parts": {"Strings": [{"category": "Strings", "subcategory": [None, "Violin"]}],
                  "Beats": [{"category": "Drums", "kick": True}]},
        "break": {"match": [{"descriptors": ["Fill"]}]},
        "fx": {"match": [{"category": None}]}}


def test_rules_match_values_lists_and_untagged():
    assert matches({"category": "Strings", "subcategory": [None, "Violin"]}, "x", {"category": "Strings"})
    assert not matches({"category": "Strings", "subcategory": "Harp"}, "x", {"category": "Strings"})
    assert matches({"category": None}, "x", {})
    assert matches({"name": ["riser"]}, "Electro Riser 01", {})


def test_fill_loops_skip_parts_and_go_to_break():
    fill = {"category": "Strings", "subcategory": "Violin", "descriptors": "Fill,Melodic"}
    assert assign("Run", fill, PACK) == ("break", None)
    assert assign("Theme", dict(fill, descriptors="Melodic"), PACK) == ("Strings", None)
    assert assign("Beat", {"category": "Drums"}, PACK) == ("Beats", True)
    assert assign("Whoosh", {}, PACK) == ("fx", None)


def test_drum_loops_list_every_matching_part_for_the_kick_split():
    pack = {"parts": {"Beats": [{"category": "Drums", "kick": True}],
                      "Toppers": [{"category": "Drums", "kick": False}]}}
    assert options("Clap", {"category": "Drums"}, pack) == [("Beats", True), ("Toppers", False)]


def loop(role, native, root="C", scale="minor"):
    return dict(name=role, role=role, part=True, kick=None, root=root, scale=scale, native=native,
                beats=8.0, valid=None, lean=0)


def test_auto_tempo_and_scale_maximise_full_sections():
    pack = {"parts": {"A": [], "B": []}, "drum_parts": [], "tempo": "auto", "tempo_window": 0.05,
            "scale": "auto", "key": "auto", "max_shift": 5}
    loops = ([loop("A", 100)] * 30 + [loop("B", 100)] * 2      # 100 BPM: B has 2 loops
             + [loop("A", 90, scale="major")] * 13 + [loop("B", 90, scale="major")] * 13)
    kept, tempo, key, scale = fit(loops, pack)
    assert (tempo, scale) == (90.0, "major")                    # the only choice with a full section
