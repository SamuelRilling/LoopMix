"""Make templates/base.als from a working Live Set: keep tracks, returns, master and
one session AudioClip (als_writer's clip template); drop all other clips.

Usage:  python tools/make_template.py <source.als> [templates/base.als]
"""
import gzip
import re
import sys
from pathlib import Path

import settings

ARRANGEMENT = re.compile(r"<Events>\s*<AudioClip .*?</AudioClip>\s*</Events>", re.S)  # arrangement/take-lane clips
SESSION_CLIP = re.compile(r"<Value>\s*<AudioClip .*?</AudioClip>\s*</Value>", re.S)


def make_template(xml: str) -> str:
    xml = ARRANGEMENT.sub("<Events />", xml)
    first = SESSION_CLIP.search(xml)
    head, tail = xml[:first.end()], xml[first.end():]
    return head + SESSION_CLIP.sub("<Value />", tail)


if __name__ == "__main__":
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else settings.TEMPLATE
    out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out, "wb") as f:
        f.write(make_template(gzip.open(sys.argv[1]).read().decode("utf-8")).encode("utf-8"))
    print("wrote", out)
