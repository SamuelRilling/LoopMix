# Task: work on the key map, or produce a static map of a set

Two things share this prompt: the **live key map page** (inside Live) and the **preview** of a set on that same page (`tools/viz_preview.py`, no Live needed).

## Preview a new set
```bash
python tools/viz_preview.py sets/<kit>/layout.json --port 9891 --section 0 --part 0 --mode loop
```
Serves the same `LoopMix/viz.html` through `LoopMix/viz.py`, but `/state` is built from `layout.json` instead of Live (`build_snapshot()`):
nothing plays, `is_playing` is false, bar 4. The keys show the selected part's 13 loops in the chosen section, its 5 breaks and 5 FX (labels
without the `[...]` suffix). `--section` and `--part` are 0-based (part order Drums, Bass, Part A, Part B, Part X); defaults: port 9891,
section 0, part 0, loop mode. It prints the URL and runs until Ctrl+C; to check it from a script, start it in the background,
`curl http://127.0.0.1:9891/state`, then stop it. Check both reference layouts (`sets/electro-house/layout.json`, `sets/prog-rock-1/layout.json`).
If you change `_snapshot()` in `loop_mix.py`, change `build_snapshot()` to match; unit test:
```bash
python -m pytest -q tests/test_viz_preview.py
```

## How the live page works
- `LoopMix/viz.py` starts a read-only HTTP server on `127.0.0.1:<config.VIZ_PORT>` (default 9890; `None` = off) in a daemon thread.
  `/` returns `LoopMix/viz.html`; `/state` returns the latest snapshot as JSON plus `age` (seconds since the snapshot).
- `LoopMix/loop_mix.py` builds the snapshot in `_snapshot()` on Live's main thread every 2nd `update_display` and assigns `Viz.state`.
  The server thread never calls Live's API.
- `viz.html` polls `/state`, and between snapshots animates the beat clock from `tempo` and `age`.

`/state` fields: `mode` (`loop`/`play`), `octave`, `section` (0-based), `sections` (names), `tempo`, `is_playing`, `song_time` (beats), `bar` (beats per bar),
`phrase` (sync on), `phrase_beats`, `pending_start` (beat or null), `rows` (rows per section), `parts` (list of `name`, `selected`, `playing` clip name,
`position`, `length`, `pending`), `keys` (23 entries: 13 loops of the selected part, 5 breaks, 5 FX; each `key` offset from the lowest C,
`kind` loop/break/fx, `label`, `playing`), `age`.

## Changing the live page
Edit `LoopMix/viz.html` (CSS tokens at the top: `--loop`, `--break`, `--fx`, …) for looks, `_snapshot()` for data. Keep it dependency-free.
Live loads the script only at startup: restart Live to see Python changes; `viz.html` is read on every request, so a browser refresh is
enough for HTML-only changes. Don't touch Live's API from the server thread. Keep `LocalServer.server_bind` (it avoids `getfqdn`, which fails
in Live's Python). While Live runs, `/state` can be opened in a browser.
`python -m pytest -q tests` must still pass (`logic.py` is the tested part).
