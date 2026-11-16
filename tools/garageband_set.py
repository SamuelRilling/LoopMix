"""Arrange GarageBand loops into a LoopMix layout, as described by a set's pack.json.

Everything comes from Apple's own content packages: the tags GarageBand's loop
browser uses (category, subcategory, key, scale, beats, descriptors) and the audio
(.caf, decoded with ffmpeg only for the loops a set can use).

pack.json (one per set, committed as sets/<kit>/pack.json):
{
 "name": "Classical",                              set name; staged folder
 "packages": ["samples/_apple/<pkg>.pkg"],         repo-relative or absolute
 "parts": {"Strings": [<rule>, ...], ...},         1-6 tracks; order = buttons B2..B7
 "drum_parts": ["Beats"],                           parts kept in Beats warp, never retuned
 "break": {"match": [<rule>], "keep": ["Strings"]}, optional: plays once, other parts pause
 "fx": {"match": [<rule>]},                         optional: instant one-shots on top
 "tempo": "auto" | 100,                             auto = most common native tempo of the parts
 "tempo_window": 0.1,                               leave out loops more than 10 % off that tempo
 "scale": "auto" | "minor" | "major",              GarageBand hides loops of the other scale
 "key": "auto" | "C",                               auto = most common root; loops retuned to it
 "max_shift": 5,                                    leave out loops needing a bigger retune
 "sections": ["Prelude", "Theme", ...]              optional names; the count comes from the pools
}
<rule> = {"category": ..., "subcategory": ..., "descriptors": [...], "not_descriptors": [...],
          "kick": true|false, "name": [...]}: every given field must match; category and
subcategory take a value, a list, or null (= untagged); "name" = substrings of the loop name;
"kick" splits drum loops by sound (GarageBand files beats and toppers alike).
A loop goes to the first part whose rules match, else Break, else FX. Parts skip loops tagged
Arrhythmic or Fill unless a rule asks for those descriptors.

Every section is full (13 loops per part); the smallest part sets the number of sections.

Usage:  python tools/garageband_set.py sets/<kit>/pack.json [--staged <dir>]
Output: sets/<kit>/layout.json + <settings.STAGED>/<name>/<track>/*.wav
"""
import argparse
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

import settings
from apple_loops import decode_packages, read_tags
from audio import features, rank, read_mono, spread
from render_loops import render

ROOT = Path(__file__).resolve().parent.parent
DECODED = Path(settings.STAGED).parent / "decoded"   # decoded .caf loops, one folder per package
RATE = 44100
ROWS = 13                     # white keys per section
BREAKS = FX = 5               # black keys per octave
FX_TRACKS = tuple("FX %d" % (i + 1) for i in range(FX))   # one track per key: FX overlap
KICK_RATIO = 0.35             # share of energy under 120 Hz that marks a full beat
SKIPPED_IN_PARTS = ("Arrhythmic", "Fill")
DEFAULTS = {"tempo": "auto", "tempo_window": 0.1, "scale": "auto", "key": "auto", "max_shift": 5,
            "drum_parts": [], "sections": []}
SECTION_NAMES = {
    3: ("Warm-up", "Groove", "Peak"),
    4: ("Warm-up", "Groove", "Drive", "Peak"),
    5: ("Warm-up", "Groove", "Lift", "Drive", "Peak"),
}
NOTES = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6,
         "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


# --- rules -------------------------------------------------------------------

def family(name: str) -> str:
    return re.sub(r"\s*\d+$", "", name)


