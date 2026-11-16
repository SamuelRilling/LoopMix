# Building sets

Live 11's API can't import audio, so a set is built offline: source loops → `sets/<kit>/layout.json` (+ staged WAVs under
`settings.STAGED`) → a generated `.als`. Samples and `.als` files are git-ignored; `layout.json` is the tracked source of truth.

## Pipeline 1: GarageBand pack — `tools/garageband_set.py`
```
python tools/garageband_set.py [--out <dir>] [--staged <dir>] <Apple .pkg> [<Apple .pkg> ...]
```
Only the `.pkg` files are needed. Output: `sets/electro-house/layout.json` and `<STAGED>/Electro House/<track>/` (`--out`/`--staged`
redirect, e.g. to temp paths). Tempo is fixed at 128 (`TEMPO`).
- **Audio** is decoded from the packages: each `.caf` is extracted from the payload and decoded by ffmpeg to 16-bit 44.1 kHz WAV in
  `<STAGED>/../decoded/` (cache, outside git). ffmpeg already drops the AAC priming and trailing padding (checked: *Alpha Male Bass*
  decodes to 165375 frames = `valid frames`), so decoded files start on the beat and layouts use `priming` 0.
- **Tags** come from Apple's `.pkg` (`apple_loops.py` reads the xar → cpio → `.caf` `uuid` chunk): category, subcategory,
  key signature, key type, beat count, descriptors, plus `valid frames` (the decoded length). Loops without a category
  borrow a numbered sibling's tags.
- **Roles** (track names = GarageBand categories): Drums → `Beats` if ≥ 35% of the energy (30–120 Hz vs > 30 Hz) is
  kick, otherwise `Toppers`; Bass → `Bass`, Keyboards → `Synths`, Mixed → `Music Beds`. Parts in order: Beats, Bass, Synths,
  Music Beds, Toppers (B2–B6; `drum_parts` = Beats, Toppers); Sound Effect / "Impacts & Crashes" → FX; other Sound Effects and untagged → Break.
- **Filter:** arrhythmic loops are dropped from the five parts; the set is minor, so major-only loops go; the most common root
  becomes the key (`<root> minor`); loops needing more than 5 semitones of retune go.
- **Sections:** `min(pool sizes) // 13` full sections, each part exactly 13 loops per section, ordered Warm-up → Peak by
  energy (mean rank of loudness and onset rate, ±0.25 for the Intense/Relaxed tag). Tonal parts pick the least retuned loops
  first. 3–5 sections get names (Warm-up, Groove, [Lift,] Drive, Peak), otherwise `Level n`.
- **Breaks:** 5 per section, `[Bass, Synths, Music Beds]` kept (drums drop out). **FX:** key *k* of every section on track `FX k`.
- Needs `ffmpeg` (Rubber Band) for loops that must be retuned or re-tempoed; the rest are copied.

Licence: GarageBand's loops are licensed to owners of Apple devices (the user owns them). The `.pkg` files come from
`audiocontentdownload.apple.com`; nothing from Apple is stored in the repo.

### Finding the package for a style
Apple publishes a content index per app version at `https://audiocontentdownload.apple.com/lp10_ms3_content_2016/`:
`garageband1047.plist` (GarageBand 10.4.7, ~4 MB, verified) and `logicpro1050.plist` exist; other version numbers 404. It is a binary plist:
`Packages` maps package name → `DownloadName`, `DownloadSize` (bytes), `FileCheck` (a file inside, whose folder names the style) and
`ContainsAppleLoops`. The package URL is the same folder + `DownloadName`, e.g. `…/MAContent10_AssetPack_0315_AppleLoopsElectroHouse1.pkg`
(a `HEAD` request shows the size without downloading).
```
python -c "import plistlib,sys;[print(v['DownloadName'],v['DownloadSize']//2**20,'MB',v['FileCheck']) for v in plistlib.load(open(sys.argv[1],'rb'))['Packages'].values() if v.get('ContainsAppleLoops')]" garageband1047.plist
```
Orchestral material: `MAContent10_AssetPack_0329_AppleLoopsJamPackOrchestra` is only 39 loops (8 MB, mixed keys/tempos). The full orchestra
(2203 loops: violin, viola, cello, bass, harp, winds, brass, timpani, piano...) is `../lp10_ms3_content_2013/MAContent10_AppleLoopsLegacySymphony.pkg`
(655 MB; the plist `DownloadName` is a relative path into the 2013 folder; `FileCheck` can be a list). `tools/garageband_set.py` hard-codes the
electro-house roles/tempo/names, so an orchestra needs its roles remapped (`sets/classical/` was built by overriding `role`, `LOOP_TRACKS`,
`DRUM_PARTS`, `BREAK_KEEPS` from a driver script; a proper `--style` option is a tools change).

## Pipeline 2: song kit — `tools/kit_set.py`
```
python tools/kit_set.py sets/<kit>/kit.json
```
Writes `sets/<kit>/layout.json` next to `kit.json` and stages WAVs under `<STAGED>/<name>/`. Sections are the kit's own song
sections, not an energy ladder: loops of one song section share harmony.

