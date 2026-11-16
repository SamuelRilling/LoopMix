import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from set_map import render_page  # noqa: E402


def clip(row, name):
    return dict(row=row, name=name)


LAYOUT = {
    "tempo": 128.0, "key": "A minor", "rows_per_section": 13, "sections": ["Warm-up", "Peak"],
    "tracks": {
        "Drums": [clip(0, "Kick <A>"), clip(13, "Kick B")],
        "Bass": [clip(2, "Sub")],
        "Break": [clip(14, "Riser [Bass, Part A]")],
        "FX 1": [clip(0, "Crash"), clip(13, "Impact")],
    },
}


def test_page_shows_sections_keys_and_loops():
    page = render_page(LAYOUT, "demo")
    assert "128.0</b> BPM" in page and "A minor" in page
    assert "S1 Warm-up" in page and "S2 Peak" in page
    assert page.count("<section") == 2
    assert "Kick &lt;A&gt;" in page and "Kick <A>" not in page   # escaped
    assert '<td class="k">D3</td><td title="Kick B">Kick B</td>' in page   # section 2, key 1
    assert '<td class="k">F3</td><td class="empty">–</td><td title="Sub">Sub</td>' in page   # bass row 2 = F3
    assert '<span class="k">D#3</span>Riser [Bass, Part A]' in page
    assert "Impact" in page and "Crash" in page
