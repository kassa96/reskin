from fastapi import APIRouter

from app.mannequins import list_mannequins

router = APIRouter(prefix="/api", tags=["mannequins"])


@router.get("/mannequins")
async def get_mannequins() -> list[dict[str, str]]:
    return [
        {
            "id": item["id"],
            "label": item["label"],
            "image_url": f"/static/mannequins/{item['filename']}",
        }
        for item in list_mannequins()
    ]
