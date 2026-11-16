# LoopMix

**A GarageBand / Roland-style loop player for Ableton Live 11, played from a 25-key MIDI keyboard.**

Pick a part, press a key, and a loop starts on the next bar. Step up through sections as the music builds, drop a break, fire an
effect on top, then switch to Play mode and play a lead over it. LoopMix brings that "Loop Mix" workflow from Roland's
GO:KEYS to Ableton Live with a Behringer UMX25, and adds tools that turn GarageBand's loop library or any loop kit into
ready-to-play sets, including an agent prompt that builds a set from one line such as *"make a set that sounds like
classical music"*.

## What it does
- **Sets shaped to the music.** Each set has its own 1–6 instrument tracks: an orchestra set has Strings, Low Strings,
  Woodwinds, Brass and Harp; an electro house set has Beats, Bass, Synths, Music Beds and Toppers. No empty tracks.
- **Loops on the white keys.** 13 loops per part per section, ordered from mellow to busy. Everything launches on the next bar.
- **Sections on the octave buttons.** Each section is a step on an energy ladder (GarageBand packs) or a song section
  (loop kits). Changing section moves every playing part to the same key in the new section, in time.
- **Breaks and FX on the black keys.** Breaks play once while chosen parts pause, then everything comes back on the bar.
  FX are instant, overlap, and retrigger on every press.
- **Phrase sync (B8).** Loops wait for the start of the phrase, so every part shares one downbeat.
- **Play mode (B1).** The keys play a synth over the running loops; the octave buttons shift it.
- **Key map page.** A live view on `http://127.0.0.1:9890`: song position, a beat ring per part (like Live's clip pie),
  the section ladder, and every key labelled with its loop, break or FX.
- **No glitches from warping.** Loops that need a new tempo or key are rendered once, offline, with the Rubber Band engine;
  Live plays every clip as plain audio.

## How it works
```
GarageBand packages ──(pack.json)──► tools/garageband_set.py ─┐
loop kit WAVs ───────(kit.json)───► tools/kit_set.py ─────────┼─► sets/<kit>/layout.json ─► tools/als_writer.py ─► <Set>.als
                                                              │                         └─► tools/viz_preview.py (key map, no Live)
                                                              └─ staged WAVs (rendered to the set's tempo and key)

UMX25 ──MIDI──► LoopMix/ remote script inside Live ──► launches clips, serves the key map page
```
- **`LoopMix/`** is an Ableton remote script: `logic.py` turns key and button presses into actions (pure Python, unit-tested),
  `loop_mix.py` runs them in Live (bar-quantized launches, break pause/resume, phrase sync), `viz.py` serves the key map page.
- **GarageBand sets** are described by a small `pack.json`: rules on GarageBand's own loop tags (instrument category, key,
  scale, tempo, *Fill* phrases) pick which loops go to which track. Tempo and key can be chosen automatically to give every
  part the most full sections. The audio and tags come straight from Apple's content packages.
- **Loop kits** are described by `kit.json`: which folders feed which track, and how to read the song section from a file
  name. Tempo and key are read from the WAVs' embedded ACID metadata when present.
- **Live 11 can't import audio through its API**, so the Set file itself is generated (`.als` is gzipped XML) from
  `templates/base.als`.

## Getting started
Requirements: Windows, Ableton Live 11, Python 3 with numpy, ffmpeg with the `rubberband` filter, a Behringer UMX25
(other keyboards work after editing `LoopMix/config.py`).

1. **Install** — [docs/setup.md](docs/setup.md): set your folders in `tools/settings.py`, link `LoopMix/` into Live's MIDI
   Remote Scripts, link the sample folder into your User Library, assign the UMX25's octave buttons.
2. **Build a set** — give an AI agent [prompts/make-a-set.md](prompts/make-a-set.md) plus a style, pack or link; or run the
   tools yourself ([docs/building-sets.md](docs/building-sets.md)):
   ```
   python tools/garageband_set.py sets/classical/pack.json
   python tools/als_writer.py templates/base.als sets/classical/layout.json "sets/classical/Classical.als"
   python tools/viz_preview.py sets/classical/layout.json
   ```
3. **Play** — open the `.als` in Live, open the key map page, pick a part with B2–B7 and press keys.

## Included sets
Set descriptions only — **no audio is included**. GarageBand's loops are licensed to owners of Apple devices and are
downloaded from Apple's content server by the tools; free kits are downloaded from their publishers.

| Set | Source | Tracks | Sections |
|---|---|---|---|
| `classical` | GarageBand Symphony Orchestra | Strings, Low Strings, Woodwinds, Brass, Harp (+ timpani/cymbal FX, orchestral breaks) | 3 · D major · 100 BPM |
| `electro-house` | GarageBand Electro House | Beats, Bass, Synths, Music Beds, Toppers (+ transitions, impacts) | 4 · C minor · 128 BPM |
| `prog-rock-1` | MusicRadar SampleRadar prog rock kit | Drums, Bass, Guitars, Organ, Rhodes (+ lead breaks, drum-hit FX) | 6 song sections · G · 138 BPM |

## Controls (UMX25)
| Control | Loop mode | Play mode |
|---|---|---|
| B1 | → Play mode | → Loop mode |
| B2–B7 | Select part 1–6 | — |
| B8 | Phrase sync on/off | — |
| Lowest C | Stop the selected part | play |
| 13 white keys | Loops of the selected part in this section | play |
| Lower black keys | Breaks | play |
| Upper black keys | FX | play |
| Octave ◄ ► | Previous / next section | Octave down / up |

## Docs
| | |
|---|---|
| [docs/setup.md](docs/setup.md) | Live preferences, links, UMX25 ASSIGN steps, audio driver (ASIO recommended) |
| [docs/controls.md](docs/controls.md) | every button and key, both modes, `LoopMix/config.py` settings |
| [docs/architecture.md](docs/architecture.md) | remote script, `logic.py`, timing, key map server |
| [docs/building-sets.md](docs/building-sets.md) | both pipelines, `pack.json` / `kit.json` / `layout.json`, offline rendering, `.als` writer, checklist |
| [docs/troubleshooting.md](docs/troubleshooting.md) | log file, replaying a session, restarts, glitches, latency |
| [prompts/](prompts) | for an AI agent: start with `make-a-set.md` (routes to `garageband-set.md` or `kit-set.md`, then `build-in-live.md`) |

## Repository
```
LoopMix/    remote script: config.py (edit), logic.py (pure, tested), loop_mix.py (Live glue), viz.py + viz.html (key map)
tools/      settings.py (machine paths), garageband_set.py, kit_set.py, als_writer.py, apple_loops.py, audio.py,
            render_loops.py, make_template.py, viz_preview.py, replay_log.py
templates/  base.als — Play track + one prototype audio track the writer clones, returns, master
sets/       <kit>/pack.json or kit.json + layout.json; generated .als files are git-ignored
prompts/    agent prompts            docs/  documentation            tests/  python -m pytest -q tests
```
`.overcoder/` holds the project's planning state and run log.

## Status
Built and tested on Windows 10 with Ableton Live 11.0 and a Behringer UMX25. With the Ableton MCP server on Live 12.0.5+,
an agent can build the Set directly in Live instead of generating the file (see `prompts/build-in-live.md`).
