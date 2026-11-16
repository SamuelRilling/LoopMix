"""Static overview of a set: sections x parts x the 13 white keys, plus breaks and FX.

Usage:  python tools/set_map.py <layout.json> [out.html]
Output: self-contained HTML, default <layout dir>/set-map.html (git-ignored).
Colours match LoopMix/viz.html: loop teal, break amber, FX pink.
"""
import html
import json
import re
import sys
from pathlib import Path

WHITE_KEYS = ("D3", "E3", "F3", "G3", "A3", "B3", "C4", "D4", "E4", "F4", "G4", "A4", "B4")
BREAK_KEYS = ("C#3", "D#3", "F#3", "G#3", "A#3")
FX_KEYS = ("C#4", "D#4", "F#4", "G#4", "A#4")
PARTS = ("Drums", "Bass", "Part A", "Part B", "Part X")
FX_TRACKS = tuple("FX %d" % (i + 1) for i in range(5))

CSS = """
:root{--bg:#0e0f12;--panel:#17191e;--line:#2a2d35;--text:#e9e6df;--dim:#8a8d96;--loop:#49d6c4;--break:#f2a93b;--fx:#e0559b;
--font:"Bahnschrift","DIN Alternate","Segoe UI Variable Display",system-ui,sans-serif;--mono:"Cascadia Mono",Consolas,ui-monospace,monospace}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:var(--font)}
main{max-width:1400px;margin:0 auto;padding:20px 16px 32px}
h1{margin:0;font-size:15px;letter-spacing:.32em;font-weight:600;color:var(--dim)}
.meta{font-family:var(--mono);font-size:13px;color:var(--dim);margin:8px 0 18px}.meta b{color:var(--text);font-weight:500}
nav{display:flex;gap:4px;flex-wrap:wrap}
nav button{font:inherit;color:var(--dim);background:var(--panel);border:0;border-top:3px solid var(--line);padding:10px 14px;cursor:pointer}
nav button:hover,nav button:focus-visible{color:var(--text)}nav button[aria-selected=true]{color:var(--text);border-top-color:var(--loop);background:#1c2a2a}
section{display:none;margin-top:4px}section.on{display:block}
table{width:100%;border-collapse:collapse;background:var(--panel);table-layout:fixed}
th,td{padding:6px 10px;text-align:left;font-size:13px;border-bottom:1px solid var(--line);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
th{font-family:var(--mono);font-size:11px;letter-spacing:.14em;color:var(--dim);font-weight:400}
td.k{font-family:var(--mono);color:var(--loop);width:56px}td.empty{color:var(--line)}
.lists{display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-top:4px}
.lists div{background:var(--panel);padding:12px 14px}.lists h2{margin:0 0 8px;font-size:12px;letter-spacing:.2em;font-weight:600}
.break h2,.break .k{color:var(--break)}.fx h2,.fx .k{color:var(--fx)}
.lists p{margin:3px 0;font-size:13px;display:flex;gap:10px}.lists .k{font-family:var(--mono);min-width:34px}
@media(max-width:700px){.lists{grid-template-columns:1fr}table{table-layout:auto}}
"""

JS = """
const tabs=[...document.querySelectorAll('nav button')],panels=[...document.querySelectorAll('section')];
tabs.forEach((b,i)=>b.onclick=()=>{tabs.forEach((t,j)=>t.setAttribute('aria-selected',i===j));panels.forEach((p,j)=>p.classList.toggle('on',i===j))});
"""


def label(name: str) -> str:
    """Clip name without the `[Bass, Part A]` keep-list (shown on its own)."""
    return re.sub(r"\s*\[[^\]]*\]", "", name)


def by_row(layout: dict, track: str) -> dict:
    return {c["row"]: c for c in layout["tracks"].get(track, [])}


def esc(s) -> str:
    return html.escape(str(s))


def keyed(keys, names) -> str:
    return "".join('<p><span class="k">%s</span>%s</p>' % (k, esc(n) if n else "–") for k, n in zip(keys, names))


def section_html(layout: dict, s: int, on: bool) -> str:
    per = layout["rows_per_section"]
    parts = [p for p in PARTS if p in layout["tracks"]]
    rows = {p: by_row(layout, p) for p in parts}
    head = "<tr><th>KEY</th>%s</tr>" % "".join("<th>%s</th>" % esc(p.upper()) for p in parts)
    body = ""
    for i, key in enumerate(WHITE_KEYS[:per]):
        cells = ""
        for p in parts:
            c = rows[p].get(s * per + i)
            cells += '<td title="%s">%s</td>' % (esc(c["name"]), esc(label(c["name"]))) if c else '<td class="empty">–</td>'
        body += '<tr><td class="k">%s</td>%s</tr>' % (key, cells)
    breaks = by_row(layout, "Break")
    brk = keyed(BREAK_KEYS, [breaks[s * per + k]["name"] if s * per + k in breaks else "" for k in range(5)])
    fx = []
    for t in FX_TRACKS:
        c = by_row(layout, t).get(s * per)
        fx.append(c["name"] if c else "")
    return ('<section%s><table>%s%s</table><div class="lists"><div class="break"><h2>BREAKS</h2>%s</div>'
            '<div class="fx"><h2>FX</h2>%s</div></div></section>'
            % (' class="on"' if on else "", head, body, brk, keyed(FX_KEYS, fx)))


def render_page(layout: dict, title: str = "set") -> str:
    names = layout["sections"]
    tabs = "".join('<button aria-selected="%s">S%d %s</button>' % ("true" if i == 0 else "false", i + 1, esc(n))
                   for i, n in enumerate(names))
    panels = "".join(section_html(layout, i, i == 0) for i in range(len(names)))
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>LoopMix Set Map</title><style>%s</style></head><body><main><h1>LOOPMIX · %s</h1>'
            '<p class="meta"><b>%s</b> BPM · key <b>%s</b> · <b>%d</b> sections · <b>%d</b> rows per section</p>'
            '<nav>%s</nav>%s</main><script>%s</script></body></html>'
            % (CSS, esc(title.upper()), esc(layout["tempo"]), esc(layout.get("key") or "–"),
               len(names), layout["rows_per_section"], tabs, panels, JS))


def main(layout_path: str, out_path: str = None) -> int:
    src = Path(layout_path)
    out = Path(out_path) if out_path else src.parent / "set-map.html"
    out.write_text(render_page(json.loads(src.read_text(encoding="utf-8")), src.parent.name), encoding="utf-8")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
