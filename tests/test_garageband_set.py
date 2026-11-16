import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from garageband_set import needs_render  # noqa: E402

AT_128 = 8 * 60 / 128 * 44100
AT_125 = 8 * 60 / 125 * 44100


def clip(frames, shift=0, loop=True):
    return dict(frames=frames, beats=8.0, shift=shift, loop=loop)


def test_retuned_or_off_tempo_loops_are_rendered():
    assert needs_render(clip(AT_128, shift=3))
    assert needs_render(clip(AT_125))


def test_native_loops_and_one_shots_are_copied():
    assert not needs_render(clip(AT_128))
    assert not needs_render(clip(AT_125, loop=False))
