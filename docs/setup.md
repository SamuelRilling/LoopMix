# Setup (Windows, Live 11.0, Behringer UMX25)

Requirements: Python 3 with `numpy` and `pytest`; ffmpeg with the `rubberband` filter on `PATH`
(check: `ffmpeg -hide_banner -filters`, look for `rubberband`). The remote script itself runs on
Live's own Python 3.7 and needs nothing installed.

## 1. Machine paths — `tools/settings.py`
The only file with machine paths. Edit these before running any tool:

| Setting | Meaning |
|---|---|
| `REPO` | repo root (derived, don't edit) |
| `USER_LIBRARY` | Live's User Library folder; must end with `/` |
| `CORE_DEVICES` | `…/Resources/Core Library/Devices/` of the Live install; the writer reads the Pitch and Wavetable presets there |
| `REMOTE_SCRIPTS` | `…/Resources/MIDI Remote Scripts/` of the Live install |
| `STAGED` | `<repo>/samples/staged/`; the tools write the set's WAVs here; must end with `/` |
| `TEMPLATE` | `templates/base.als`, the Set the writer starts from |
| `LIVE_LOG` | Live's `Log.txt` (`%APPDATA%\Ableton\Live 11.0\Preferences\Log.txt`) |

## 2. Link the remote script
Live loads scripts from `settings.REMOTE_SCRIPTS`. Junction the repo's `LoopMix/` folder there (no copy to keep in sync):

```
mklink /J "<REMOTE_SCRIPTS>LoopMix" "<repo>\LoopMix"
```

## 3. Link the samples
Generated Sets reference clips as `Samples/LoopMix/<kit>/<track>/<file>.wav` inside the User Library. Junction
`settings.STAGED` there:

```
mklink /J "<USER_LIBRARY>Samples\LoopMix" "<repo>\samples\staged"
```

## 4. Live preferences
Live → Preferences → Link/Tempo/MIDI: Control Surface **LoopMix**, Input **UMX 25**, Output **None**.
Restart Live after any change to `LoopMix/` — scripts load only at startup.

## 5. UMX25 buttons
- B1–B8 send factory CCs and need no setup: B1 = 97, B2–B7 = 96, 66, 67, 64, 65, 7, B8 = 10.
  B1–B6 latch (127 on one press, 0 on the next); B7 and B8 send the same value every press.
- The two octave buttons need ASSIGN mode, each with its own controller number:
  1. Press ASSIGN on the UMX25.
  2. Press the **right** octave button, set controller **20**; confirm.
  3. Press the **left** octave button, set controller **21**; confirm.
  4. Leave ASSIGN mode.
  They latch too, so every message counts as one press. Right = `OCTAVE_UP_CC` (next section), left = `OCTAVE_DOWN_CC`.
- Different numbers? Change them in `LoopMix/config.py`; set `LOG_ALL_CCS = True` once to log every unassigned CC the keyboard sends.

## 6. Audio driver
Use **ASIO** (Preferences → Audio → Driver Type); ASIO4ALL works if the interface has no driver. With MME the measured
key-to-sound latency was about 85 ms.

## 7. Check
`python -m pytest -q tests` (all pass). Open a generated Set, then <http://127.0.0.1:9890> shows the key map; if it
doesn't, see [troubleshooting.md](troubleshooting.md).
