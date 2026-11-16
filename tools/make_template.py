"""Make templates/base.als from a working Live Set: keep the MIDI tracks, returns, master
and one session AudioClip (als_writer's clip template); drop all other clips. Of the
audio tracks only the one holding that clip stays, renamed "Prototype": als_writer
clones it once per track the set needs, then removes it.

Usage:  python tools/make_template.py <source.als> [templates/base.als]
"""
import gzip
import re
import sys
from pathlib import Path

import settings

ARRANGEMENT = re.compile(r"<Events>\s*<AudioClip .*?</AudioClip>\s*</Events>", re.S)  # arrangement/take-lane clips
AUDIO_TRACK = re.compile(r'<AudioTrack Id="\d+">.*?</AudioTrack>', re.S)
SESSION_CLIP = re.compile(r"<Value>\s*<AudioClip .*?</AudioClip>\s*</Value>", re.S)


def make_template(xml: str) -> str:
    xml = ARRANGEMENT.sub("<Events />", xml)
    first = SESSION_CLIP.search(xml)
    head, tail = xml[:first.end()], xml[first.end():]
    xml = head + SESSION_CLIP.sub("<Value />", tail)
    for m in reversed(list(AUDIO_TRACK.finditer(xml))):
        if not m.start() <= first.start() < m.end():
            xml = xml[:m.start()] + xml[m.end():]
    for tag in ("EffectiveName", "UserName"):
        xml = re.sub(r'(<AudioTrack .*?<%s Value=")[^"]*(")' % tag, r"\g<1>Prototype\g<2>", xml, count=1, flags=re.S)
    return xml


if __name__ == "__main__":
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else settings.TEMPLATE
    out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out, "wb") as f:
        f.write(make_template(gzip.open(sys.argv[1]).read().decode("utf-8")).encode("utf-8"))
    print("wrote", out)
