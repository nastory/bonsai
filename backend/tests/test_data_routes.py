"""Tests for the /api/data export/import routes."""

import io
import json
import zipfile

from app.models import Course


def _seed_course(db) -> None:
    course = Course(
        id="c1", title="GPU Programming", description="d", prerequisites=[],
        estimated_timeline="1 week", thumbnail_url="x", stage="active",
    )
    db.session.add(course)
    db.session.commit()


def test_export_returns_a_zip_archive(client, db) -> None:
    _seed_course(db)

    response = client.get("/api/data/export")

    assert response.status_code == 200
    assert response.content_type == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
        data = json.loads(archive.read("data.json"))
    assert len(data["courses"]) == 1


def test_import_restores_a_previously_exported_archive(client, db) -> None:
    _seed_course(db)
    export_response = client.get("/api/data/export")

    response = client.post(
        "/api/data/import",
        data={"file": (io.BytesIO(export_response.data), "bonsai-export.zip")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert db.session.get(Course, "c1") is not None


def test_import_returns_422_for_an_invalid_archive(client, db) -> None:
    response = client.post(
        "/api/data/import",
        data={"file": (io.BytesIO(b"not a zip"), "garbage.zip")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 422
    assert "error" in response.get_json()


def test_import_returns_400_when_no_file_given(client, db) -> None:
    response = client.post("/api/data/import", data={}, content_type="multipart/form-data")

    assert response.status_code == 400


def test_reset_deletes_all_data_when_confirmed(client, db) -> None:
    _seed_course(db)

    response = client.post("/api/data/reset", json={"confirm": "delete"})

    assert response.status_code == 200
    assert db.session.get(Course, "c1") is None


def test_reset_rejects_a_missing_confirmation(client, db) -> None:
    _seed_course(db)

    response = client.post("/api/data/reset", json={})

    assert response.status_code == 400
    assert db.session.get(Course, "c1") is not None


def test_reset_rejects_a_wrong_confirmation_word(client, db) -> None:
    _seed_course(db)

    response = client.post("/api/data/reset", json={"confirm": "Delete"})

    assert response.status_code == 400
    assert db.session.get(Course, "c1") is not None
