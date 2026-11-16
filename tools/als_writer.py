"""Write a LoopMix Live Set from a layout.json, using a template Set (templates/base.als).

Live 11 can't import audio through its API, so the Set file is generated.
A .als is gzip'd XML. From the template we reuse one audio clip, one scene and
every track; we rebuild the scenes and clip slots, clone the Break track into
an FX track, and set the tempo. Clips start after each file's AAC padding.

Usage:  python tools/als_writer.py <templates/base.als> <layout.json> <out.als>
"""
import gzip
import itertools
import json
import os
import re
import sys
import wave
from pathlib import Path

import settings

RATE = 44100
LIBRARY_ROOT = settings.USER_LIBRARY
CORE = settings.CORE_DEVICES
PITCH_PRESET = CORE + "MIDI Effects/Pitch/+ 12.adv"
PLAY_PRESET = CORE + "Instruments/Wavetable/Synth Lead/Bright SAW Lead.adv"
SECTION_COLORS = (26, 6, 2, 14, 18, 10)    # Live palette indexes, one per section
WARP_BEATS, WARP_COMPLEX = 0, 4
DRUM_TRACKS = ("Drums", "Part X")
LAUNCH_GLOBAL, LAUNCH_NOW = 0, 1   # clip launch quantization: Global / None


def element(xml: str, start_tag: str, end_tag: str, start: int = 0) -> tuple:
    i = xml.index(start_tag, start)
    j = xml.index(end_tag, i) + len(end_tag)
    return i, j


def set_value(xml: str, tag: str, value) -> str:
    return re.sub(r'(<%s Value=")[^"]*(")' % tag, r"\g<1>%s\g<2>" % value, xml)


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def library_path(real: str) -> str:
    """samples/staged is linked into the User Library as Samples/LoopMix."""
    return LIBRARY_ROOT + "Samples/LoopMix/" + real.split("/samples/staged/", 1)[1]


def sound_beats(c: dict) -> float:
    """Beats the sound spans: a loop is stretched to exactly its tagged length so it
    repeats seamlessly; a one-shot keeps its own speed."""
    return float(c["beats"]) if c["loop"] else float(c.get("audio_beats", c["beats"]))


def warp_mode(c: dict, track: str, tempo: float) -> int:
    """Beats suits drums; on sustained sounds it chops when stretching, so melodic
    loops that are retuned or played off their own tempo use Complex instead."""
    stretched = abs(c["frames"] / RATE - sound_beats(c) * 60 / tempo) > 0.001
    melodic = track not in DRUM_TRACKS
    return WARP_COMPLEX if melodic and (c["shift"] or stretched) else WARP_BEATS


def audio_clip(template: str, c: dict, color: int, track: str) -> str:
    path = c["path"]
    lib = library_path(path)
    beats = c["beats"]
    start = c["priming"] / RATE
    end = start + c["frames"] / RATE   # the sound spans exactly its own beats: no stretching
    x = template
    for tag in ("CurrentEnd", "LoopEnd", "OutMarker", "HiddenLoopEnd"):
        x = set_value(x, tag, beats)
    for tag in ("CurrentStart", "LoopStart", "StartRelative", "HiddenLoopStart"):
        x = set_value(x, tag, 0)
    x = set_value(x, "LoopOn", "true" if c["loop"] else "false")
    x = set_value(x, "Name", esc(c["name"]))
    x = set_value(x, "Color", color)
    x = set_value(x, "RelativePath", esc(lib[len(LIBRARY_ROOT):]))
    x = set_value(x, "Path", esc(lib))
    x = set_value(x, "OriginalFileSize", os.path.getsize(path))
    x = set_value(x, "OriginalCrc", 0)
    x = set_value(x, "LastModDate", int(os.path.getmtime(path)))
    x = set_value(x, "BrowserContentPath", "")
    with wave.open(path) as w:
        x = set_value(x, "DefaultDuration", w.getnframes())
    x = set_value(x, "DefaultSampleRate", RATE)
    x = set_value(x, "PitchCoarse", c["shift"])
    x = set_value(x, "WarpMode", warp_mode(c, track, TEMPO))
    x = set_value(x, "IsWarped", "true")
    x = set_value(x, "LaunchQuantisation", LAUNCH_NOW if c.get("instant") else LAUNCH_GLOBAL)
    markers = ('<WarpMarkers><WarpMarker Id="0" SecTime="%r" BeatTime="0" />'
               '<WarpMarker Id="1" SecTime="%r" BeatTime="%r" /></WarpMarkers>'
               % (start, end, sound_beats(c)))
    return re.sub(r"<WarpMarkers>.*?</WarpMarkers>", markers, x, flags=re.S)


def slot(i: int, clip: str = "") -> str:
    value = "<Value>%s</Value>" % clip if clip else "<Value />"
    return ('<ClipSlot Id="%d"><LomId Value="0" /><ClipSlot>%s</ClipSlot>'
            '<HasStop Value="true" /><NeedRefreeze Value="true" /></ClipSlot>' % (i, value))


def rebuild_slots(track: str, rows: int, clips: dict) -> str:
    """First ClipSlotList (session clips) gets the clips; the freeze list stays empty."""
    out, pos, first = [], 0, True
    while "<ClipSlotList>" in track[pos:]:
        i, j = element(track, "<ClipSlotList>", "</ClipSlotList>", pos)
        body = "".join(slot(r, clips.get(r, "") if first else "") for r in range(rows))
        out.append(track[pos:i] + "<ClipSlotList>" + body + "</ClipSlotList>")
        pos, first = j, False
    return "".join(out) + track[pos:]


