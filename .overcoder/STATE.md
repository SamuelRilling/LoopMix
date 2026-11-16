# STATE — LoopMix
Goal: classical set finished; sets buildable by an agent from one prompt (prompts/make-a-set.md); repo pushed. — DONE 2026-11-16
Now:
- Controller: LoopMix remote script (Live 11.0, UMX25) — per-set parts on B2–B7 (≤6), loops on 13 white keys, breaks/FX on black keys, sections on octave CC 20/21, B1 Loop/Play, B8 phrase sync, key map page :9890.
- Sets: GarageBand → tools/garageband_set.py + sets/<kit>/pack.json (rules on Apple tags; tempo/scale auto = most full sections; decodes only matched loops); song kits → tools/kit_set.py + kit.json (ACID/smpl aware); both → layout.json → tools/als_writer.py (templates/base.als). Every retune/re-tempo rendered offline; Live plays clips unshifted.
- Built: classical (Strings, Low Strings, Woodwinds, Brass, Harp; timpani/cymbals/bells FX; Fill phrases as breaks; D major, 100 BPM, 3 sections, 225 clips, 0 missing, 0 live processing); electro-house (played version, 504-loop export; pack.json rebuild = 5 sections); prog-rock-1; classical-strings (first agent test).
- Docs: README, docs/, prompts/ (make-a-set → garageband-set | kit-set → build-in-live; key-map-viz). Tests: 56.
- User checks open: play Classical in Live (ASIO), Electro House after render fix.
Runs in flight: none
Next: none.
Decisions: workers on branches, overseer merges · user | song kits step song sections · default | no HTML files; viz preview = viz.html from layout · user | ≤6 parts on B2–B7, agent picks instruments · user | GarageBand audio from Apple .pkg · user | EH tracks = Beats, Bass, Synths, Music Beds, Toppers · user | 2026-11-16 remaining work done by the overseer itself, no more sessions · user | GitHub repo private (default; user asked for a push)
Open: old decode caches samples/decoded (flat), decoded_orch, decoded_symph ≈ 4.8 GB unused since per-package cache (delete on user's yes).
