import os
import tempfile

from tools.file_reader import read_file


def test_read_existing_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Hello, world!")
        tmppath = f.name
    try:
        result = read_file(tmppath)
        assert result == "Hello, world!"
    finally:
        os.unlink(tmppath)


def test_file_not_found():
    result = read_file("/nonexistent/file.txt")
    assert "no existe" in result


def test_directory_instead_of_file():
    result = read_file(os.path.dirname(__file__))
    assert "directorio" in result


def test_large_file():
    large = "x" * (1024 * 1024 + 1)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(large)
        tmppath = f.name
    try:
        result = read_file(tmppath)
        assert "demasiado grande" in result
    finally:
        os.unlink(tmppath)