def clone_track(track: str, name: str, track_id: int, next_id: itertools.count) -> str:
    """Copy a track with fresh global ids (automation/modulation targets, pointees)."""
    track = re.sub(r'^<AudioTrack Id="\d+"', '<AudioTrack Id="%d"' % track_id, track)
    track = re.sub(r'<(\w*(?:Target|Pointee)) Id="\d+"',
                   lambda m: '<%s Id="%d"' % (m.group(1), next(next_id)), track)
    for tag in ("EffectiveName", "UserName"):
        track = re.sub(r'(<%s Value=")[^"]*(")' % tag, r"\g<1>%s\g<2>" % name, track, count=1)
    return track


def preset_device(path: str, device_id: int, next_id: itertools.count) -> str:
    """The device XML inside a Live preset (.adv), with fresh global ids."""
    preset = gzip.open(path).read().decode("utf-8")
    tag = re.search(r"<Ableton[^>]*>\s*<(\w+)>", preset).group(1)
    device = preset[slice(*element(preset, "<%s>" % tag, "</%s>" % tag))]
    device = device.replace("<%s>" % tag, '<%s Id="%d">' % (tag, device_id), 1)
    return re.sub(r'<(\w*(?:Target|Pointee)) Id="\d+"', lambda m: '<%s Id="%d"' % (m.group(1), next(next_id)), device)


def set_play_devices(xml: str, next_id: itertools.count) -> str:
    """Play track = Pitch (at 0, for the octave buttons) -> PLAY_PRESET instrument."""
    _, s, e = next(t for t in tracks(xml) if t[0] == "Play")
    pitch = preset_device(PITCH_PRESET, 0, next_id)
    p0, p1 = element(pitch, "<Pitch>", "</Pitch>")
    pitch = pitch[:p0] + set_value(pitch[p0:p1], "Manual", 0) + pitch[p1:]
    instrument = preset_device(PLAY_PRESET, 1, next_id)
    d0, d1 = element(xml, "<Devices>", "</Devices>", s)
    return xml[:d0] + "<Devices>" + pitch + instrument + "</Devices>" + xml[d1:]


def tracks(xml: str):
    """(name, start, end) of every Midi/Audio track inside <Tracks>."""
    t0, t1 = element(xml, "<Tracks>", "</Tracks>")
    for m in re.finditer(r"<(MidiTrack|AudioTrack) Id=\"\d+\">", xml[t0:t1]):
        s = t0 + m.start()
        e = xml.index("</%s>" % m.group(1), s) + len(m.group(1)) + 3
        name = re.search(r'<EffectiveName Value="([^"]*)"', xml[s:e]).group(1)
        yield name, s, e


def main(template_path: str, layout_path: str, out_path: str) -> int:
    global TEMPO
    layout = json.loads(Path(layout_path).read_text(encoding="utf-8"))
    TEMPO = layout["tempo"]
    per = layout["rows_per_section"]
    rows = per * len(layout["sections"])
    xml = gzip.open(template_path).read().decode("utf-8")
    clip_template = xml[slice(*element(xml, "<AudioClip ", "</AudioClip>"))]
    next_id = itertools.count(int(re.search(r'<NextPointeeId Value="(\d+)"', xml).group(1)))

    # Layout tracks the template lacks (the FX tracks) = clones of Break, appended in order.
    for wanted in layout["tracks"]:
        existing = list(tracks(xml))
        if any(n == wanted for n, _, _ in existing):
            continue
        _, s, e = next(t for t in existing if t[0] == "Break")
        last_end = existing[-1][2]
        track_ids = [int(i) for i in re.findall(r'<(?:MidiTrack|AudioTrack|ReturnTrack) Id="(\d+)"', xml)]
        xml = xml[:last_end] + clone_track(xml[s:e], wanted, max(track_ids) + 1, next_id) + xml[last_end:]

    xml = set_play_devices(xml, next_id)

    # Clip slots, track by track (from the end so offsets stay valid).
    for name, s, e in reversed(list(tracks(xml))):
        clips = {c["row"]: audio_clip(clip_template, c, SECTION_COLORS[c["row"] // per % len(SECTION_COLORS)], name)
                 for c in layout["tracks"].get(name, [])}
        xml = xml[:s] + rebuild_slots(xml[s:e], rows, clips) + xml[e:]

    # Scenes: one per row, named by section and key.
    s, e = element(xml, "<Scenes>", "</Scenes>")
    scene = xml[slice(*element(xml, '<Scene Id="0">', "</Scene>"))]
    keys = ("D3", "E3", "F3", "G3", "A3", "B3", "C4", "D4", "E4", "F4", "G4", "A4", "B4")
    scenes = []
    for r in range(rows):
        sec = r // per
        label = "S%d %s · %s" % (sec + 1, layout["sections"][sec], keys[r % per])
        x = re.sub(r'^<Scene Id="0">', '<Scene Id="%d">' % r, scene)
        x = set_value(set_value(x, "Name", esc(label)), "Color", SECTION_COLORS[sec % len(SECTION_COLORS)])
        scenes.append(x)
    xml = xml[:s] + "<Scenes>" + "".join(scenes) + "</Scenes>" + xml[e:]

    # Tempo (master track) and the next free global id.
    m0, m1 = element(xml, "<MasterTrack>", "</MasterTrack>")
    t0, t1 = element(xml, "<Tempo>", "</Tempo>", m0)
    xml = xml[:t0] + set_value(xml[t0:t1], "Manual", TEMPO) + xml[t1:]
    xml = set_value(xml, "NextPointeeId", next(next_id))

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out_path, "wb") as f:
        f.write(xml.encode("utf-8"))
    print("wrote %s: %d rows, tracks %s" % (out_path, rows, [n for n, _, _ in tracks(xml)]))
    return 0


TEMPO = 120.0

if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
