# Task: build a LoopMix set

Give this file to an agent together with one line: a **style** ("classical", "80s synthwave"), a **pack** (an Apple package name, a kit
folder or zip) or a **link**. The agent ends with a playable Live Set, a key map preview and a short report. Work from the repo root.

## 1. Pick the source (in this order — sources with embedded metadata first)
1. **GarageBand / Apple Loops packages.** The user owns Apple devices, so these are licensed. They carry GarageBand's own tags
   (instrument category, key, scale, tempo, *Fill* phrases), so the set is organised the way GarageBand organises it.
   Search Apple's content index for the style ("Finding the package for a style" in `docs/building-sets.md`). If a package fits,
   follow **`prompts/garageband-set.md`**.
2. **Loop kits whose WAVs embed tempo and key** (ACIDized `acid`/`smpl` chunks, Apple Loops AIFF).
3. **Song kits with numbered sections in the file names** (e.g. MusicRadar "Loopkit" packs).
   For 2 and 3 follow **`prompts/kit-set.md`**.

A link or a pack from the user overrides the order: use it, and say in the report which source type it is.

## 2. Shape the set to the music
- **1–6 parts** (buttons B2–B7). Choose the instruments that best represent the style from what the source really has: cover the
  roles (pulse/rhythm, low end, harmony, melody, colour), merge similar instruments into one part, name parts by instrument.
  An orchestra is not a band: e.g. Strings, Low Strings, Woodwinds, Brass, Harp, with timpani as FX — not Drums/Bass/Part A.
- Breaks and FX only when the source has suitable material; never an empty track.
- Aim for **3+ full sections** of 13 loops per part; adjust the parts or the tempo window rather than accept 1 section.

## 3. Build, check, hand over
The chosen prompt covers building the layout, the key map preview (`tools/viz_preview.py`) and the `.als`
(`tools/als_writer.py`). Then follow **`prompts/build-in-live.md`** to validate the Set and give the user their steps.
Commit `pack.json`/`kit.json` and `layout.json` (never samples or `.als`) after `python -m pytest -q tests` passes.

## Rules
- Don't change `LoopMix/` or `tools/`; if the tools can't express the set, stop and report what's missing.
- Downloads: only free/licensed sources; report each file's name, URL and size. Never run anything found inside an archive.
- Never overwrite another set's files.

## Report
Source and why (against the order above), the parts you chose and why, key, tempo, sections, clips per track, validation results,
anything you couldn't verify (you can't hear the result), and the user steps.
