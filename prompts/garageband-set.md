# Task: build a LoopMix set from a GarageBand loop pack

You are building `sets/electro-house/layout.json` (and staged WAVs) from a GarageBand pack, then a Live Set. Read `docs/building-sets.md`
(pipeline 1 and the `layout.json` schema) first. Don't change `LoopMix/` or the tools.

## Inputs you need (ask the user if any is missing)
- Apple's content packages (`.pkg`) for the style: they hold both the audio (`.caf`) and the loop tags, so nothing else is needed.
  If missing, find the packages in Apple's content index (see "Finding the package for a style" in `docs/building-sets.md`) and download only those from
  `audiocontentdownload.apple.com` (the user owns Apple devices, so GarageBand's loops are licensed to them). Report package name, URL and size.
- `tools/settings.py` already points at this machine's Live folders and `samples/staged/`; if a path is wrong, ask.

## Steps
1. Check the tools. ffmpeg must have the `rubberband` filter:
   ```bash
   ffmpeg -hide_banner -filters
   ```
   (look for `rubberband`; if absent, stop and tell the user to install an ffmpeg build with librubberband).
2. Generate the layout and stage the audio (minutes for a full pack; run it in the background with a timeout, e.g. 20 min):
   ```bash
   python tools/garageband_set.py <pkg> [<pkg> ...]
   ```
   The `.caf` loops are decoded once to `samples/decoded/` (ffmpeg; Apple's AAC padding is already removed, so clips start on the beat).
   Output goes to `sets/electro-house/layout.json` and `samples/staged/Electro House/` (`--out` / `--staged` redirect them).
   The set has 1–6 parts (B2–B7, in layout order); `Break`/`FX` exist only when the pack has suitable loops. It prints key, sections and clips per track.
   Fewer than 3 sections, or a part with 0 clips, means the pack is too small: report it, don't pad.
3. Preview the set on the key map page (no Live; foreground server, stop with Ctrl+C; start it in the background and curl `/state`):
   ```bash
   python tools/viz_preview.py sets/electro-house/layout.json --port 9891
   ```
   Every section needs 13 loops per part; use `--section N --part N` to look for empty keys.
4. Build the Set (next to the layout; `.als` is git-ignored):
   ```bash
   python tools/als_writer.py templates/base.als sets/electro-house/layout.json "sets/electro-house/Electro House.als"
   ```
   **If a Set by that name already exists and the user didn't ask to replace it, write to another name.** If it is open in Live it must
   be closed with *Don't Save* before regenerating.
5. Validate and open in Live: follow `prompts/build-in-live.md` (Live 11 path).
6. Tests still pass:
   ```bash
   python -m pytest -q tests
   ```

## Report
Key, tempo (128), section names, clips per track, `left_out` counts, which loops were retuned/rendered (`rendered_from` in the layout),
validation results, and the user steps (open the Set, restart Live only if `LoopMix/` changed, check the key map page).
