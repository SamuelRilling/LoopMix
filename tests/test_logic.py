from LoopMix.logic import (LOOP, PLAY, Action, Layout, State, kept_parts, on_cc, on_note,
                           phrase_release, resume_beat, section_row)

L = Layout(mode_cc=97, part_ccs=(96, 66, 67, 64, 65), octave_up_cc=20, octave_down_cc=21,
           phrase_cc=10, base_note=48, latch=False, rows_per_section=13)
PARTS = ("Drums", "Bass", "Part A", "Part B", "Part X")
SECTIONS = 4


def cc(state, number, value):
    return on_cc(state, number, value, L, SECTIONS)


def test_b1_toggles_mode_both_ways():
    s, a = cc(State(), 97, 127)
    assert s.mode == PLAY and a == (Action("mode", mode=PLAY),)
    s, a = cc(s, 97, 127)
    assert s.mode == LOOP and a[0].mode == LOOP


def test_momentary_release_is_ignored():
    assert cc(State(), 97, 0) == (State(), ())


def test_latching_button_acts_on_release_value_too():
    s, _ = on_cc(State(), 97, 0, L._replace(latch=True), SECTIONS)
    assert s.mode == PLAY


def test_part_buttons_select_part_in_loop_mode():
    s, a = cc(State(), 64, 127)
    assert s.part == 3 and a == (Action("select", part=3),)


def test_part_buttons_ignored_in_play_mode():
    play = State(mode=PLAY, part=1)
    assert cc(play, 67, 127) == (play, ())


def test_octave_buttons_move_sections_in_loop_mode():
    s, a = cc(State(), 20, 127)
    assert s.section == 1 and a == (Action("section", section=1),)
    s, a = cc(s, 21, 127)
    assert s.section == 0 and a == (Action("section", section=0),)


def test_latching_octave_buttons_step_on_every_press():
    s = State()
    for value in (127, 0, 127):  # the right button alternates 127 / 0
        s, _ = cc(s, 20, value)
    assert s.section == 3
    for value in (127, 0):
        s, _ = cc(s, 21, value)
    assert s.section == 1


def test_sections_stop_at_both_ends():
    assert cc(State(section=0), 21, 127) == (State(section=0), ())
    assert cc(State(section=3), 20, 0) == (State(section=3), ())


def test_octave_buttons_shift_play_octave_in_play_mode():
    s, a = cc(State(mode=PLAY, section=2), 20, 0)
    assert s.octave == 1 and s.section == 2 and a == (Action("octave", octave=1),)
    assert cc(State(mode=PLAY, octave=-3), 21, 127)[1] == ()


def test_lowest_key_stops_selected_part():
    assert on_note(State(part=2), 48, 100, L)[1] == (Action("stop", part=2),)


def test_thirteen_white_keys_fire_rows_including_middle_c():
    whites = (50, 52, 53, 55, 57, 59, 60, 62, 64, 65, 67, 69, 71)
    fired = [on_note(State(part=1), n, 100, L)[1] for n in whites]
    assert fired == [(Action("fire", part=1, row=r),) for r in range(13)]


def test_rows_offset_by_section():
    assert on_note(State(section=2), 50, 100, L)[1] == (Action("fire", row=26),)


def test_lower_black_keys_fire_breaks_upper_fire_fx():
    assert [on_note(State(), n, 100, L)[1] for n in (49, 51, 54, 56, 58)] == \
        [(Action("breakdown", row=r),) for r in range(5)]
    assert [on_note(State(section=1), n, 100, L)[1] for n in (61, 63, 66, 68, 70)] == \
        [(Action("fx", part=k, row=13),) for k in range(5)]


def test_keys_outside_range_and_top_c_do_nothing():
    for note in (47, 72, 73, 100):
        assert on_note(State(), note, 100, L)[1] == ()


def test_note_off_and_play_mode_do_nothing():
    assert on_note(State(), 50, 0, L)[1] == ()
    assert on_note(State(mode=PLAY), 50, 100, L)[1] == ()


def test_section_row_keeps_key():
    assert section_row(2, 1, 13) == 15
    assert section_row(40, 0, 13) == 1


def test_kept_parts_from_clip_name():
    assert kept_parts("Riser [Bass, Part A, Part B]", PARTS) == {1, 2, 3}
    assert kept_parts("03 Lead [drums]", PARTS) == {0}
    assert kept_parts("Boomer FX 01", PARTS) == frozenset()


def test_b8_toggles_phrase_sync_on_every_press():
    s, a = cc(State(), 10, 64)
    assert s.phrase and a == (Action("phrase", flag=True),)
    s, a = cc(s, 10, 64)
    assert not s.phrase and a == (Action("phrase", flag=False),)


def test_phrase_release_lands_on_next_phrase_start():
    assert phrase_release(now=5.0, phrase=16.0, bar=4.0) == (12.0, 16.0)
    assert phrase_release(now=13.5, phrase=16.0, bar=4.0) == (12.0, 16.0)  # already in last bar
    assert phrase_release(now=16.0, phrase=16.0, bar=4.0) == (28.0, 32.0)  # on the 1: next phrase
    assert phrase_release(now=1.0, phrase=2.0, bar=4.0) == (0.0, 4.0)      # never shorter than a bar


def test_resume_lands_in_last_bar_of_break():
    assert resume_beat(now=33.1, bar=4.0, break_length=16.0) == 44.0
    assert resume_beat(now=33.1, bar=4.0, break_length=2.0) == 32.0
