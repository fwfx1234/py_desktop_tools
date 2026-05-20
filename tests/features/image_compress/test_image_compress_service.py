from __future__ import annotations

from pathlib import Path

from PIL import Image

from features.image_compress.service import ImageCompressService, _normalize_path


def _make_image(path: Path, size=(200, 200), color=(123, 222, 64)) -> None:
    img = Image.new("RGB", size, color=color)
    img.save(path)


def test_add_pending_records_state_and_source(tmp_path: Path):
    src = tmp_path / "a.jpg"
    _make_image(src)
    out = tmp_path / "out"
    service = ImageCompressService(output_dir=out)
    added = service.add_pending([str(src)], from_clipboard=False)
    assert len(added) == 1
    entry = added[0]
    assert entry.state == "pending"
    assert entry.source == str(src)
    assert entry.file_name == "a.jpg"
    assert entry.from_clipboard is False
    assert entry.original_bytes > 0


def test_add_pending_clipboard_clears_source(tmp_path: Path):
    src = tmp_path / "clip.png"
    _make_image(src)
    out = tmp_path / "out"
    service = ImageCompressService(output_dir=out)
    added = service.add_pending([str(src)], from_clipboard=True)
    entry = added[0]
    assert entry.from_clipboard is True
    assert entry.source == ""
    assert entry.file_name == "(剪贴板)"
    payload = entry.to_dict()
    assert payload["fromClipboard"] is True
    assert payload["source"] == ""


def test_compress_pending_processes_all_pending(tmp_path: Path):
    src_a = tmp_path / "a.jpg"
    src_b = tmp_path / "b.jpg"
    _make_image(src_a, size=(400, 400))
    _make_image(src_b, size=(400, 400))
    out = tmp_path / "out"
    service = ImageCompressService(output_dir=out)
    service.add_pending([str(src_a), str(src_b)], from_clipboard=False)
    assert len(service.pending_ids()) == 2
    service.compress_pending(quality=40, mode="normal")
    assert service.pending_ids() == []
    for entry in service.entries():
        assert entry.state == "success"
        assert Path(entry.output).exists()


def test_compress_pending_with_no_pending_returns_existing(tmp_path: Path):
    out = tmp_path / "out"
    service = ImageCompressService(output_dir=out)
    rows = service.compress_pending(quality=50, mode="normal")
    assert rows == []


def test_overwrite_blocks_clipboard_source(tmp_path: Path):
    src = tmp_path / "clip2.png"
    _make_image(src)
    out = tmp_path / "out"
    service = ImageCompressService(output_dir=out)
    service.add_pending([str(src)], from_clipboard=True)
    service.compress_pending(quality=80, mode="visual")
    entry = service.entries()[0]
    assert entry.state == "success"
    ok, message = service.overwrite_original(entry.id)
    assert ok is False
    assert "剪贴板" in message
    # 源文件未被改写
    assert src.stat().st_size > 0


def test_overwrite_original_replaces_file_source(tmp_path: Path):
    src = tmp_path / "overwrite_me.jpg"
    _make_image(src, size=(500, 500))
    original_size = src.stat().st_size
    out = tmp_path / "out"
    service = ImageCompressService(output_dir=out)
    service.add_pending([str(src)], from_clipboard=False)
    service.compress_pending(quality=20, mode="normal")
    entry = service.entries()[0]
    ok, message = service.overwrite_original(entry.id)
    assert ok
    assert message == str(src)
    assert src.stat().st_size < original_size


def test_save_as_copies_to_target(tmp_path: Path):
    src = tmp_path / "sa.jpg"
    _make_image(src)
    out = tmp_path / "out"
    service = ImageCompressService(output_dir=out)
    service.add_pending([str(src)], from_clipboard=False)
    service.compress_pending(quality=70, mode="normal")
    entry = service.entries()[0]
    target = tmp_path / "saved" / "result"
    ok, saved = service.save_as(entry.id, str(target))
    assert ok
    assert Path(saved).exists()
    assert saved.endswith(".jpg")


def test_retry_after_failure(tmp_path: Path):
    missing = tmp_path / "ghost.jpg"
    out = tmp_path / "out"
    service = ImageCompressService(output_dir=out)
    service.add_pending([str(missing)], from_clipboard=False)
    entry = service.entries()[0]
    assert entry.state == "failed"  # marked at add time because file missing
    # Make the file exist now
    _make_image(missing)
    refreshed = service.retry(entry.id, quality=60, mode="normal")
    assert refreshed is not None
    assert refreshed.state == "success"
    assert Path(refreshed.output).exists()


def test_remove_cleans_output_and_pending(tmp_path: Path):
    src = tmp_path / "r.jpg"
    _make_image(src)
    out = tmp_path / "out"
    service = ImageCompressService(output_dir=out)
    service.add_pending([str(src)], from_clipboard=False)
    service.compress_pending(quality=60, mode="normal")
    entry = service.entries()[0]
    output_path = Path(entry.output)
    assert output_path.exists()
    service.remove(entry.id)
    assert not output_path.exists()
    assert service.get(entry.id) is None


def test_clear_removes_all(tmp_path: Path):
    src = tmp_path / "c.jpg"
    _make_image(src)
    out = tmp_path / "out"
    service = ImageCompressService(output_dir=out)
    service.add_pending([str(src)], from_clipboard=False)
    service.add_pending([str(src)], from_clipboard=False)
    service.compress_pending(quality=60, mode="normal")
    assert len(service.entries()) == 2
    service.clear()
    assert service.entries() == []


def test_normalize_path_strips_file_scheme():
    assert _normalize_path("file:///Users/foo/bar.png") == "/Users/foo/bar.png"
    assert _normalize_path("'/tmp/abc.png'") == "/tmp/abc.png"
