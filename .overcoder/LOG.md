# LOG
2026-11-16 · bootstrap · opus · STATE/LOG created; plan for cleanup, kit importer, docs+prompts · — · ctx n/a
## Tips
- Live 11.0 can't import audio via API: sets are generated as .als from a working template (tools/als_writer.py).
- Validate generated sets by parsing the .als (tracks, slot counts, duplicate ids, missing samples) before the user opens them.
- Script changes load only on Live restart; regenerated sets are lost if the user saves the open copy.
