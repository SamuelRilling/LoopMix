# Task: work on the key map, or produce a static map of a set

Two things share this prompt: the **live key map page** (inside Live) and the **static set map** (`tools/set_map.py`, no Live needed).

## Static set map for a new set
```bash
python tools/set_map.py sets/<kit>/layout.json [out.html]
```
Writes one self-contained HTML page (default `sets/<kit>/set-map.html`, git-ignored): tempo and key, one tab per section, and per tab a
table of the 13 white keys (D3 … B4) × parts with the loop name in each cell, plus the 5 breaks (C#3 D#3 F#3 G#3 A#3) and 5 FX
(C#4 D#4 F#4 G#4 A#4) of that section. Colours are viz.html's (loop teal, break amber, FX pink). The page needs no network. To change it,
edit `tools/set_map.py` (`CSS`, `section_html`) and run the test:
```bash
python -m pytest -q tests/test_set_map.py
```
Check on both reference layouts (`sets/electro-house/layout.json`, `sets/prog-rock-1/layout.json`); open the HTML and confirm every
section tab shows loops. Report the output path.

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
