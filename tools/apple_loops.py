"""Read GarageBand's own loop metadata from Apple's content packages.

Apple ships each loop pack as a .pkg (xar archive) whose Payload is a gzip'd
cpio archive of .caf files. Each .caf carries a `uuid` chunk with the tags
GarageBand's loop browser filters on: category, subcategory, key, key type,
beat count and descriptors (Single/Ensemble, Part/Fill, Relaxed/Intense, ...).

Only the metadata is read here; the audio comes from your WAV copies.
"""
import gzip
import re
import struct
import zlib
from pathlib import Path
from typing import Dict, Iterator, Tuple

LOOP_TAGS_UUID = bytes.fromhex("29819273b5bf4aefb78d62d1ef90bb2c")


def _payload(pkg: Path) -> bytes:
    with pkg.open("rb") as f:
        magic, header_size, _, toc_len, _, _ = struct.unpack(">4sHHQQI", f.read(28))
        if magic != b"xar!":
            raise ValueError(f"{pkg.name}: not a xar package")
        f.seek(header_size)
        toc = zlib.decompress(f.read(toc_len)).decode()
        for data, name in re.findall(r'<file id="\d+">\s*<data>(.*?)</data>.*?<name>(.*?)</name>', toc, re.S):
            if name == "Payload":
                offset = int(re.search(r"<offset>(\d+)", data).group(1))
                length = int(re.search(r"<length>(\d+)", data).group(1))
                f.seek(header_size + toc_len + offset)
                return gzip.decompress(f.read(length))
    raise ValueError(f"{pkg.name}: no Payload")


def _cpio(buf: bytes) -> Iterator[Tuple[str, bytes]]:
    """Old-ASCII ('070707') cpio entries."""
    p = 0
    while p < len(buf):
        if buf[p:p + 6] != b"070707":
            raise ValueError("unexpected cpio header")
        name_size = int(buf[p + 59:p + 65], 8)
        file_size = int(buf[p + 65:p + 76], 8)
        name = buf[p + 76:p + 76 + name_size - 1].decode()
        start = p + 76 + name_size
        if name == "TRAILER!!!":
            return
        yield name, buf[start:start + file_size]
        p = start + file_size


def _loop_tags(caf: bytes) -> Dict[str, str]:
    """GarageBand tags, plus 'valid frames' and 'priming frames' from the pakt chunk.

    AAC decoders put `priming frames` of padding before the audio; a WAV made
    from the .caf keeps it, so a clip must start that many frames in.
    """
    tags = {}
    p = 8
    while p + 12 <= len(caf):
        kind = caf[p:p + 4]
        size = struct.unpack(">q", caf[p + 4:p + 12])[0]
        body = caf[p + 12:p + 12 + size]
        if kind == b"uuid" and body[:16] == LOOP_TAGS_UUID:
            fields = body[20:].split(b"\x00")
            tags.update({fields[i].decode(): fields[i + 1].decode() for i in range(0, len(fields) - 1, 2)})
        elif kind == b"pakt":
            _, valid, priming, _ = struct.unpack(">qqii", body[:24])
            tags["valid frames"], tags["priming frames"] = str(valid), str(priming)
        if size < 0:
            break
        p += 12 + size
    return tags


def read_packages(pkgs) -> Dict[str, Dict[str, str]]:
    """Loop name (no extension) -> GarageBand tags, across all packages."""
    tags = {}
    for pkg in pkgs:
        for name, data in _cpio(_payload(Path(pkg))):
            if name.endswith(".caf"):
                tags[Path(name).stem] = _loop_tags(data)
    return tags
