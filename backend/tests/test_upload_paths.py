from pathlib import Path

from app.services import knowledge


def test_resolve_local_path_checks_shared_upload_root(tmp_path, monkeypatch):
    shared_upload_root = tmp_path / "shared" / "uploads"
    shared_upload_root.mkdir(parents=True)
    target = shared_upload_root / "example.txt"
    target.write_text("conteudo", encoding="utf-8")

    monkeypatch.setattr(knowledge, "UPLOAD_ROOT", shared_upload_root)

    resolved = knowledge._resolve_local_path("uploads/example.txt")

    assert resolved == target
