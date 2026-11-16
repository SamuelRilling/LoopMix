"""Ableton glue: turns UMX25 MIDI into logic.py events and runs the actions."""
from __future__ import absolute_import

import re
import traceback

from _Framework.ButtonElement import ButtonElement
from _Framework.ControlSurface import ControlSurface
from _Framework.InputControlElement import MIDI_CC_TYPE, MIDI_NOTE_TYPE

from . import config
from .logic import (BREAK_KEYS, FX_KEYS, LOOP, LOOP_KEYS, PLAY, Layout, State, kept_parts,
                    on_cc, on_note, phrase_release, resume_beat, section_row)

LAYOUT = Layout(
    mode_cc=config.MODE_CC,
    part_ccs=tuple(config.PART_CCS),
    octave_up_cc=config.OCTAVE_UP_CC,
    octave_down_cc=config.OCTAVE_DOWN_CC,
    phrase_cc=config.PHRASE_CC,
    base_note=config.BASE_NOTE,
    latch=config.BUTTONS_LATCH,
    rows_per_section=config.ROWS_PER_SECTION,
    same_value_ccs=tuple(config.SAME_VALUE_CCS),
)
MAX_PARTS = len(config.PART_CCS)
ROWS = config.ROWS_PER_SECTION
VIZ_EVERY = 2  # update_display ticks between key map snapshots; the page animates in between


