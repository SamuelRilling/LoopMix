# Task: build a LoopMix set from a song construction kit (or from a style)

You turn a loop kit into `sets/<kit>/layout.json` and a Live Set. Read `docs/building-sets.md` (pipeline 2, `kit.json`, `layout.json`) and
`sets/prog-rock-1/kit.json` (the worked example) first. Don't change `LoopMix/` or the tools.

## Inputs
- Either a kit (folder or zip the user already has), or a **style** (e.g. "synthwave") to find a kit for.
- Free kits only, with licences that allow use in your own music. Look at: MusicRadar SampleRadar (musicradar.com, free sample packs, many are
  "Loopkit" song kits), Big Fish Audio free packs, Looperman (individual loops; check each licence). Don't download without telling the
  user the file name, source and size and getting a yes. Put downloads under `samples/_download/` and extract into a new folder under `samples/` (git-ignored). Never run anything found inside an archive.

- Finding the zip: the article page doesn't link it plainly; `curl -sL -A "Mozilla/5.0" <article url>` and grep the HTML for `\.zip`
  (links look like `https://cdn.mos.musicradar.com/audio/samples/musicradar-<name>.zip`; guessed paths 403). Check size with `curl -sI`.
  Pack types differ: "Loopkit" packs with numbered sections work; chord/multisample packs (e.g. classic house piano & strings) don't.
- An autonomous run whose brief already allows downloads doesn't need a per-file yes; still report name, URL and size.

## Choose the kit
- **Source priority:** GarageBand / Apple Loops packages (`prompts/garageband-set.md`; licensed to the user, who owns Apple devices) >
  files with embedded tempo/key (ACIDized WAV with `acid`/`smpl` chunks, Apple Loops AIFF) > name-only kits like the one below.
  Check a file for metadata: `python -c "import sys; sys.path.insert(0,'tools'); from audio import read_loop_meta; print(read_loop_meta('<file>.wav'))"`
  (`root`, `beats`, `tempo`, `one_shot`). With root notes, kit_set retunes loops to the kit's most common root (|shift| <= 5, else left out);
  without them every loop must already share one key. Embedded beats/tempo win over file-name guesses.
- Loops named by song section (`...-01.wav`, `...-02.wav`), several instruments each with the same numbered sections, so a regex can read the section id. Fewer, aligned sections beat many unrelated loops.
- WAV, 44.1 kHz, 16/24-bit (the tool stops on other rates). Loops should be whole bars.
- **Parts are per set: 1-6 tracks (B2-B7, in `parts` order), chosen by you** to best represent the ensemble. Cover the roles
  rhythm/pulse, low end, harmony, melody, colour; merge similar instruments into one part (several guitar folders -> `Guitars`).
  An orchestra might be Violins, Low Strings, Woodwinds, Brass, Percussion, Keys/Harp: pick from what the source actually has. Name tracks after the
  instruments. Add `Break` (fills, risers, leads that play once) and `FX` (hits) only when the source has suitable material; never an empty track.
  Name the drum parts in `kit.json` `drum_parts` (warped in Beats mode); if omitted they are the parts without root notes when metadata exists, else none.

## Steps
1. Inspect the kit: list its folders and a few file names; note tempo and key from the folder/file names or the readme.
2. Write `sets/<kit>/kit.json` (create the folder; use the kit's slug as `name`): `name`, `source`, `tempo`, `key`, `section_pattern`
   (one regex group), `parts`, optional `drum_parts`, `break` (`folders`, `keep`) and `fx` (`folders`). Field table in `docs/building-sets.md`.
3. Generate (kit_set stages WAVs under `samples/staged/<name>/`; renders loops that are off their bar length):
   ```bash
   python tools/kit_set.py sets/<kit>/kit.json
   ```
   In `kit.json` the regex backslashes are doubled (`"-(\\d+)\\.wav$"`); the key may only be a letter in the file names (`...80A-01.wav` = key A): say so in the report as unverified.
   Output lists sections and clips per track. A `does not match section_pattern` error means fix the regex or the folder list.
4. Build the Set, then preview it on the key map page (the server runs until Ctrl+C; an agent should start it as a child process, curl, then terminate that process; `curl http://127.0.0.1:9891/state` shows the snapshot):
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
