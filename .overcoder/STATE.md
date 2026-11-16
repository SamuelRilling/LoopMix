# STATE — LoopMix
Goal: per-set track layouts (≤6 parts, agent picks instruments), no empty tracks, metadata-first sources, verified by an agent re-test of a classical set.
Now:
- Controller: LoopMix remote script (Live 11.0, UMX25) — loops, sections on octave CC 20/21, breaks, FX 1–5, Play synth, B8 phrase sync, key map page :9890.
- Sets: GarageBand packs → tools/garageband_set.py; song kits → tools/kit_set.py (kit.json); both → layout.json → tools/als_writer.py (templates/base.als). Loops pre-rendered (Rubber Band), no live warping.
- Built: sets/electro-house (4 sections), sets/prog-rock-1 (6 song sections), sets/classical-strings (agent workflow test; only loosely classical; to be replaced by classical-retest).
- Viz: live page on :9890; tools/viz_preview.py serves the same page from a layout.json (no HTML files).
- Docs: README.md, docs/, prompts/ (garageband-set, kit-set, build-in-live, key-map-viz); tests/test_docs.py guards coverage. Machine paths only in tools/settings.py. Tests: 38.
- Open checks for the user: listen to Electro House after the render fix (with ASIO); try Prog Rock 1.
- Parts: per-set (layout "parts", ≤6, B2–B7), Prototype template, no empty tracks; EH = Beats, Bass, Synths, Music Beds, Toppers; prog-rock = Drums, Bass, Guitars, Organ, Rhodes. Tests: 41.
- Metadata-first: GarageBand sets from Apple .pkg alone (ffmpeg decodes .caf, already drops priming); kit_set reads ACID/smpl; layout drum_parts drives warp; prompts rank metadata sources. Tests: 51. Full EH packages = 971 loops (user's WAVs were a 504 subset) → a pkg rebuild gives 5 sections; committed EH layout kept as played.
- User's Desktop WAV folder + zip copies vanished between ~15:18 and the metadata run; no LoopMix session deleted them (transcript search). Staged copies keep EH playable.
Runs in flight: none | (worktrees .claude/worktrees/dynamic-parts-749f36 + branch claude/dynamic-parts-749f36 merged; remove after archiving its session)
Next:
- classical-retest · sonnet/medium · after metadata-first · fresh agent rebuilds a classical set from prompts, one track per chosen instrument · done when set validates + friction report
Decisions: 2026-11-16 · git repo, workers on branches, overseer merges · user | song kits: octave buttons step song sections · default | set overview = viz.html served from layout.json, no HTML files · user | max 6 parts on B2–B7 (B7 = CC 7), agent chooses instruments · user | GarageBand audio from Apple .pkg · user | Electro House tracks = Beats, Bass, Synths, Music Beds, Toppers · user
Open: render path only exercised on Electro House renders and synthetic WAVs.
