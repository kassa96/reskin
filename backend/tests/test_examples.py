"""Le registre liste chaque dossier d'exemple avec ses trois visuels."""

import json

from app import examples


def _make_image(path, size=(600, 800)):
    from io import BytesIO

    from PIL import Image as PILImage

    img = PILImage.new("RGB", size, color="blue")
    buf = BytesIO()
    img.save(buf, format="PNG")
    path.write_bytes(buf.getvalue())


def _make_example(root, name, with_meta=True, with_reference=True):
    folder = root / name
    folder.mkdir()
    _make_image(folder / "person1_produit.png")
    if with_reference:
        _make_image(folder / "person2.png", size=(400, 800))
    _make_image(folder / "resultat.png", size=(900, 1200))
    if with_meta:
        (folder / "meta.json").write_text(
            json.dumps(
                {
                    "titre": "Pyjama test",
                    "categorie": "Mode",
                    "description": "Exemple de démonstration.",
                    "lien_alibaba": "https://www.alibaba.com/product-detail/test.html",
                }
            ),
            encoding="utf-8",
        )
    return folder


def test_list_examples_returns_web_versions_and_meta(tmp_path, monkeypatch):
    base = tmp_path / "exemples"
    base.mkdir()
    cache = tmp_path / "cache"
    _make_example(base, "exemple1")

    monkeypatch.setattr(examples, "EXAMPLES_DIR", base)
    monkeypatch.setattr(examples, "CACHE_DIR", cache)

    (item,) = examples.list_examples()
    assert item["id"] == "exemple1"
    assert item["titre"] == "Pyjama test"
    assert item["lien_alibaba"].startswith("https://www.alibaba.com/")
    assert item["resultat_web"] == "exemple1/resultat.jpg"
    assert (cache / "exemple1" / "resultat.jpg").is_file()
    assert item["produit_web"] == "exemple1/person1_produit.jpg"
    assert item["reference_web"] == "exemple1/person2.jpg"


def test_list_examples_skips_folders_without_result(tmp_path, monkeypatch):
    base = tmp_path / "exemples"
    base.mkdir()
    incomplete = base / "exemple-incomplet"
    incomplete.mkdir()
    _make_image(incomplete / "person1_produit.png")

    monkeypatch.setattr(examples, "EXAMPLES_DIR", base)
    monkeypatch.setattr(examples, "CACHE_DIR", tmp_path / "cache")

    assert examples.list_examples() == []


def test_list_examples_tolerates_missing_meta_and_reference(tmp_path, monkeypatch):
    base = tmp_path / "exemples"
    base.mkdir()
    _make_example(base, "exemple2", with_meta=False, with_reference=False)

    monkeypatch.setattr(examples, "EXAMPLES_DIR", base)
    monkeypatch.setattr(examples, "CACHE_DIR", tmp_path / "cache")

    (item,) = examples.list_examples()
    assert item["titre"] == "exemple2"
    assert item["reference"] is None
    assert item["reference_web"] is None


def test_list_examples_returns_empty_when_dir_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(examples, "EXAMPLES_DIR", tmp_path / "absent")
    monkeypatch.setattr(examples, "CACHE_DIR", tmp_path / "cache")

    assert examples.list_examples() == []


def test_list_examples_keeps_each_folder_with_its_own_link(tmp_path, monkeypatch):
    """Non-régression : l'exemple N affiche son propre lien, jamais celui du voisin.

    Chaque dossier garde le couple (id, lien_alibaba) de son meta.json :
    aucun mélange entre exemples dans l'affichage de la galerie.
    """
    base = tmp_path / "exemples"
    base.mkdir()
    liens = {
        "exemple1": "https://www.alibaba.com/product-detail/deodorant_1.html",
        "exemple2": "https://www.alibaba.com/product-detail/dentifrice_2.html",
    }
    for name, lien in liens.items():
        folder = base / name
        folder.mkdir()
        _make_image(folder / "person1_produit.png")
        _make_image(folder / "resultat.png", size=(900, 1200))
        (folder / "meta.json").write_text(
            json.dumps({"titre": f"Titre {name}", "lien_alibaba": lien}),
            encoding="utf-8",
        )

    monkeypatch.setattr(examples, "EXAMPLES_DIR", base)
    monkeypatch.setattr(examples, "CACHE_DIR", tmp_path / "cache")

    by_id = {item["id"]: item for item in examples.list_examples()}
    assert set(by_id) == set(liens)
    for name, lien in liens.items():
        assert by_id[name]["lien_alibaba"] == lien
        assert by_id[name]["titre"] == f"Titre {name}"