def with_sibling_tags(tags: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    """Untagged loops take the tags of a numbered sibling ('Riser 02' from 'Riser 01')."""
    by_family = {}
    for n, t in tags.items():
        if t.get("category"):
            by_family.setdefault(family(n), t)
    return {n: t if t.get("category") else dict(by_family.get(family(n), {}), **t) for n, t in tags.items()}


def _one_of(value, wanted) -> bool:
    return value in wanted if isinstance(wanted, list) else value == wanted


def matches(rule: dict, name: str, t: Dict[str, str]) -> bool:
    """Every field the rule gives must match (except 'kick', which needs the audio)."""
    desc = set(filter(None, t.get("descriptors", "").split(",")))
    return all((
        "category" not in rule or _one_of(t.get("category"), rule["category"]),
        "subcategory" not in rule or _one_of(t.get("subcategory"), rule["subcategory"]),
        set(rule.get("descriptors", [])) <= desc,
        not set(rule.get("not_descriptors", [])) & desc,
        not rule.get("name") or any(s.lower() in name.lower() for s in rule["name"]),
    ))


def options(name: str, t: Dict[str, str], pack: dict) -> List[tuple]:
    """Every (role, kick rule or None) whose rules match, in pack order: parts, then break, fx.
    The loop takes the first one; a kick rule is settled once the audio is decoded."""
    desc = set(filter(None, t.get("descriptors", "").split(",")))
    found = []
    for part, rules in pack["parts"].items():
        for rule in rules:
            if desc & set(SKIPPED_IN_PARTS) - set(rule.get("descriptors", [])):
                continue
            if matches(rule, name, t):
                found.append((part, rule.get("kick")))
    for role in ("break", "fx"):
        found += [(role, r.get("kick")) for r in pack.get(role, {}).get("match", []) if matches(r, name, t)]
    return found


def assign(name: str, t: Dict[str, str], pack: dict) -> Optional[tuple]:
    """The first matching (role, kick rule), before any audio is known."""
    found = options(name, t, pack)
    return found[0] if found else None


def native_tempo(t: Dict[str, str]) -> Optional[float]:
    if t.get("beat count") and t.get("valid frames"):
        return float(t["beat count"]) / (int(t["valid frames"]) / RATE) * 60
    return None


def shift_to(root: str, target: int) -> int:
    return (target - NOTES[root] + 6) % 12 - 6


def kick_ratio(path: Path) -> float:
    x, rate = read_mono(path)
    spec = np.abs(np.fft.rfft(x)) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / rate)
    return float(spec[(freqs > 30) & (freqs < 120)].sum() / spec[freqs > 30].sum())


# --- set decisions -------------------------------------------------------------

def choose_key(loops: List[dict], wanted: str) -> str:
    if wanted != "auto":
        return wanted
    votes = Counter(l["root"] for l in loops if l["part"] and l["root"])
    return votes.most_common(1)[0][0] if votes else "C"


def section_names(count: int, wanted: List[str]) -> List[str]:
    names = list(wanted[:count]) or list(SECTION_NAMES.get(count, ()))
    return names + ["Level %d" % (i + 1) for i in range(len(names), count)]


# --- build ---------------------------------------------------------------------

def candidates(pack: dict, tags: Dict[str, Dict[str, str]]) -> List[dict]:
    loops = []
    for name, t in sorted(tags.items()):
        found = options(name, t, pack)
        if not found:
            continue
        role, kick = found[0]
        root = t.get("key signature")
        if root and root not in NOTES:
            continue
        loops.append(dict(name=name, role=role, part=role in pack["parts"], kick=kick, options=found, root=root,
                          scale=t.get("key type"), native=native_tempo(t),
                          beats=float(t["beat count"]) if t.get("beat count") else None,
                          valid=int(t["valid frames"]) if t.get("valid frames") else None,
                          lean=1 if "Intense" in t.get("descriptors", "") else
                          -1 if "Relaxed" in t.get("descriptors", "") else 0))
    return loops


def fit_to(loops: List[dict], pack: dict, scale: str, tempo: float) -> tuple:
    """Loops that fit one scale + tempo (window) + key, with their retune; returns (loops, key)."""
    drums = set(pack["drum_parts"])
    loops = [dict(l) for l in loops if not l["root"] or l["role"] in drums or l["scale"] in (scale, "both")]
    loops = [l for l in loops if not (l["part"] and l["native"])
             or abs(l["native"] / tempo - 1) <= pack["tempo_window"]]
    key = choose_key(loops, pack["key"])
    for l in loops:
        l["shift"] = shift_to(l["root"], NOTES[key]) if l["root"] and l["role"] not in drums else 0
    return [l for l in loops if abs(l["shift"]) <= pack["max_shift"]], key


