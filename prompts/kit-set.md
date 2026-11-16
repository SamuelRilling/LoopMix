# Task: build a LoopMix set from a song construction kit (or from a style)

You turn a loop kit into `sets/<kit>/layout.json` and a Live Set. Read `docs/building-sets.md` (pipeline 2, `kit.json`, `layout.json`) and
`sets/prog-rock-1/kit.json` (the worked example) first. Don't change `LoopMix/` or the tools.

## Inputs
- Either a kit (folder or zip the user already has), or a **style** (e.g. "synthwave") to find a kit for.
- Free kits only, with licences that allow use in your own music. Look at: MusicRadar SampleRadar (musicradar.com, free sample packs, many are
  "Loopkit" song kits), Big Fish Audio free packs, Looperman (individual loops; check each licence). Don't download without telling the
  user the file name, source and size and getting a yes. Put downloads under `samples/_download/` and extract into a new folder under `samples/` (git-ignored). Never run anything found inside an archive.

## Choose the kit
- **One tempo and one key for the whole kit** (kit_set doesn't retune; all loops must already fit).
- Loops named by song section (`...-01.wav`, `...-02.wav`), several instruments each with the same numbered sections, so a regex can read the section id. Fewer, aligned sections beat many unrelated loops.
- WAV, 44.1 kHz, 16/24-bit (the tool stops on other rates). Loops should be whole bars.
- Instruments to parts: Drums, Bass, Part A, Part B, Part X (any may be missing). Optional break folder (fills, risers, leads that play once) and
  FX folder (hits).

## Steps
1. Inspect the kit: list its folders and a few file names; note tempo and key from the folder/file names or the readme.
2. Write `sets/<kit>/kit.json` (create the folder; use the kit's slug as `name`): `name`, `source`, `tempo`, `key`, `section_pattern`
   (one regex group), `parts`, optional `break` (`folders`, `keep`) and `fx` (`folders`). Field table in `docs/building-sets.md`.
3. Generate (kit_set stages WAVs under `samples/staged/<name>/`; renders loops that are off their bar length):
   ```bash
   python tools/kit_set.py sets/<kit>/kit.json
   ```
   Output lists sections and clips per track. A `does not match section_pattern` error means fix the regex or the folder list.
4. Build the Set, then preview it on the key map page (the server runs until Ctrl+C; `curl http://127.0.0.1:9891/state` shows the snapshot):
   ```bash
   python tools/als_writer.py templates/base.als sets/<kit>/layout.json "sets/<kit>/<Kit Name>.als"
   ```
   ```bash
   python tools/viz_preview.py sets/<kit>/layout.json --port 9891
   ```
   Never overwrite an existing `.als` (e.g. `Electro House.als`, `Prog Rock 1.als`) unless the user says so.
5. Validate and open: `prompts/build-in-live.md`.
6. ```bash
   python -m pytest -q tests
   ```

## Report
Kit source and licence, tempo, key, sections, clips per track and `left_out`, parts missing, rendered loops, validation result, the user steps.
