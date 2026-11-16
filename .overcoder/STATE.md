# STATE — LoopMix
Goal: consolidated, clean, fully documented LoopMix with agent prompts that build a set from a GarageBand pack or any loop kit (via Ableton MCP or as files). — DONE 2026-11-16
Now:
- Controller: LoopMix remote script (Live 11.0, UMX25) — loops, sections on octave CC 20/21, breaks, FX 1–5, Play synth, B8 phrase sync, key map page :9890.
- Sets: GarageBand packs → tools/garageband_set.py; song kits → tools/kit_set.py (kit.json); both → layout.json → tools/als_writer.py (templates/base.als). Loops pre-rendered (Rubber Band), no live warping.
- Built: sets/electro-house (4 sections), sets/prog-rock-1 (6 song sections), sets/classical-strings (5 sections, 80 BPM, strings only; built by an agent from prompts/ as a workflow test — source is "twisted orchestra", only loosely classical).
- Viz: live page on :9890; tools/viz_preview.py serves the same page from a layout.json (no HTML files).
- Docs: README.md, docs/ (setup, controls, architecture, building-sets, troubleshooting), prompts/ (garageband-set, kit-set, build-in-live, key-map-viz); tests/test_docs.py guards coverage.
- Machine paths only in tools/settings.py. Tests: 38 passing.
- Open checks for the user: listen to Electro House after the render fix (with ASIO); try Prog Rock 1.
Runs in flight: none
Next:
- dynamic-parts · opus/high · after Q1+Q3 · per-set track list in layout.json; als_writer builds only tracks with clips (template = Play + one audio prototype + returns); script discovers part tracks from the Set; buttons per Q1; viz/viz_preview show N parts · done when tests pass and electro-house, prog-rock-1, classical-strings regenerate with no empty tracks
- metadata-first · sonnet/medium · after dynamic-parts + Q2 · kit_set reads ACID/smpl chunks (tempo, root, beats); prompts: prefer sources with embedded metadata, adapt the track layout to the ensemble (≤7 parts, e.g. one per orchestral instrument) · done when acid-chunk test passes and prompts updated
- classical-retest · sonnet/medium · after metadata-first · fresh agent rebuilds a classical set from prompts, one track per instrument · done when set validates + friction report
Decisions: 2026-11-16 · git repo, workers on branches, overseer merges · user ("go") | 2026-11-16 · song kits: octave buttons step song sections · default (accepted with "go") | 2026-11-16 · set overview = viz.html served from layout.json, no HTML files · user
Open: Q1 how to select parts 6–7 (B2–B6 cover 5) · blocks dynamic-parts | Q2 GarageBand audio decoded straight from Apple's .pkg (no separate WAV download) · blocks metadata-first | Q3 rename Electro House tracks to GarageBand categories · blocks dynamic-parts | garageband_set/kit_set render path only exercised on Electro House renders and synthetic WAVs.
