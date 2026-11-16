# LOG
2026-11-16 · bootstrap · opus · STATE/LOG created; plan for cleanup, kit importer, docs+prompts · — · ctx n/a
2026-11-16 · cleanup · sonnet · repo template, tools/settings.py, tools/audio.py, rank_energy removed; 26 tests, regen 300 clips/0 missing · merged 4c189f9 · ctx n/a
2026-11-16 · kit-importer · sonnet · tools/kit_set.py + prog-rock-1 kit.json/layout; 32 tests; render path untested on real files (none needed) · merged da4b67a · ctx n/a
2026-11-16 · docs-prompts · sonnet · README + docs/ + 4 agent prompts + tools/viz_preview.py (user: no HTML files) + docs coverage test; 38 tests · merged (see git log) · ctx n/a
## Tips
- Scope changes mid-run: SendMessage to the worker queues until its turn ends; verify the change landed in the report.
- Runs must start from a user-started turn: the app refuses cwd-elsewhere starts from wake turns.
- Live 11.0 can't import audio via API: sets are generated as .als from a working template (tools/als_writer.py).
- Validate generated sets by parsing the .als (tracks, slot counts, duplicate ids, missing samples) before the user opens them.
- Script changes load only on Live restart; regenerated sets are lost if the user saves the open copy.
