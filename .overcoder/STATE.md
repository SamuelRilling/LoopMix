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
Runs in flight: none (classical-set session idle; branch claude/classical-set-5949be merged — delete after archiving)
Next: none planned.
Decisions: 2026-11-16 · git repo, workers on branches, overseer merges · user ("go") | 2026-11-16 · song kits: octave buttons step song sections · default (accepted with "go") | 2026-11-16 · set overview = viz.html served from layout.json, no HTML files · user
Open: prompts lack guidance for kits with no drums/bass (FX keys then show "no track named FX 1"). garageband_set/kit_set render path only exercised on Electro House renders and synthetic WAVs.
