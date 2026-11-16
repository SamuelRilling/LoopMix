import struct
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from audio import read_loop_meta  # noqa: E402


def make_wav(path, *chunks):
    """A tiny WAV with extra RIFF chunks (kind, body) appended after the audio."""
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(44100)
        w.writeframes(bytes(200))
    data = path.read_bytes()
    extra = b"".join(k + struct.pack("<I", len(b)) + b + bytes(len(b) % 2) for k, b in chunks)
    path.write_bytes(data[:4] + struct.pack("<I", len(data) - 8 + len(extra)) + data[8:] + extra)


def acid(flags, root, beats, tempo):
    return b"acid", struct.pack("<IHHfIHHf", flags, root, 0x8000, 0.0, beats, 4, 4, tempo)


def smpl(unity):
    return b"smpl", struct.pack("<9I", 0, 0, 22675, unity, 0, 0, 0, 0, 0)


def test_acid_chunk(tmp_path):
    make_wav(tmp_path / "a.wav", acid(0x02 | 0x04, 57, 8, 120.0))
    assert read_loop_meta(tmp_path / "a.wav") == {"one_shot": False, "root": 57, "beats": 8, "tempo": 120.0}


def test_acid_one_shot_without_root(tmp_path):
    make_wav(tmp_path / "a.wav", acid(0x01, 60, 0, 0.0))
    assert read_loop_meta(tmp_path / "a.wav") == {"one_shot": True}


def test_smpl_unity_note_is_the_root_when_acid_has_none(tmp_path):
    make_wav(tmp_path / "a.wav", smpl(45))
    assert read_loop_meta(tmp_path / "a.wav") == {"root": 45}
    make_wav(tmp_path / "b.wav", smpl(45), acid(0x02, 57, 4, 90.0))
    assert read_loop_meta(tmp_path / "b.wav")["root"] == 57


def test_plain_wav_has_no_metadata(tmp_path):
    make_wav(tmp_path / "a.wav")
    assert read_loop_meta(tmp_path / "a.wav") == {}
