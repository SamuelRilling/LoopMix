# LoopMix — UMX25 loop player for Ableton Live 11

Turns a Behringer UMX25 into a GarageBand/Roland-style loop player. One kit per Live Set:
B2–B7 select up to 6 parts (each set has its own part tracks, no empty tracks),
13 white keys launch loops of the selected part, black keys fire breaks and FX, the octave
buttons step through the kit's sections. Loops are pre-rendered to one tempo and key, so
Live never warps anything while you play.

Two halves:
- `LoopMix/` — the Live remote script (keys, buttons, key map page on port 9890).
- `tools/` — offline tools that turn a GarageBand pack or a song kit into `sets/<kit>/layout.json`, then into a Live Set (`.als`).

## Quick start
1. Install: [docs/setup.md](docs/setup.md) (edit `tools/settings.py`, link `LoopMix/` into Live, link the sample folder, assign the octave buttons).
2. Build a set — either ask an agent: give it [prompts/make-a-set.md](prompts/make-a-set.md) plus a style, pack or link
   ("make a set that sounds like classical music"); or run the tools ([docs/building-sets.md](docs/building-sets.md)):
   ```
   python tools/garageband_set.py sets/classical/pack.json          # GarageBand packages -> layout.json
   python tools/als_writer.py templates/base.als sets/classical/layout.json "sets/classical/Classical.als"
   python tools/viz_preview.py sets/classical/layout.json           # key map preview on :9891, no Live
   ```
   Song kits use `python tools/kit_set.py sets/<kit>/kit.json` instead of the first line.
3. Open the `.als` in Live, press B1 until the key map page (<http://127.0.0.1:9890>) says LOOP, play.

## Docs
| | |
|---|---|
| [docs/setup.md](docs/setup.md) | Live preferences, links, UMX25 ASSIGN steps, audio driver |
| [docs/controls.md](docs/controls.md) | every button and key, both modes, `LoopMix/config.py` settings |
| [docs/architecture.md](docs/architecture.md) | remote script, `logic.py`, timing, key map server |
| [docs/building-sets.md](docs/building-sets.md) | both pipelines, `layout.json` schema, offline rendering, `.als` writer, checklist |
| [docs/troubleshooting.md](docs/troubleshooting.md) | log file, replay, restarts, glitches, latency |
| [prompts/](prompts) | for an agent: start with `make-a-set.md`; it routes to `garageband-set.md` or `kit-set.md`, then `build-in-live.md`; `key-map-viz.md` for the page |

## Repo
```
LoopMix/    remote script: config.py (edit), logic.py (pure, tested), loop_mix.py (Live glue), viz.py + viz.html (key map)
tools/      settings.py (machine paths), apple_loops.py, garageband_set.py, kit_set.py, render_loops.py, audio.py,
            als_writer.py, make_template.py, viz_preview.py, replay_log.py
templates/  base.als  (Play + one Prototype audio track the writer clones, returns, master)
sets/       <kit>/layout.json (+ pack.json for GarageBand sets, kit.json for song kits); *.als are generated and git-ignored
            classical (orchestra, GarageBand Symphony), electro-house, prog-rock-1, classical-strings (first agent test)
samples/    audio (git-ignored); samples/staged is linked into Live's User Library
tests/      python -m pytest -q tests
```
