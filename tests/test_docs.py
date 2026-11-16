"""Docs coverage: every tool, setting and control is named somewhere in README.md, docs/ or prompts/."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = "\n".join(p.read_text(encoding="utf-8") for p in [ROOT / "README.md", *(ROOT / "docs").glob("*.md"),
                                                         *(ROOT / "prompts").glob("*.md")])
CONTROLS = ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "Octave", "White keys", "black keys", "Top C", "Bottom C",
            "CC 20", "CC 21", "Loop mode", "Play mode"]
PROMPTS = ["make-a-set.md", "garageband-set.md", "kit-set.md", "build-in-live.md", "key-map-viz.md"]
DOC_FILES = ["setup.md", "controls.md", "architecture.md", "building-sets.md", "troubleshooting.md"]


def settings_names(path):
    return re.findall(r"^([A-Z][A-Z_]+)\s*=", (ROOT / path).read_text(encoding="utf-8"), re.M)


def test_every_source_file_is_documented():
    files = [p.name for d in ("tools", "LoopMix") for p in (ROOT / d).iterdir() if p.suffix in (".py", ".html")]
    assert [f for f in files if f not in DOCS] == []


def test_every_setting_is_documented():
    names = settings_names("LoopMix/config.py") + settings_names("tools/settings.py")
    assert len(names) >= 20
    assert [n for n in names if n not in DOCS] == []


def test_every_control_is_documented():
    assert [c for c in CONTROLS if c.lower() not in DOCS.lower()] == []


def test_docs_and_prompts_exist():
    assert [f for f in DOC_FILES if not (ROOT / "docs" / f).exists()] == []
    assert [f for f in PROMPTS if not (ROOT / "prompts" / f).exists()] == []


def test_prompt_commands_name_existing_scripts():
    for f in PROMPTS:
        text = (ROOT / "prompts" / f).read_text(encoding="utf-8")
        for script in re.findall(r"python (tools/\w+\.py)", text):
            assert (ROOT / script).exists(), (f, script)
