"""Tests for file-based source-material text storage.

Mirrors test_content_storage.py: a round trip through save then load should
return exactly what was saved, with an instance-relative (not absolute) path.
"""

from pathlib import Path

from app.services.source_material_storage import load_source_material_text, save_source_material_text


def test_save_source_material_text_returns_a_path(app) -> None:
    with app.app_context():
        path = save_source_material_text("src-1", "Extracted text about GPU memory coalescing.")

        assert path.endswith("src-1.txt")


def test_save_source_material_text_returns_a_path_relative_to_instance_path(app) -> None:
    with app.app_context():
        path = save_source_material_text("src-1", "Some extracted text.")

        assert not Path(path).is_absolute()


def test_load_source_material_text_round_trips_saved_text(app) -> None:
    with app.app_context():
        text = "A paper about efficient memory coalescing in CUDA kernels."
        path = save_source_material_text("src-2", text)

        loaded = load_source_material_text(path)

        assert loaded == text


def test_load_source_material_text_accepts_an_absolute_path(app, tmp_path) -> None:
    text_file = tmp_path / "legacy-source.txt"
    text_file.write_text("legacy extracted text")

    with app.app_context():
        loaded = load_source_material_text(str(text_file))

    assert loaded == "legacy extracted text"
