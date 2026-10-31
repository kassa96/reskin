from fastapi import APIRouter

from app.examples import list_examples

router = APIRouter(prefix="/api", tags=["exemples"])


@router.get("/exemples")
async def get_exemples() -> list[dict]:
    """Toutes les transformations enregistrées, avec URLs web allégées."""
    return [
        {
            "id": item["id"],
            "titre": item["titre"],
            "categorie": item["categorie"],
            "description": item["description"],
            "lien_alibaba": item["lien_alibaba"],
            "produit_url": f"/static/exemples/{item['produit_web']}"
            if item["produit_web"]
            else None,
            "produit_original_url": f"/static/exemples-src/{item['produit']}"
            if item["produit"]
            else None,
            "reference_url": f"/static/exemples/{item['reference_web']}"
            if item["reference_web"]
            else None,
            "reference_original_url": f"/static/exemples-src/{item['reference']}"
            if item["reference"]
            else None,
            "resultat_url": f"/static/exemples/{item['resultat_web']}",
            "resultat_original_url": f"/static/exemples-src/{item['resultat']}",
        }
        for item in list_examples()
    ]
