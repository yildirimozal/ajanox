"""primitives testleri: read_file, list_files, bash."""

from ajanox.core import primitives
from ajanox.core.primitives import bash, list_files, read_file


def test_read_file_success(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("merhaba", encoding="utf-8")
    assert read_file(str(f)) == "merhaba"


def test_read_file_missing(tmp_path):
    assert read_file(str(tmp_path / "yok.txt")).startswith("Hata:")


def test_read_file_truncates(tmp_path):
    f = tmp_path / "big.txt"
    f.write_text("x" * 5000, encoding="utf-8")
    assert len(read_file(str(f))) == primitives.MAX_OUTPUT


def test_list_files_sorted(tmp_path):
    (tmp_path / "b.txt").write_text("", encoding="utf-8")
    (tmp_path / "a.txt").write_text("", encoding="utf-8")
    assert list_files(str(tmp_path)) == "a.txt\nb.txt"


def test_list_files_empty(tmp_path):
    assert list_files(str(tmp_path)) == "(boş klasör)"


def test_list_files_missing(tmp_path):
    assert list_files(str(tmp_path / "yok")).startswith("Hata:")


def test_bash_echo():
    assert bash("echo hi") == "hi"


def test_bash_no_output():
    assert "exit 0" in bash("true")


def test_bash_truncates():
    out = bash("python3 -c \"print('x'*5000, end='')\"")
    assert len(out) == primitives.MAX_OUTPUT


def test_bash_timeout(monkeypatch):
    monkeypatch.setattr(primitives, "BASH_TIMEOUT", 1)
    assert "saniye" in bash("sleep 3")
