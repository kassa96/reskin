"""Le sélecteur sert le dossier studio quand il contient des visuels."""

from app import mannequins


def _make_image(path):
    from io import BytesIO

    from PIL import Image as PILImage

    img = PILImage.new("RGB", (8, 8), color="red")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    path.write_bytes(buf.getvalue())


def test_studio_dir_preferred_when_it_has_images(tmp_path, monkeypatch):
    src = tmp_path / "manoquin"
    studio = tmp_path / "manoquin_studio"
    src.mkdir()
    studio.mkdir()
    _make_image(src / "femme_blanche_1.jpeg")
    _make_image(studio / "femme_blanche_1_studio.png")

    monkeypatch.setattr(mannequins, "MANNEQUIN_DIR", src)
    monkeypatch.setattr(mannequins, "STUDIO_DIR", studio)

    assert mannequins.active_mannequin_dir() == studio
    (item,) = mannequins.list_mannequins()
    assert item["id"] == "femme_blanche_1"
    assert item["filename"] == "femme_blanche_1_studio.png"
    assert item["label"] == "Woman (light skin) 1"
    assert mannequins.get_mannequin_path("femme_blanche_1") == studio / "femme_blanche_1_studio.png"


def test_falls_back_to_source_dir_when_studio_empty(tmp_path, monkeypatch):
    src = tmp_path / "manoquin"
    studio = tmp_path / "manoquin_studio"
    src.mkdir()
    studio.mkdir()
    _make_image(src / "femme_blanche_1.jpeg")

    monkeypatch.setattr(mannequins, "MANNEQUIN_DIR", src)
    monkeypatch.setattr(mannequins, "STUDIO_DIR", studio)

    assert mannequins.active_mannequin_dir() == src
    (item,) = mannequins.list_mannequins()
    assert item["id"] == "femme_blanche_1"
    assert item["filename"] == "femme_blanche_1.jpeg"