def fit(loops: List[dict], pack: dict) -> tuple:
    """Pick scale and tempo ("auto" = the choice giving every part the most full sections,
    then the most loops), keep the loops that fit; return (loops, tempo, key, scale)."""
    scales = ["minor", "major"] if pack["scale"] == "auto" else [pack["scale"]]
    tempos = ([float(t) for t in sorted({round(l["native"]) for l in loops if l["part"] and l["native"]})]
              if pack["tempo"] == "auto" else [float(pack["tempo"])])
    if not tempos:
        raise SystemExit("no tagged loop tempos to choose from: set \"tempo\" in pack.json")
    best = None
    for scale in scales:
        for tempo in tempos:
            kept, key = fit_to(loops, pack, scale, tempo)
            pools = Counter(l["role"] for l in kept if l["part"])
            score = (min(pools.get(p, 0) for p in pack["parts"]) // ROWS, sum(pools.values()))
            if best is None or score > best[0]:
                best = (score, kept, tempo, key, scale)
    return best[1:]


def main(pack_path: Path, staged_root: Path) -> int:
    pack = dict(DEFAULTS, **json.loads(pack_path.read_text(encoding="utf-8")))
    if not 1 <= len(pack["parts"]) <= 6:
        raise SystemExit("pack.json: 1 to 6 parts")
    pkgs = [p if Path(p).is_absolute() else str(ROOT / p) for p in pack["packages"]]
    loops, tempo, key, scale = fit(candidates(pack, with_sibling_tags(read_tags(pkgs))), pack)

    wavs = decode_packages(pkgs, DECODED, names=[l["name"] for l in loops])
    for l in loops:
        l["path"] = wavs[l["name"]]
    for l in loops:   # settle kick rules: the first option the audio satisfies
        if any(k is not None for _, k in l["options"]):
            has_kick = kick_ratio(l["path"]) >= KICK_RATIO
            l["role"] = next((r for r, k in l["options"] if k is None or k == has_kick), None)
            l["part"] = l["role"] in pack["parts"]
    loops = [l for l in loops if l["role"]]
    for l in loops:
        l["rms"], l["onsets"] = features(l["path"])
    for r in set(l["role"] for l in loops):
        group = [l for l in loops if l["role"] == r]
        energy = (rank([l["rms"] for l in group]) + rank([l["onsets"] for l in group])) / (2 * max(len(group) - 1, 1))
        for l, e in zip(group, energy):
            l["energy"] = float(e) + 0.25 * l["lean"]

    pools = {p: sorted([l for l in loops if l["role"] == p], key=lambda l: l["energy"]) for p in pack["parts"]}
    short = {p: len(pool) for p, pool in pools.items() if len(pool) < ROWS}
    if short:
        raise SystemExit("too few loops for one full section (13): %s; widen its rules, tempo_window or "
                         "max_shift, or drop the part" % short)
    sections = min(len(p) for p in pools.values()) // ROWS
    layout = {"name": pack["name"], "tempo": tempo, "key": "%s %s" % (key, scale), "rows_per_section": ROWS,
              "sections": section_names(sections, pack["sections"]), "parts": list(pack["parts"]),
              "drum_parts": list(pack["drum_parts"]), "tracks": {}, "left_out": {}}
    need = sections * ROWS
    for p, pool in pools.items():
        if p in pack["drum_parts"]:
            chosen = [pool[i] for i in spread(list(range(len(pool))), need)]
        else:   # least retuning and stretching first, then energy order
            chosen = sorted(pool, key=lambda l: (abs(l["shift"]), abs((l["native"] or tempo) / tempo - 1)))[:need]
            chosen.sort(key=lambda l: l["energy"])
        layout["tracks"][p] = [clip(l, row, tempo) for row, l in enumerate(chosen)]
        layout["left_out"][p] = len(pool) - need

    keep = " [%s]" % ", ".join(pack["break"]["keep"]) if pack.get("break", {}).get("keep") else ""
    breaks = sorted([l for l in loops if l["role"] == "break"], key=lambda l: l["energy"])
    if breaks:
        layout["tracks"]["Break"] = [clip(breaks[(s * BREAKS + k) % len(breaks)], s * ROWS + k, tempo,
                                          one_shot=True, suffix=keep, bars=True)
                                     for s in range(sections) for k in range(BREAKS)]
    fx = sorted([l for l in loops if l["role"] == "fx"], key=lambda l: l["energy"])
    for k, track in enumerate(FX_TRACKS if fx else ()):
        layout["tracks"][track] = [clip(fx[(s * FX + k) % len(fx)], s * ROWS, tempo, one_shot=True, instant=True)
                                   for s in range(sections)]

    stage(layout, staged_root / pack["name"])
    pack_path.parent.joinpath("layout.json").write_text(json.dumps(layout, indent=1), encoding="utf-8")
    print("%s: %s, %g BPM, %d sections: %s" % (pack["name"], layout["key"], tempo, sections,
                                               ", ".join(layout["sections"])))
    for r, rows in layout["tracks"].items():
        print("  %-12s %3d clips, %s left out" % (r, len(rows), layout["left_out"].get(r, "-")))
    return 0


def clip(l: dict, row: int, tempo: float, one_shot: bool = False, suffix: str = "", bars: bool = False,
         instant: bool = False) -> dict:
    """`audio_beats` = the sound's own length at the set tempo (one-shots play unstretched);
    `beats` = the clip's length: tagged loop length, the sound itself, or whole bars."""
    frames = l["valid"] or len(read_mono(l["path"])[0])
    audio_beats = round(frames / RATE * tempo / 60, 3)
    beats = l["beats"] if l["beats"] and not one_shot else audio_beats
    if bars:  # breaks last whole bars, so paused parts come back on the bar
        beats = max(4, 4 * round(audio_beats / 4))
    return dict(row=row, name=l["name"] + suffix, file=l["name"] + ".wav", source=str(l["path"]),
                beats=beats, audio_beats=audio_beats, priming=0, frames=frames, shift=l["shift"],
                root=l["root"], energy=round(l["energy"], 3), loop=not one_shot, instant=instant)


def needs_render(c: dict, tempo: float) -> bool:
    """A clip GarageBand would retune (any clip) or re-tempo (loops): done offline, so Live
    never warps or pitch-shifts while playing."""
    stretched = c["loop"] and abs(c["frames"] / RATE - c["beats"] * 60 / tempo) > 0.001
    return c["shift"] != 0 or stretched


def stage(layout: dict, staged: Path) -> None:
    """Put the chosen WAVs under the User Library link (settings.STAGED): loops needing a new
    key or tempo are rendered to exactly `beats`; everything else is copied as-is."""
    tempo, key = layout["tempo"], layout["key"].split()[0]
    for r, rows in layout["tracks"].items():
        dst = staged / r
        dst.mkdir(parents=True, exist_ok=True)
        for c in rows:
            source = Path(c.pop("source"))
            if needs_render(c, tempo):
                length = c["beats"] if c["loop"] else c["audio_beats"]   # one-shots: retune only
                target = dst / ("%s (%s %g).wav" % (c["file"][:-4], key, tempo))
                if not target.exists():
                    if shutil.which("ffmpeg") is None:
                        raise RuntimeError("ffmpeg (with the rubberband filter) is needed to render loops")
                    render(source, target, 0, c["frames"], length, c["shift"], tempo, shutil.which("ffmpeg"))
                c.update(rendered_from=c["shift"], shift=0,
                         frames=int(round(length * 60 / tempo * RATE)), file=target.name)
                if not c["loop"]:
                    c["audio_beats"] = round(c["frames"] / RATE * tempo / 60, 3)
            else:
                target = dst / c["file"]
                if not target.exists():
                    shutil.copy2(source, target)
            c["path"] = str(target).replace("\\", "/")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pack", type=Path, help="sets/<kit>/pack.json")
    ap.add_argument("--staged", type=Path, default=Path(settings.STAGED), help="staging root (default settings.STAGED)")
    a = ap.parse_args()
    sys.exit(main(a.pack, a.staged))
