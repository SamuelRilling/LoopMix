"""Pure controller logic: (state, MIDI event) -> (new state, actions).

No Live imports, so it runs and is tested outside Ableton.
Python 3.7 compatible (Live 11.0 ships Python 3.7).

Loop mode keyboard (25 keys, offsets from the lowest C):
  0            stop the selected part
  13 white     D..B, C, D..B  -> loop rows 1..13 of the current section
  5 black low  C# D# F# G# A# -> break rows 1..5 (others stop, then resume)
  5 black high C# D# F# G# A# -> FX 1..5 (instant, one track each, so they overlap)
  24 (top C)   unused
Octave buttons each send their own CC (latching, so any value = one press).
Loop mode: they move between sections. Play mode: they shift the Play octave.
"""
import math
import re
from typing import FrozenSet, NamedTuple, Sequence, Tuple

LOOP = "loop"
PLAY = "play"

LOOP_KEYS = (2, 4, 5, 7, 9, 11, 12, 14, 16, 17, 19, 21, 23)
BREAK_KEYS = (1, 3, 6, 8, 10)
FX_KEYS = (13, 15, 18, 20, 22)
STOP_KEY = 0
MAX_OCTAVE = 3


class State(NamedTuple):
    mode: str = LOOP
    part: int = 0     # index into the Set's part tracks
    section: int = 0
    octave: int = 0   # Play mode octave
    phrase: bool = False  # phrase sync: loops start only on the phrase's first beat


class Action(NamedTuple):
    kind: str      # fire | stop | select | mode | section | breakdown | fx | octave | phrase
    part: int = 0
    row: int = 0
    mode: str = LOOP
    section: int = 0
    octave: int = 0
    flag: bool = False


class Layout(NamedTuple):
    mode_cc: int
    part_ccs: Tuple[int, ...]
    octave_up_cc: int
    octave_down_cc: int
    phrase_cc: int
    base_note: int
    latch: bool
    rows_per_section: int
    same_value_ccs: Tuple[int, ...] = ()   # buttons sending one value on every press


NO_ACTIONS = ()  # type: Tuple[Action, ...]


def is_press(value: int, latch: bool) -> bool:
    """Momentary buttons act on press only; latching ones on every change."""
    return latch or value > 0


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def on_cc(state: State, cc: int, value: int, layout: Layout,
          section_count: int, part_count: int) -> Tuple[State, Tuple[Action, ...]]:
    if cc in (layout.octave_up_cc, layout.octave_down_cc):
        return on_octave(state, 1 if cc == layout.octave_up_cc else -1, section_count)
    if cc == layout.phrase_cc:  # B8 sends the same value on every press
        phrase = not state.phrase
        return state._replace(phrase=phrase), (Action("phrase", flag=phrase),)
    if not is_press(value, layout.latch) and cc not in layout.same_value_ccs:
        return state, NO_ACTIONS
    if cc == layout.mode_cc:
        mode = PLAY if state.mode == LOOP else LOOP
        return state._replace(mode=mode), (Action("mode", part=state.part, mode=mode),)
    if cc in layout.part_ccs and state.mode == LOOP:
        part = layout.part_ccs.index(cc)
        if part >= part_count:   # the Set has fewer parts than buttons
            return state, NO_ACTIONS
        return state._replace(part=part), (Action("select", part=part),)
    return state, NO_ACTIONS


def on_octave(state: State, step: int, section_count: int) -> Tuple[State, Tuple[Action, ...]]:
    if state.mode == PLAY:
        octave = clamp(state.octave + step, -MAX_OCTAVE, MAX_OCTAVE)
        if octave == state.octave:
            return state, NO_ACTIONS
        return state._replace(octave=octave), (Action("octave", octave=octave),)
    section = clamp(state.section + step, 0, max(section_count - 1, 0))
    if section == state.section:
        return state, NO_ACTIONS
    return state._replace(section=section), (Action("section", section=section),)


def on_note(state: State, note: int, velocity: int, layout: Layout) -> Tuple[State, Tuple[Action, ...]]:
    if velocity == 0 or state.mode != LOOP:
        return state, NO_ACTIONS
    key = note - layout.base_note
    first = state.section * layout.rows_per_section
    if key == STOP_KEY:
        return state, (Action("stop", part=state.part),)
    if key in LOOP_KEYS:
        return state, (Action("fire", part=state.part, row=first + LOOP_KEYS.index(key)),)
    if key in BREAK_KEYS:
        return state, (Action("breakdown", row=first + BREAK_KEYS.index(key)),)
    if key in FX_KEYS:
        return state, (Action("fx", part=FX_KEYS.index(key), row=first),)
    return state, NO_ACTIONS


def section_row(row: int, section: int, rows_per_section: int) -> int:
    """Same key, other section: row 2 of section 0 -> row 2 of `section`."""
    return section * rows_per_section + row % rows_per_section


def kept_parts(clip_name: str, part_names: Sequence[str]) -> FrozenSet[int]:
    """Parts named in brackets keep playing during a break: 'Riser [Bass, Part B]'."""
    tagged = {n.strip().lower() for group in re.findall(r"\[([^\]]*)\]", clip_name)
              for n in group.split(",")}
    return frozenset(i for i, name in enumerate(part_names) if name.lower() in tagged)


def phrase_release(now: float, phrase: float, bar: float) -> Tuple[float, float]:
    """(release beat, start beat) for a launch held for the next phrase.

    The start is the next phrase boundary after `now`. Releasing the launch in
    the bar before it lets Live's 1-bar quantization land it exactly there.
    """
    phrase = max(phrase, bar)
    start = (math.floor(now / phrase) + 1) * phrase
    return start - bar, start


def resume_beat(now: float, bar: float, break_length: float) -> float:
    """Beat at which to relaunch stopped parts: inside the break's last bar.

    The break started on the bar at or before `now`; firing during its last
    bar makes Live's 1-bar launch quantization land exactly on the break's end.
    """
    start = math.floor(now / bar) * bar
    return start + max(break_length - bar, 0.0)