class LoopMix(ControlSurface):
    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        self._state = State()
        self._clear_break()
        self._pending = {}        # phrase sync: part index -> row waiting for the phrase start
        self._pending_start = None
        self._tick = 0
        ch = config.MIDI_CHANNEL
        with self.component_guard():
            ccs = (config.MODE_CC, config.OCTAVE_UP_CC, config.OCTAVE_DOWN_CC,
                   config.PHRASE_CC) + tuple(config.PART_CCS)
            self._buttons = [ButtonElement(True, MIDI_CC_TYPE, ch, cc) for cc in ccs]
            # All 128 notes: in Loop mode no key may leak through to a track.
            self._keys = [ButtonElement(True, MIDI_NOTE_TYPE, ch, n) for n in range(128)]
            self._probes = [ButtonElement(True, MIDI_CC_TYPE, ch, cc)
                            for cc in range(128) if config.LOG_ALL_CCS and cc not in ccs]
        for b in self._buttons:
            b.add_value_listener(self._on_button, identify_sender=True)
        for p in self._probes:
            p.add_value_listener(self._on_probe, identify_sender=True)
        self._set_keys_captured(True)
        self._viz = self._start_viz()
        self.log_message("LoopMix loaded (Loop mode)")
        self.show_message("LoopMix: LOOP mode")

    def disconnect(self):
        for b in self._buttons:
            b.remove_value_listener(self._on_button)
        for p in self._probes:
            p.remove_value_listener(self._on_probe)
        self._set_keys_captured(False)
        if self._viz is not None:
            self._viz.close()
        ControlSurface.disconnect(self)

    # --- MIDI in ---------------------------------------------------------

    def _on_button(self, value, sender):
        cc = sender.message_identifier()
        self.log_message("LoopMix CC %d = %d" % (cc, value))
        self._apply(on_cc(self._state, cc, value, LAYOUT, self._section_count(), len(self._parts())))

    def _on_probe(self, value, sender):
        self.log_message("LoopMix unassigned CC %d = %d" % (sender.message_identifier(), value))

    def _on_key(self, value, sender):
        self.log_message("LoopMix note %d vel %d" % (sender.message_identifier(), value))
        self._apply(on_note(self._state, sender.message_identifier(), value, LAYOUT))

    def _set_keys_captured(self, captured):
        """Loop mode: the script owns the keys. Play mode: keys go to the armed track."""
        for k in self._keys:
            if captured and not k.value_has_listener(self._on_key):
                k.add_value_listener(self._on_key, identify_sender=True)
            elif not captured and k.value_has_listener(self._on_key):
                k.remove_value_listener(self._on_key)
        self.request_rebuild_midi_map()

    # --- helpers ---------------------------------------------------------

    def _apply(self, result):
        self._state, actions = result
        for action in actions:
            try:
                getattr(self, "_do_" + action.kind)(action)
            except Exception:
                self.log_message("LoopMix error on %r:\n%s" % (action, traceback.format_exc()))

    def _track(self, name, quiet=False):
        track = next((t for t in self.song().tracks if t.name == name), None)
        if track is None and not quiet:
            self.show_message("LoopMix: no track named '%s'" % name)
        return track

    def _parts(self):
        """Part tracks: the Set's audio tracks other than Break and FX, in Set order."""
        others = (config.BREAK_TRACK,) + tuple(config.FX_TRACKS)
        return [t for t in self.song().tracks if t.has_audio_input and t.name not in others][:MAX_PARTS]

    def _part_track(self, part):
        parts = self._parts()
        return parts[part] if part < len(parts) else None

    def _section_count(self):
        return max(len(self.song().scenes) // ROWS, 1)

    def _section_name(self, section):
        scenes = self.song().scenes
        row = section * ROWS
        name = scenes[row].name if row < len(scenes) else ""
        match = re.match(r"S\d+\s+(.+?)\s+\S\s+\S+$", name)
        return match.group(1) if match else "Section %d" % (section + 1)

    def _fire_slot(self, track, row):
        """Fire `row`, or the nearest clip above it in the same section."""
        first = row - row % ROWS
        for r in range(row, first - 1, -1):
            if r < len(track.clip_slots) and track.clip_slots[r].has_clip:
                track.clip_slots[r].fire()
                return

    def _fire_once(self, name, row):
        track = self._track(name, quiet=True)   # Break / FX tracks are optional
        if track is None or row >= len(track.clip_slots) or not track.clip_slots[row].has_clip:
            return None
        slot = track.clip_slots[row]
        slot.clip.looping = False
        slot.fire()
        return slot

    # --- actions ---------------------------------------------------------

    def _launch(self, part, row):
        """Fire now (next bar), or hold for the phrase start when phrase sync is on."""
        if self._state.phrase and self.song().is_playing:
            self._pending[part] = row
            return
        track = self._part_track(part)
        if track is not None:
            self._fire_slot(track, row)

    def _do_fire(self, action):
        track = self._part_track(action.part)
        if track is not None and action.row < len(track.clip_slots) and track.clip_slots[action.row].has_clip:
            self._launch(action.part, action.row)

    def _do_stop(self, action):
        self._pending.pop(action.part, None)
        track = self._part_track(action.part)
        if track is not None:
            track.stop_all_clips()

    def _do_phrase(self, action):
        if not action.flag:
            self._release_pending()  # nothing stays held once sync is off
        self.show_message("LoopMix: phrase sync %s" % ("ON" if action.flag else "OFF"))

    def _do_select(self, action):
        track = self._part_track(action.part)
        if track is not None:
            self.song().view.selected_track = track
            self.show_message("LoopMix: %s" % track.name)

    def _do_mode(self, action):
        play = self._track(config.PLAY_TRACK)
        if play is not None and play.can_be_armed:
            play.arm = action.mode == PLAY
        self._set_keys_captured(action.mode == LOOP)
        if action.mode == PLAY and play is not None:
            self.song().view.selected_track = play
        else:
            self._do_select(action)
        self.show_message("LoopMix: %s mode" % action.mode.upper())

    def _do_section(self, action):
        """Every playing part moves to the same key in the new section, on the next bar."""
        for part, track in enumerate(self._parts()):
            if track.playing_slot_index >= 0:
                self._launch(part, section_row(track.playing_slot_index, action.section, ROWS))
        self._resume = dict((p, section_row(row, action.section, ROWS)) for p, row in self._resume.items())
        self._pending = dict((p, section_row(row, action.section, ROWS)) for p, row in self._pending.items())
        self.show_message("LoopMix: section %d/%d - %s" % (
            action.section + 1, self._section_count(), self._section_name(action.section)))

    def _do_fx(self, action):
        """Each FX key has its own track and launches instantly; pressing it again restarts it."""
        self._fire_once(config.FX_TRACKS[action.part], action.row)

    def _do_octave(self, action):
        play = self._track(config.PLAY_TRACK)
        device = next((d for d in play.devices if d.class_name == "MidiPitcher"), None) if play else None
        param = next((p for p in device.parameters if p.name == "Pitch"), None) if device else None
        if param is None:
            self.show_message("LoopMix: add Live's Pitch device to the Play track for octaves")
            return
        param.value = max(param.min, min(param.max, 12.0 * action.octave))
        self.show_message("LoopMix: Play octave %+d" % action.octave)

    # --- breakdown -------------------------------------------------------
    # Fire: the break clip plays once; non-kept parts stop on the same bar
    # (both quantized by Live, so sample-accurate). update_display polls the
    # song position and relaunches the stopped parts during the break's last
    # bar, so Live's 1-bar quantization starts them exactly when it ends.

    def _clear_break(self):
        self._resume = {}         # part index -> slot row to relaunch
        self._break_row = None    # Break track row we are waiting on
        self._resume_at = None    # song beat at which to relaunch

    def _do_breakdown(self, action):
        brk = self._track(config.BREAK_TRACK, quiet=True)
        if brk is None or action.row >= len(brk.clip_slots) or not brk.clip_slots[action.row].has_clip:
            return
        parts = self._parts()
        keep = kept_parts(brk.clip_slots[action.row].clip.name, [t.name for t in parts])
        for part, track in enumerate(parts):
            if part in keep or track.playing_slot_index < 0:
                continue
            self._resume.setdefault(part, track.playing_slot_index)
            track.stop_all_clips()
        self._fire_once(config.BREAK_TRACK, action.row)
        self._break_row = action.row
        self._resume_at = None

    def update_display(self):
        ControlSurface.update_display(self)
        if self._break_row is not None:
            try:
                self._poll_break()
            except Exception:
                self.log_message("LoopMix break error:\n%s" % traceback.format_exc())
                self._clear_break()
        if self._pending:
            try:
                self._poll_pending()
            except Exception:
                self.log_message("LoopMix phrase error:\n%s" % traceback.format_exc())
                self._pending = {}
        self._tick += 1
        if self._viz is not None and self._tick % VIZ_EVERY == 0:
            try:
                self._viz.state = self._snapshot()
            except Exception:
                self.log_message("LoopMix viz error:\n%s" % traceback.format_exc())

    def _poll_break(self):
        song = self.song()
        brk = self._track(config.BREAK_TRACK, quiet=True)
        if brk is None or not song.is_playing:
            self._clear_break()
            return
        playing = brk.playing_slot_index
        if self._resume_at is None:
            if playing == self._break_row:
                bar = 4.0 * song.signature_numerator / song.signature_denominator
                length = brk.clip_slots[playing].clip.length
                self._resume_at = resume_beat(song.current_song_time, bar, length)
            elif brk.fired_slot_index < 0 and playing < 0:
                self._relaunch()  # break never started
            return
        if playing != self._break_row or song.current_song_time >= self._resume_at:
            self._relaunch()

    def _relaunch(self):
        for part, row in self._resume.items():
            track = self._part_track(part)
            # Skip parts the player relaunched by hand during the break.
            if track is not None and track.playing_slot_index < 0 and track.fired_slot_index < 0:
                self._fire_slot(track, row)
        self._clear_break()

    # --- phrase sync -----------------------------------------------------
    # Held launches are released in the bar before the next phrase start, so
    # Live's 1-bar quantization starts them exactly on the phrase's first beat.

    def _bar(self):
        song = self.song()
        return 4.0 * song.signature_numerator / song.signature_denominator

    def _phrase_beats(self):
        """Phrase = the longest loop playing or waiting to start (at least one bar)."""
        lengths = [self._bar()]
        for part, track in enumerate(self._parts()):
            for row in (track.playing_slot_index, self._pending.get(part, -1)):
                if 0 <= row < len(track.clip_slots) and track.clip_slots[row].has_clip:
                    lengths.append(track.clip_slots[row].clip.length)
        return max(lengths)

    def _poll_pending(self):
        song = self.song()
        if not song.is_playing:
            self._release_pending()
            return
        release, self._pending_start = phrase_release(song.current_song_time, self._phrase_beats(), self._bar())
        if song.current_song_time >= release:
            self._release_pending()

    def _release_pending(self):
        for part, row in self._pending.items():
            track = self._part_track(part)
            if track is not None:
                self._fire_slot(track, row)
        self._pending, self._pending_start = {}, None

    # --- key map page ----------------------------------------------------

    def _start_viz(self):
        if not config.VIZ_PORT:
            return None
        try:
            from .viz import Viz
            viz = Viz(config.VIZ_PORT)
            self.log_message("LoopMix key map on http://127.0.0.1:%d" % config.VIZ_PORT)
            return viz
        except Exception:
            self.log_message("LoopMix key map disabled:\n%s" % traceback.format_exc())
            return None

    def _snapshot(self):
        song, s = self.song(), self._state
        first = s.section * ROWS

        def clip(track, row):
            # playing_slot_index is negative when nothing plays; never index with it.
            if track is None or not 0 <= row < len(track.clip_slots) or not track.clip_slots[row].has_clip:
                return None
            return track.clip_slots[row].clip

        def clip_name(track, row):
            c = clip(track, row)
            return re.sub(r"\s*\[[^\]]*\]", "", c.name) if c is not None else ""

        def playing(track):
            return track.playing_slot_index if track is not None else -1

        def keys(track, offsets, kind):
            now = playing(track)
            return [dict(key=k, kind=kind, label=clip_name(track, first + i), playing=now == first + i)
                    for i, k in enumerate(offsets)]

        parts = []
        for i, t in enumerate(self._parts()):
            c = clip(t, playing(t))
            parts.append(dict(
                name=t.name, selected=i == s.part, playing=clip_name(t, playing(t)),
                position=c.playing_position if c is not None else None,
                length=c.length if c is not None else None,
                pending=clip_name(t, self._pending[i]) if i in self._pending else ""))
        part_track = self._part_track(s.part)

        def fx_key(index, key):
            return self._fx_key(index, key, first)

        return dict(
            mode=s.mode, octave=s.octave, section=s.section, tempo=round(song.tempo, 2),
            is_playing=song.is_playing, song_time=song.current_song_time, bar=self._bar(),
            phrase=s.phrase, phrase_beats=self._phrase_beats(), pending_start=self._pending_start,
            sections=[self._section_name(i) for i in range(self._section_count())],
            parts=parts, rows=ROWS,
            keys=keys(part_track, LOOP_KEYS, "loop")
            + keys(self._track(config.BREAK_TRACK, quiet=True), BREAK_KEYS, "break")
            + [fx_key(i, k) for i, k in enumerate(FX_KEYS)],
        )

    def _fx_key(self, index, key, first):
        track = self._track(config.FX_TRACKS[index], quiet=True)
        name = ""
        if track is not None and first < len(track.clip_slots) and track.clip_slots[first].has_clip:
            name = track.clip_slots[first].clip.name
        playing = track is not None and track.playing_slot_index == first
        return dict(key=key, kind="fx", label=name, playing=playing)
