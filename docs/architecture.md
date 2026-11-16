# Architecture

```
LoopMix/__init__.py   create_instance(): Live's entry point; imports loop_mix lazily
LoopMix/config.py     hardware CCs, track names, rows per section, viz port
LoopMix/logic.py      pure: (State, MIDI event) -> (State, Actions). No Live imports; Python 3.7; tested
LoopMix/loop_mix.py   ControlSurface subclass: listens to MIDI, runs Actions against Live's API, timing, snapshots
LoopMix/viz.py        read-only HTTP server in a daemon thread
LoopMix/viz.html      key map page (polls /state)
```

## logic.py
`State(mode, part, section, octave, phrase)`; `on_cc` and `on_note` return the new state and a tuple of `Action`s
(`fire stop select mode section breakdown fx octave phrase`). `Layout` bundles the CC numbers, base note, latch flag and
`rows_per_section`. Key offsets (`LOOP_KEYS`, `BREAK_KEYS`, `FX_KEYS`, `STOP_KEY`) live here. Also pure helpers:
`section_row` (same key, other section), `kept_parts` (parses `[brackets]`), `phrase_release`, `resume_beat`.
`tools/replay_log.py` reuses `on_cc`/`on_note` offline.

## loop_mix.py
Registers a `ButtonElement` for each CC (mode, octave ×2, phrase, parts) and for all 128 notes (listeners attached only in
Loop mode via `_set_keys_captured`, so Play mode notes reach the armed track). Each event is logged to `Log.txt`
(`LoopMix CC n = v`, `LoopMix note n vel v`), passed to `logic`, and each returned `Action` runs as `_do_<kind>`;
exceptions are logged, never raised into Live. `update_display()` (Live calls it every display tick) drives the polling and snapshots.

## Timing
- **Next-bar launch.** Loops fire with Live's own quantization: the generated clips use Global launch quantization (1 bar),
  so Live starts them sample-accurately. The script never schedules clip starts itself.
- **Break stop/resume.** Break fires (once, on the bar) and the non-kept parts are stopped in the same call, so both land on
  the same bar. `_poll_break` waits until the break plays, computes `resume_beat` = start of its bar + (break length − 1 bar),
  and when the song position passes it relaunches the stopped parts; Live's 1-bar quantization then starts them exactly at the
  break's end. If the break never started, the parts relaunch at once; if the transport stopped, the list is dropped.
- **Phrase sync release.** With B8 on, a launch is stored in `_pending`. `_poll_pending` computes `phrase_release`: the next
  phrase boundary after now, minus one bar; once the song time passes it, the held clips fire and Live's quantization lands them
  on the phrase start. Phrase length = longest playing or pending clip, at least one bar.
- **FX instant tracks.** FX clips have launch quantization "None" and sit on separate tracks (one per key), so a press sounds
  immediately, presses overlap, and re-pressing restarts the clip.

## Key map server
`viz.py` serves `/` (viz.html) and `/state` (JSON) on `127.0.0.1:VIZ_PORT`. The main thread stores a plain dict snapshot
every `VIZ_EVERY` (2) display ticks; the server thread only serialises it and adds `age`, so Live's API is touched from
one thread. `LocalServer` overrides `server_bind` to skip `socket.getfqdn()`: Live's embedded Python lacks the `idna` codec, and
`HTTPServer.server_bind` would raise on the name lookup. If the server fails to start, the script logs "key map disabled" and
carries on. Details: [prompts/key-map-viz.md](../prompts/key-map-viz.md).

## Tools data flow
```
GarageBand WAVs + Apple .pkg  --garageband_set.py-->  sets/electro-house/layout.json + samples/staged/Electro House/
song kit WAVs + kit.json      --kit_set.py---------->  sets/<kit>/layout.json         + samples/staged/<kit>/
layout.json + templates/base.als --als_writer.py-->  <name>.als      layout.json --set_map.py--> set-map.html
```
Shared: `audio.py` (loudness/onset energy, rank, spread), `render_loops.py` (offline retune/re-tempo), `apple_loops.py`
(GarageBand tags from `.pkg`), `settings.py` (paths). See [building-sets.md](building-sets.md).