**Source priority:** GarageBand / Apple Loops packages (pipeline 1) > files with embedded tempo/key > name-only kits. Embedded metadata
(`audio.read_loop_meta`): the WAV `acid` chunk (one-shot flag, root note, beats, tempo) and `smpl` (unity note, used when `acid` has no
root). It beats file-name guesses: embedded beats set a loop's length, embedded tempo stands in for a missing `tempo`, a one-shot flag makes a
one-shot. With root notes, loops are retuned (rendered offline) to the kit's most common root; |shift| > 5 leaves a loop out; loops without a
root note (drums) are untouched. Without metadata every file must already be in one key.

`kit.json` (see `sets/prog-rock-1/kit.json`):
| Field | Meaning |
|---|---|
| `name` | staging folder and Live sample folder name; use the folder name of `sets/<kit>` |
| `source` | folder of the unzipped kit |
| `tempo` | the kit's BPM (one per kit); may be omitted when the files carry it |
| `key` | label only, shown in `layout.json`/set map (default: the most common embedded root) |
| `section_pattern` | regex with **one group** applied to each WAV file name; the group is the section id (`-(\d+)\.wav$` → `03`) |
| `parts` | `{"<track name>": [subfolders of source], …}`: 1–6 tracks named as you like (not `Break`/`FX n`); order = B2…B7. Per set, chosen to represent the ensemble: cover rhythm/pulse, low end, harmony, melody, colour; merge similar instruments (an orchestra: Violins, Low Strings, Woodwinds, Brass, Percussion, Keys/Harp) |
| `drum_parts` | optional list of part names warped in Beats mode; default: parts whose loops carry no root note when any loop has metadata, else none |
| `break` | optional `{"folders": [...], "keep": [part names]}`; kept parts keep playing during the break |
| `fx` | optional `{"folders": [...]}`; hits are not sectioned, spread over `FX 1`–`FX 5` |

Numeric ids sort numerically and become `Section n`; non-numeric ids sort after, by name. Within a section a part's loops run
mellow → busy over the keys; more than 13 are thinned evenly, fewer leave keys empty (sections are not padded). Breaks: up to 5
per section. WAVs must be 44.1 kHz, 16/24-bit PCM. Loops are clipped to whole bars (≥ 4 beats); any loop more than 1 ms off its
bar length is rendered offline.

## `layout.json`
Top level: `tempo` (BPM, float), `key` (string, display), `rows_per_section` (13), `sections` (names, in order),
`parts` (1–6 part track names in button order, B2…B7; per set, in Set order), `drum_parts` (part names warped in Beats mode; the writer
uses this, not track names), `tracks` (`{track: [clip,…]}`), `left_out` (`{track: pool size − clips
used}`; informational). `tracks` keys: the `parts` (each with ≥ 1 clip), plus optional `Break` and `FX 1`…`FX 5` (only when the source has suitable material: no empty tracks).

Clip fields (`als_writer` reads those marked *):
| Field | Meaning |
|---|---|
| `row`* | Session row = `section × 13 + key index` (breaks: key index 0–4; FX: first row of the section) |
| `name`* | clip name and scene label source; breaks end with ` [Kept, Parts]` |
| `path`* | absolute staged WAV path containing `/samples/staged/` |
| `beats`* | clip length in beats |
| `audio_beats` | length of the sound itself in beats (one-shots keep this speed) |
| `priming`*, `frames`* | skip `priming` frames, then `frames` frames of audio; 0 for decoded, rendered and kit files |
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
A `.als` is gzip'd XML. The writer clones the template's `Prototype` audio track once per part (in `parts` order), then for
`Break` and each `FX n` that has clips, and removes the prototype: no empty tracks. It rebuilds scenes and clip slots (13 rows ×
sections; scenes named `S2 Groove · D3`), sets the tempo, and replaces the `Play` track's devices with
Pitch (`+ 12.adv`, `Manual` 0) → Wavetable "Bright SAW Lead" (paths from `settings.CORE_DEVICES`). Clip start/loop points, warp
markers, launch mode (loops: Global; FX: None), colour per section and warp mode (`drum_parts`: Beats; melodic and retuned/stretched:
Complex) are set from the layout.

`templates/base.als` holds `Play` (MIDI), one audio track `Prototype`, returns and master, plus one session clip as the clip
template. Make a new one from any working Set with a `Play` track and at least one audio clip in a session slot:
```
python tools/make_template.py "<working.als>" [templates/base.als]
```
It strips arrangement clips and all session clips except the first, and keeps only the audio track holding that clip, renamed
`Prototype`.

## Validation checklist
1. `layout.json`: every loop part has clips in every section you expect; each loop's `frames` ≈ `beats × 60 / tempo × 44100`
   (within 1 ms) and `shift` is 0; every `path` exists; breaks name kept parts that exist; one tempo, one key.
2. `python tools/viz_preview.py sets/<kit>/layout.json --section N --part N` and open the URL it prints: no empty key where you expected a loop (Ctrl+C to stop).
3. `.als`: scene count = sections × 13; clip count = clips in layout; no missing samples (command in
   [prompts/build-in-live.md](../prompts/build-in-live.md)).
4. In Live: open the Set (choose **Don't Save** if an older copy is open), restart Live if `LoopMix/` changed, press every key
   of one section, one break, one FX, an octave button; check the key map page.
