# Building sets

Live 11's API can't import audio, so a set is built offline: source loops → `sets/<kit>/layout.json` (+ staged WAVs under
`settings.STAGED`) → a generated `.als`. Samples and `.als` files are git-ignored; `layout.json` is the tracked source of truth.

## Pipeline 1: GarageBand pack — `tools/garageband_set.py`
```
python tools/garageband_set.py "<folder of WAVs>" <Apple .pkg> [<Apple .pkg> ...]
```
Output is fixed: `sets/electro-house/layout.json` and `<STAGED>/Electro House/<track>/`. Tempo is fixed at 128 (`TEMPO`).
- **Tags** come from Apple's `.pkg` (`apple_loops.py` reads the xar → cpio → `.caf` `uuid` chunk): category, subcategory,
  key signature, key type, beat count, descriptors, plus AAC `priming frames` / `valid frames`. Loops absent from the
  packages borrow a numbered sibling's tags.
- **Roles:** Bass → Bass, Keyboards → Part A, Mixed → Part B; Drums → Drums if ≥ 35% of the energy (30–120 Hz vs > 30 Hz) is
  kick, otherwise Part X; Sound Effect / "Impacts & Crashes" → FX; other Sound Effects and untagged → Break.
- **Filter:** arrhythmic loops are dropped from the five parts; the set is minor, so major-only loops go; the most common root
  becomes the key (`<root> minor`); loops needing more than 5 semitones of retune go.
- **Sections:** `min(pool sizes) // 13` full sections, each part exactly 13 loops per section, ordered Warm-up → Peak by
  energy (mean rank of loudness and onset rate, ±0.25 for the Intense/Relaxed tag). Tonal parts pick the least retuned loops
  first. 3–5 sections get names (Warm-up, Groove, [Lift,] Drive, Peak), otherwise `Level n`.
- **Breaks:** 5 per section, `[Bass, Part A, Part B]` kept (drums drop out). **FX:** key *k* of every section on track `FX k`.
- Needs `ffmpeg` (Rubber Band) for loops that must be retuned or re-tempoed; the rest are copied.

Licence: you need an Apple device / GarageBand to use these loops. Apple's original `.pkg` files (for tags only) come
from `audiocontentdownload.apple.com`; the audio is your own WAV export. Nothing from Apple is stored in the repo.

## Pipeline 2: song kit — `tools/kit_set.py`
```
python tools/kit_set.py sets/<kit>/kit.json
```
Writes `sets/<kit>/layout.json` next to `kit.json` and stages WAVs under `<STAGED>/<name>/`. Sections are the kit's own song
sections, not an energy ladder: loops of one song section share harmony. No retune: every file must already be in one key.

`kit.json` (see `sets/prog-rock-1/kit.json`):
| Field | Meaning |
|---|---|
| `name` | staging folder and Live sample folder name; use the folder name of `sets/<kit>` |
| `source` | folder of the unzipped kit |
| `tempo` | the kit's BPM (one per kit) |
| `key` | label only, shown in `layout.json`/set map |
| `section_pattern` | regex with **one group** applied to each WAV file name; the group is the section id (`-(\d+)\.wav$` → `03`) |
| `parts` | `{"Drums"\|"Bass"\|"Part A"\|"Part B"\|"Part X": [subfolders of source]}`; omit parts the kit lacks |
| `break` | optional `{"folders": [...], "keep": [part names]}`; kept parts keep playing during the break |
| `fx` | optional `{"folders": [...]}`; hits are not sectioned, spread over `FX 1`–`FX 5` |

Numeric ids sort numerically and become `Section n`; non-numeric ids sort after, by name. Within a section a part's loops run
mellow → busy over the keys; more than 13 are thinned evenly, fewer leave keys empty (sections are not padded). Breaks: up to 5
per section. WAVs must be 44.1 kHz, 16/24-bit PCM. Loops are clipped to whole bars (≥ 4 beats); any loop more than 1 ms off its
bar length is rendered offline.

## `layout.json`
Top level: `tempo` (BPM, float), `key` (string, display), `rows_per_section` (13), `sections` (names, in order),
`tracks` (`{track: [clip,…]}`), `left_out` (`{track: pool size − clips used}`; informational).
Tracks: `Drums`, `Bass`, `Part A`, `Part B`, `Part X`, `Break`, `FX 1`…`FX 5` (names must equal `config.py`).

Clip fields (`als_writer` reads those marked *):
| Field | Meaning |
|---|---|
| `row`* | Session row = `section × 13 + key index` (breaks: key index 0–4; FX: first row of the section) |
| `name`* | clip name and scene label source; breaks end with ` [Kept, Parts]` |
| `path`* | absolute staged WAV path containing `/samples/staged/` |
| `beats`* | clip length in beats |
| `audio_beats` | length of the sound itself in beats (one-shots keep this speed) |
| `priming`*, `frames`* | skip `priming` frames (AAC padding), then `frames` frames of audio; 0 for rendered/kit files |
| `shift`* | semitones of Live pitch; 0 after offline rendering |
| `root`, `energy` | source key (or null) and 0–1 rank used for ordering; informational |
| `loop`* | false for breaks and FX (play once) |
| `instant`* | true for FX: launch quantization None |
| `rendered_from`, `file` | GarageBand only: original shift before rendering; source file name |

## Offline rendering, no live warping
Retuning or re-tempoing a dense loop in Live (Complex warp) costs CPU and can glitch. `render_loops.render()` runs ffmpeg's
`rubberband` filter at high quality once per loop and writes a WAV exactly `beats` long at the set tempo and key. The loop is
tripled before stretching and the middle copy kept, so the wrap-around is seamless. After staging, clips have `shift` 0 and their
length equals their beat length, so the writer's two warp markers map the file 1:1 to the grid: Live plays them unwarped.

## `.als` generation — `tools/als_writer.py`
```
python tools/als_writer.py templates/base.als sets/<kit>/layout.json "sets/<kit>/<Name>.als"
```
A `.als` is gzip'd XML. The writer takes the template's tracks, rebuilds scenes and clip slots (13 rows × sections; scenes named
`S2 Groove · D3`), clones the `Break` track into any missing `FX n`, sets the tempo, and replaces the `Play` track's devices with
Pitch (`+ 12.adv`, `Manual` 0) → Wavetable "Bright SAW Lead" (paths from `settings.CORE_DEVICES`). Clip start/loop points, warp
markers, launch mode (loops: Global; FX: None), colour per section and warp mode (drums: Beats; melodic and retuned/stretched:
Complex) are set from the layout.

`templates/base.als` holds the tracks (Play, Drums, Bass, Part A, Part B, Part X, Break), returns and master, plus one session clip
as the clip template. Make a new one from any working Set that has those tracks and at least one audio clip in a session slot:
```
python tools/make_template.py "<working.als>" [templates/base.als]
```
It strips arrangement clips and all session clips except the first.

## Validation checklist
1. `layout.json`: every loop part has clips in every section you expect; each loop's `frames` ≈ `beats × 60 / tempo × 44100`
   (within 1 ms) and `shift` is 0; every `path` exists; breaks name kept parts that exist; one tempo, one key.
2. `python tools/viz_preview.py sets/<kit>/layout.json --section N --part N` and open the URL it prints: no empty key where you expected a loop (Ctrl+C to stop).
3. `.als`: scene count = sections × 13; clip count = clips in layout; no missing samples (command in
   [prompts/build-in-live.md](../prompts/build-in-live.md)).
4. In Live: open the Set (choose **Don't Save** if an older copy is open), restart Live if `LoopMix/` changed, press every key
   of one section, one break, one FX, an octave button; check the key map page.
