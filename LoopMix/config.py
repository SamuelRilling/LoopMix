"""Hardware and Set layout. Edit here; nothing else needs to change.

The script logs every MIDI message it receives to Ableton's Log.txt
(%APPDATA%\\Ableton\\Live 11.0\\Preferences\\Log.txt, search "LoopMix").
"""

# MIDI channel the UMX25 sends on (0 = channel 1).
MIDI_CHANNEL = 0

# UMX25 factory buttons (latching: 127 on one press, 0 on the next).
MODE_CC = 97                          # B1: Loop <-> Play
PART_CCS = (96, 66, 67, 64, 65, 7)    # B2..B7: select part 1..6 of the Set
BUTTONS_LATCH = True
# B7 (factory CC 7) sends 0 on every press, like B8: any message is a press.
SAME_VALUE_CCS = (7,)

# Octave buttons, each assigned its own CC in ASSIGN mode. They latch (127 / 0
# on alternate presses), so every message counts as one press.
# Loop mode: next / previous section. Play mode: Play octave up / down.
OCTAVE_UP_CC = 20      # right button
OCTAVE_DOWN_CC = 21    # left button

# B8 (factory CC 10, same value on every press): phrase sync on / off.
# On: loops launched by keys or section changes wait for the next phrase start
# (phrase = longest loop playing), so every loop shares the same downbeat.
PHRASE_CC = 10

# Lowest key of the UMX25 (C3).
BASE_NOTE = 48

# Log every CC the keyboard sends (to find button numbers). Set False after.
LOG_ALL_CCS = False

# Part tracks are not named here: they are the Set's audio tracks other than
# Break and FX 1..5, in Set order (first 6 -> B2..B7). Break/FX are optional.
PLAY_TRACK = "Play"      # needs Live's Pitch device for the octave buttons
BREAK_TRACK = "Break"
FX_TRACKS = ("FX 1", "FX 2", "FX 3", "FX 4", "FX 5")   # one per key, so FX overlap

# Session rows per section; sections = scenes // ROWS_PER_SECTION.
# Scene names "S2 Groove · D3" give the section its name.
ROWS_PER_SECTION = 13

# Key map page for a browser beside Live: http://127.0.0.1:9890  (None = off)
VIZ_PORT = 9890
