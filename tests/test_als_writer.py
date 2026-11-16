import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from als_writer import WARP_BEATS, WARP_COMPLEX, sound_beats, warp_mode  # noqa: E402

RATE = 44100
AT_125 = 8 * 60 / 125 * RATE    # an 8-beat loop recorded at 125 BPM
AT_128 = 8 * 60 / 128 * RATE


def loop(frames, shift=0):
    return dict(loop=True, beats=8.0, audio_beats=frames / RATE * 128 / 60, frames=frames, shift=shift)


def test_loops_are_stretched_to_their_tagged_length():
    assert sound_beats(loop(AT_125)) == 8.0


def test_one_shots_keep_their_own_length():
    shot = dict(loop=False, beats=8, audio_beats=4.0, frames=AT_128 / 2, shift=0)
    assert sound_beats(shot) == 4.0


def test_stretched_or_retuned_melodic_loops_use_complex():
    assert warp_mode(loop(AT_125), "Part A", 128) == WARP_COMPLEX
    assert warp_mode(loop(AT_128, shift=3), "Bass", 128) == WARP_COMPLEX
    assert warp_mode(loop(AT_128), "Part B", 128) == WARP_BEATS


def test_drums_always_use_beats():
    assert warp_mode(loop(AT_125), "Drums", 128) == WARP_BEATS
    assert warp_mode(loop(AT_125), "Part X", 128) == WARP_BEATS
