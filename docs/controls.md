# Controls

Two modes, switched with B1. The script starts in **Loop** mode. Keys are numbered from the lowest C of the
UMX25 (`BASE_NOTE` = 48, C3).

| Control | Loop mode | Play mode |
|---|---|---|
| B1 (CC 97) | → Play (arms the `Play` track, keys go to its synth) | → Loop (disarms `Play`, script owns the keys again) |
| B2 (CC 96), B3 (66), B4 (67), B5 (64), B6 (65), B7 (7) | select part 1–6 of the Set, in track order (selects that track in Live); a button past the Set's part count does nothing | ignored |
| Bottom C (C3) | stop the selected part (at Live's launch quantization; also cancels a phrase-held launch) | plays notes |
| 13 white keys D3 E3 F3 G3 A3 B3 C4 D4 E4 F4 G4 A4 B4 | loops 1–13 of the selected part in the current section | play notes |
| Lower black keys C#3 D#3 F#3 G#3 A#3 | breaks 1–5 of the current section | play notes |
| Upper black keys C#4 D#4 F#4 G#4 A#4 | FX 1–5 | play notes |
| Top C (C5) | unused | plays notes |
| Octave right (CC 20) / left (CC 21) | next / previous section | Play octave +1 / −1 (limit ±3; sets the Pitch device on `Play` to 12 × octave semitones) |
| B8 (CC 10) | phrase sync on/off | same |

In Loop mode all 128 notes are captured, so no key leaks to a track.

## Loops (white keys)
Key *k* of the current section fires Session row `section × 13 + k` on the selected part's track. If that slot is empty
the nearest clip above it in the same section fires instead. Launching goes through Live's global launch quantization
(1 bar for the generated Sets), so it lands on the next bar. Several parts play together; pressing a key on another
part doesn't stop the first.

## Sections (octave buttons)
Section *n* = Session rows `(n−1)×13 … n×13−1`. Moving section relaunches every playing part on the **same key** in the
new section on the next bar; pending breaks and phrase-held launches move too. Limits: first and last section (no wrap).
Scene names such as `S2 Groove · D3` give the section its name (shown in Live's status bar and the key map).

## Breaks (lower black keys)
Break *k* fires once (loop off) on the `Break` track, row `section × 13 + k`. Parts not named in the clip's `[brackets]`
(for example `Riser [Bass, Part B]`; names are matched case-insensitively to the part names) stop on the same bar; they
restart during the break's last bar so they return exactly when it ends. Parts you relaunch by hand meanwhile are left alone.

## FX (upper black keys)
FX *k* lives on its own track `FX k`, in the **first row of the section**. One track per key so FX overlap; launch is
instant (no quantization) and pressing again restarts it.

## Phrase sync (B8)
Off by default. On: loop launches (keys or section change) wait until the next phrase start; phrase = the longest loop
playing or waiting (at least one bar). Everything then shares one downbeat. Breaks stay on the bar, FX stay instant.
Turning it off releases anything held. Only active while the transport runs.

## Settings — `LoopMix/config.py`
| Setting | Default | Meaning |
|---|---|---|
| `MIDI_CHANNEL` | 0 | channel the UMX25 sends on (0 = channel 1) |
| `MODE_CC` | 97 | B1 |
| `PART_CCS` | 96, 66, 67, 64, 65, 7 | B2–B7 → parts 1–6 |
| `BUTTONS_LATCH` | True | buttons send 127 then 0; every change counts as a press. False = act on value > 0 only |
| `OCTAVE_UP_CC` | 20 | right octave button |
| `OCTAVE_DOWN_CC` | 21 | left octave button |
| `SAME_VALUE_CCS` | 7 | buttons that send one value on every press (B7): any message is a press |
| `PHRASE_CC` | 10 | B8 |
| `BASE_NOTE` | 48 | note number of the lowest key (C3) |
| `LOG_ALL_CCS` | False | log every CC not otherwise used (to find button numbers) |
| `PLAY_TRACK` | `Play` | track armed in Play mode; needs a Pitch (MIDI effect) device for the octave buttons |
| `BREAK_TRACK` | `Break` | track holding breaks |
| `FX_TRACKS` | FX 1 … FX 5 | one track per FX key |
| `ROWS_PER_SECTION` | 13 | Session rows per section; sections = scenes // this |
| `VIZ_PORT` | 9890 | key map page port; `None` turns it off |

## Parts
Each Set carries its own part tracks (1–6, up to 6 parts): every audio track that is not `Break` or `FX 1`…`FX 5`, in Set
order, the first six on B2–B7. A Set has no empty tracks, so `Break` and each `FX n` exist only when the set has clips for
them; a break or FX key without its track does nothing. Only `Play` must be named exactly (a missing `Play` shows
"LoopMix: no track named …" in Live's status bar).
