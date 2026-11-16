# Task: build a LoopMix set from GarageBand / Apple Loops packages

You write `sets/<kit>/pack.json`, build `sets/<kit>/layout.json` from it, then a Live Set. Read `docs/building-sets.md`
(pipeline 1, the `pack.json` fields and the `layout.json` schema) first. Don't change `LoopMix/` or the tools; if a tool can't do
what the set needs, stop and report what's missing.

## Inputs (ask the user if any is missing)
- A style, a package name, or a link. The user owns Apple devices, so GarageBand's loops are licensed to them.
- Apple's content packages (`.pkg`) hold both the audio and the loop tags. If they aren't under `samples/_apple/`, find them in
  Apple's content index ("Finding the package for a style" in `docs/building-sets.md`) and download only those from
  `audiocontentdownload.apple.com` into `samples/_apple/`. Report each package's name, URL and size.

## Steps
1. ffmpeg must have the `rubberband` filter:
   ```bash
   ffmpeg -hide_banner -filters
   ```
   (no `rubberband` → stop and tell the user to install an ffmpeg build with librubberband).
2. Look at what the packages hold (categories, subcategories, tempos, scales) with the `read_tags` one-liner in `docs/building-sets.md`.
3. Choose the parts — **at most 6** (buttons B2–B7), in the order a player would want them. Pick the instruments that best represent
   the style from what the packages actually have: cover the roles (pulse/rhythm, low end, harmony, melody, colour); merge similar
   instruments into one part (e.g. Viola + Cello + Double Bass → `Low Strings`); name parts by instrument, never `Part A`. A part with
   too few loops for 13 per section is better as FX (orchestra: timpani) or merged.
   Breaks: GarageBand's *Fill* loops (one-off phrases) or transitions, with `keep` = the parts that keep playing. FX: hits, crashes,
   timpani, bells. Leave `break`/`fx` out when the packages have nothing suitable (no empty tracks).
4. Write `sets/<kit>/pack.json` (start from `sets/classical/pack.json` or `sets/electro-house/pack.json`). Leave `tempo`, `scale` and `key`
   on `"auto"` unless the style needs a fixed value; `tempo_window` 0.1–0.2 (bigger = more loops, more stretching).
5. Build the layout (decodes only the loops the rules match; minutes for a big package — run it in the background with a ~20 min timeout):
   ```bash
   python tools/garageband_set.py sets/<kit>/pack.json
   ```
   It prints key, tempo, section names and clips per track. Aim for **3 or more sections**. Fewer, or a "too few loops" stop: widen a
   rule or `tempo_window`, merge or drop the smallest part, and rebuild. Never pad.
6. Preview on the key map page (no Live). The server runs until stopped: start it in the background, curl `/state`, stop that process:
   ```bash
   python tools/viz_preview.py sets/<kit>/layout.json --port 9891
   ```
7. Build the Set (`.als` is git-ignored), then validate and hand over with `prompts/build-in-live.md`:
   ```bash
   python tools/als_writer.py templates/base.als sets/<kit>/layout.json "sets/<kit>/<Name>.als"
   ```
   Never overwrite another set's `.als`. If a Set with that name is open in Live, the user closes it with *Don't Save* first.
8. Tests still pass, then commit `pack.json` and `layout.json` (never samples or `.als`):
   ```bash
   python -m pytest -q tests
   ```

## Report
Packages used (name, URL, size), the parts you chose and why, key, tempo, section names, clips per track, `left_out`, how many clips
were rendered (`rendered_from` in the layout), validation results, and the user steps from `prompts/build-in-live.md`.
