import pytest

from notes_svc import export as export_mod
from notes_svc.notes import create_note


@pytest.fixture(autouse=True)
def tmp_exports(tmp_path, monkeypatch):
    monkeypatch.setattr(export_mod, "EXPORT_DIR", tmp_path / "exports")


def test_export_writes_txt(conn):
    create_note(conn, 1, "hello", "world")
    path = export_mod.export_notes(conn, 1, "mine")
    assert path.suffix == ".txt" and "hello" in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("bad", ["../x", "a/b", "", "x" * 65, "na me"])
def test_export_rejects_unsafe_names(conn, bad):
    with pytest.raises(ValueError):
        export_mod.export_notes(conn, 1, bad)
