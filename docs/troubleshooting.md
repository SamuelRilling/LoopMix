# Troubleshooting

| Symptom | Cause / fix |
|---|---|
| LoopMix not in the Control Surface list | The `LoopMix` junction under `settings.REMOTE_SCRIPTS` is missing or wrong ([setup.md](setup.md)); restart Live. |
| Changed `LoopMix/` or `config.py`, nothing changed | Live loads remote scripts only at startup: restart Live. |
| Keys do nothing | Loop/Play mode wrong (B1; key map header shows LOOP or PLAY), Input not UMX 25, or no track named like `config.PART_TRACKS`. Live's status bar says "no track named …". |
| Regenerated a Set, old content appears | The Set was open: Live asked to save on closing and overwrote the new file. Close it with **Don't Save**, regenerate, then open. |
| Octave buttons do nothing | They must send their own CC in ASSIGN mode (20 / 21, [setup.md](setup.md)). They latch (127, 0, 127 …); the script counts every message as a press regardless of `BUTTONS_LATCH`. Set `LOG_ALL_CCS = True`, restart Live, press them and read the CC numbers in the log. |
| Wrong clip launches | `tools/replay_log.py` (below). Check the section: octave buttons change it, not the part. |
| Clicks, stutter, "warped" sound | Clip warping. Generated clips should be unwarped 1:1: check `shift` 0 and `frames` ≈ `beats` in `layout.json`; re-render with `kit_set.py` / `garageband_set.py`. |
| Late response | Audio driver: use ASIO (MME measured 85 ms). Lower the buffer size in Live's audio preferences. |
| Key map page empty / not loading | Log shows `LoopMix key map disabled` (port in use: change `VIZ_PORT`) or `VIZ_PORT = None`. Open <http://127.0.0.1:9890> (127.0.0.1, not `localhost`). |
| Octave in Play mode: "add Live's Pitch device" | The `Play` track needs Live's Pitch MIDI effect; the generated Set has it. |

## Live's log
`%APPDATA%\Ableton\Live 11.0\Preferences\Log.txt` (= `settings.LIVE_LOG`). Search `LoopMix`. Lines: `LoopMix loaded (Loop mode)`,
`LoopMix CC 20 = 127`, `LoopMix note 50 vel 100`, `LoopMix unassigned CC …` (with `LOG_ALL_CCS = True`), and tracebacks
(`LoopMix error on …`, `break error`, `phrase error`, `viz error`). Errors never crash Live; the action is skipped.

## `tools/replay_log.py`
```
python tools/replay_log.py [sets/<kit>/layout.json]
```
Replays the last Live session in `Log.txt` (from the last `Started: Live` line) through `logic.py` and prints, per press: time,
section, action, row, clip name, beats, recorded BPM and shift. Use it to see which clip a press launched and whether a clip was
off-tempo or retuned. Default layout: `sets/electro-house/layout.json`.
