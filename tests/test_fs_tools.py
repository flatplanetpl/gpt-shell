import os
from pathlib import Path


def test_write_file_creates_backup(mod, tmp_path):
    p = tmp_path / "a/b.txt"
    p.parent.mkdir(parents=True)
    p.write_text("v1", encoding="utf-8")
    res = mod.write_file(str(p), "v2")
    assert res["written"] == 2
    assert res["backup"]
    assert p.read_text(encoding="utf-8") == "v2"
    backup = Path(res["backup"])
    assert backup.exists()
    assert backup.read_text(encoding="utf-8") == "v1"


def test_read_file_range_basic(mod, tmp_path):
    p = tmp_path / "data.txt"
    p.write_text("abcdef", encoding="utf-8")
    r = mod.read_file_range(str(p), start=2, size=3)
    assert r["content"] == "cde"
    assert r["start"] == 2
    assert r["size"] == 3
    assert r["next_start"] == 5
    assert r["file_size"] == 6


def test_search_text_truncated(mod, tmp_path):
    for i in range(5):
        (tmp_path / f"f{i}.txt").write_text("x\ny\npattern\n", encoding="utf-8")
    r = mod.search_text("pattern", path=str(tmp_path), regex=False, max_results=3)
    assert r["truncated"] is True
    assert len(r["results"]) == 3


def test_within_workdir_security(mod, tmp_path):
    # Ścieżka względna w WORKDIR powinna przejść
    safe = mod.within_workdir(Path("ok.txt"))
    assert str(safe).startswith(str(tmp_path))
    # Ścieżka absolutna poza WORKDIR powinna rzucić PermissionError
    outside = Path("/") / "etc" / "passwd"
    try:
        mod.within_workdir(outside)
        assert False, "Expected PermissionError"
    except PermissionError:
        pass


def test_ensure_context_file_and_prompt(mod, tmp_path):
    ctx = mod.ensure_context_file()
    assert "instructions" in ctx
    sp = mod.build_system_prompt(ctx)
    assert "Zanim poprosisz o edycję" in sp
    assert "[Kontekst]" in sp
