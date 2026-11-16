"""Machine-specific paths: the one place to edit when setting LoopMix up on another PC."""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

USER_LIBRARY = "D:/Documentos/Ableton/User Library/"                      # must end with "/"
CORE_DEVICES = "D:/Software/Ableton/Resources/Core Library/Devices/"      # must end with "/"
REMOTE_SCRIPTS = "D:/Software/Ableton/Resources/MIDI Remote Scripts/"     # LoopMix/ is linked in here
STAGED = "D:/Coding Projects/LoopMix/samples/staged/"                  # User Library links it as Samples/LoopMix; must end with "/"
TEMPLATE = REPO / "templates" / "base.als"
LIVE_LOG = Path(os.environ.get("APPDATA", "")) / "Ableton" / "Live 11.0" / "Preferences" / "Log.txt"
