from types import SimpleNamespace

from sehtsnap.screens.snap import _read_file
from sehtsnap.services.ai_vision_service import MAX_UPLOAD_BYTES


def picked(data=None, path=None) -> SimpleNamespace:
    return SimpleNamespace(bytes=data, path=path)


def test_web_upload_uses_browser_bytes():
    assert _read_file(picked(b"image"), allow_local_path=False) == b"image"


def test_web_upload_never_reads_server_path(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_bytes(b"private")
    assert _read_file(picked(path=str(secret)), allow_local_path=False) is None


def test_mobile_upload_can_read_local_path(tmp_path):
    photo = tmp_path / "photo.jpg"
    photo.write_bytes(b"image")
    assert _read_file(picked(path=str(photo)), allow_local_path=True) == b"image"


def test_oversized_browser_upload_is_rejected():
    data = b"x" * (MAX_UPLOAD_BYTES + 1)
    assert _read_file(picked(data), allow_local_path=False) is None
