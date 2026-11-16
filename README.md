# LoopMix — UMX25 loop player for Ableton Live 11

One kit per Live Set. The octave buttons move between the kit's sections.

## Controls
| Control | Loop mode | Play mode |
|---|---|---|
| B1 | → Play mode | → Loop mode |
| B2–B6 | Select Drums / Bass / Part A / Part B / Part X | — |
| Lowest C | Stop the selected part at the next bar | plays guitar |
| 13 white keys D3 … B4 | Loops 1–13 of the selected part in this section (1 = mellow) | plays guitar |
| Lower black keys | Breaks 1–5: plays once, parts not named in its `[brackets]` stop and restart when it ends | plays the lead |
| Upper black keys | FX 1–5: instant, one track per key so they overlap, restart on every press | plays the lead |
| Octave ► / ◄ (CC 20 / 21) | Next / previous section; playing parts move to the same key on the next bar | Lead octave +/− (Pitch device on Play) |
| B8 (CC 10) | Phrase sync on/off: loops launched by keys or section changes wait for the next phrase start (phrase = longest loop playing), so all loops share one downbeat. Breaks stay on the bar, FX stay instant. | same |

Key map in a browser beside Live: <http://127.0.0.1:9890> (served by the script; `VIZ_PORT = None` turns it off).
It shows bar.beat, the beats of the bar, the position in the phrase, and a beat ring per part
(Live's clip pie: one segment per beat, bar starts darker). Queued loops show a countdown.

## Layout
```
LoopMix/              remote script (junction-linked into Resources\MIDI Remote Scripts\LoopMix)
  config.py           CCs, base note, track names, rows per section, viz port  <- edit this
  logic.py            pure logic, tested in tests/
  loop_mix.py         Ableton glue;  viz.py + viz.html = key map page
tools/
  apple_loops.py      reads GarageBand's loop tags from Apple's .pkg content packages
  garageband_set.py   GarageBand pack -> sets/<kit>/layout.json + staged WAVs
  als_writer.py       layout.json + a working Set as template -> generated .als
  rank_energy.py      shared audio analysis (loudness, busyness)
samples/staged/       linked into the User Library as Samples/LoopMix
sets/electro-house/   layout.json + Electro House.als
```
Rows: section n = Session rows (n−1)·13 … n·13−1. Scene names `S2 Groove · D3`
give the section its name. Break and FX tracks use rows 1–5 of each section.

## Making a set from a GarageBand pack
```
python tools/garageband_set.py "<folder of WAVs>" <Apple .pkg> [<Apple .pkg> ...]
python tools/als_writer.py "<working LoopMix.als>" sets/electro-house/layout.json "sets/electro-house/Electro House.als"
```
Roles come from GarageBand's tags (Bass, Keyboards, Mixed, Drums, Sound Effect);
drums split into beats and toppers by kick content. Melodic loops are retuned to
the most common key (≤ 5 semitones), major-only loops are left out, sections are
always full (13 per part) and ordered Warm-up → Peak by energy.

Loops that need a new key or tempo are rendered offline (`tools/render_loops.py`,
ffmpeg's Rubber Band filter, seamless wrap-around), so Live plays every clip
without warping or pitch-shifting: no live CPU cost, no warp artifacts.
`tools/replay_log.py` replays the last session's log into the clips each press launched.

## Hardware
UMX25 factory buttons send latching CCs: B1 = 97, B2–B6 = 96, 66, 67, 64, 65.
Octave buttons: ASSIGN mode, each its own controller: right = 20, left = 21 (they latch too).
The generated Set's Play track = Pitch → Wavetable "Bright SAW Lead"; FX live on tracks FX 1–5.
Live → Preferences → Link/Tempo/MIDI: Control Surface **LoopMix**, Input UMX 25, Output None.
Debug: `%APPDATA%\Ableton\Live 11.0\Preferences\Log.txt`, search `LoopMix`.
Script changes load only after restarting Live.

## Tests
`python -m pytest -q tests`
