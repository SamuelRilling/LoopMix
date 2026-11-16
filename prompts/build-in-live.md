# Task: get a layout into Ableton Live and validate it

Input: `sets/<kit>/layout.json` (from `prompts/garageband-set.md` or `prompts/kit-set.md`). Read the validation checklist in
`docs/building-sets.md`. Pick the path by Live's version.

## Path A — Live 11 (this setup): generate the `.als`
Live 11's API can't import audio, so the Set is a generated file.
1. Generate (never overwrite another kit's `.als`):
   ```bash
   python tools/als_writer.py templates/base.als sets/<kit>/layout.json "sets/<kit>/<Name>.als"
   ```
2. Check the file (scenes = sections × 13, clips = layout clips, every sample exists):
   ```bash
   python -c "import gzip,json,os,sys,xml.etree.ElementTree as E; lay=json.load(open(sys.argv[2])); r=E.fromstring(gzip.open(sys.argv[1]).read()); want=sum(map(len,lay['tracks'].values())); paths=[x.get('Value') for x in r.findall('.//AudioClip/SampleRef/FileRef/Path')]; print('scenes',len(r.findall('.//Scenes/Scene')),'of',13*len(lay['sections']),'| clips',len(paths),'of',want,'| missing',[p for p in paths if not os.path.exists(p)])" "sets/<kit>/<Name>.als" sets/<kit>/layout.json
   ```
   Any mismatch or a non-empty `missing` list: stop and fix (usually the `Samples/LoopMix` junction, see `docs/setup.md`).
3. User steps (you can't run Live): close any open copy of this Set with **Don't Save**; open the `.als`; restart Live first only if `LoopMix/` or
   `config.py` changed; Preferences → Link/Tempo/MIDI shows Control Surface LoopMix; open <http://127.0.0.1:9890> and check the key map shows
   the sections and loop names; press one key per part, a break, an FX, an octave button.

## Path B — Live ≥ 12.0.5 with the Ableton MCP server
`create_audio_clip` exists there, so the Set can be built in the running Live instead of a file. Only use it if the MCP server is connected and
its tool list contains it (list the tools first; if not, use Path A).
1. Create/rename tracks to `config.PART_TRACKS`, `Break`, `FX 1`…`FX 5` and the `Play` track (MIDI, with Pitch → an instrument), and `sections × 13` scenes named
   `S<n> <Section> · <key>` (keys `D3 E3 F3 G3 A3 B3 C4 D4 E4 F4 G4 A4 B4`), as in `als_writer`.
2. For every clip in `layout.json`: `create_audio_clip` on the track named like the layout track, slot `row`, file `path`; set loop on for `loop: true`, off
   otherwise; name = `name`; FX clips launch quantization None, loops Global (1 bar); set warping off (files are already at the set tempo and key; keep
   markers 1:1), tempo = `tempo`.
3. Do the same checks as Path A step 2 by reading the Set back through the MCP (scene count, clip count per track, names).
4. User steps: same as Path A step 3.

## Report
Path used, the check output, anything not verified (you can't hear it), the user steps.
