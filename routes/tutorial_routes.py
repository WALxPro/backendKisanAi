from fastapi import APIRouter, HTTPException
from models.tutorial_model import Tutorial, UpdateTutorial
from datetime import datetime
from database import db
from bson import ObjectId

router = APIRouter()

# ✅ Collection
tutorials_collection = db["tutorials"]


@router.post("/create")
async def create_tutorial(tutorial: Tutorial):
    tutorial_dict = tutorial.dict()

    tutorial_dict["created_at"] = datetime.utcnow()

    # ensure string conversion
    if tutorial_dict.get("video"):
        tutorial_dict["video"] = str(tutorial_dict["video"])

    # ✅ ensure image exists (thumbnail or upload)
    tutorial_dict["image"] = tutorial_dict.get("image", None)

    result = await tutorials_collection.insert_one(tutorial_dict)

    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Tutorial creation failed")

    return {
        "message": "Tutorial created successfully",
        "id": str(result.inserted_id)
    }

@router.get("/single/{tutorial_id}")
async def get_single_tutorial(tutorial_id: str):

    if not ObjectId.is_valid(tutorial_id):
        raise HTTPException(status_code=400, detail="Invalid tutorial ID")

    tutorial = await tutorials_collection.find_one(
        {"_id": ObjectId(tutorial_id)}
    )

    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    tutorial["_id"] = str(tutorial["_id"])

    if "created_at" in tutorial and isinstance(tutorial["created_at"], datetime):
        tutorial["created_at"] = tutorial["created_at"].strftime("%d %b %Y")

    return tutorial

@router.get("/all")
async def get_all_tutorials():
    tutorials = await tutorials_collection.find().sort("created_at", -1).to_list(100)

    for t in tutorials:
        t["_id"] = str(t["_id"])

        if isinstance(t.get("created_at"), datetime):
            t["created_at"] = t["created_at"].strftime("%d %b %Y")

    return tutorials

@router.get("/public")
async def get_public_tutorials():
    tutorials = await tutorials_collection.find(
        {"status": "Published"}
    ).sort("created_at", -1).to_list(length=100)

    for t in tutorials:
        t["_id"] = str(t["_id"])

        if isinstance(t.get("created_at"), datetime):
            t["created_at"] = t["created_at"].strftime("%d %b %Y")

    return tutorials


@router.put("/update/{tutorial_id}")
async def update_tutorial(tutorial_id: str, update: UpdateTutorial):

    if not ObjectId.is_valid(tutorial_id):
        raise HTTPException(status_code=400, detail="Invalid tutorial ID")

    tutorial_dict = {
        k: v for k, v in update.dict().items() if v is not None
    }

    if tutorial_dict.get("video"):
        tutorial_dict["video"] = str(tutorial_dict["video"])

    result = await tutorials_collection.update_one(
        {"_id": ObjectId(tutorial_id)},
        {"$set": tutorial_dict}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    return {"message": "Tutorial updated successfully"}

@router.delete("/delete/{tutorial_id}")
async def delete_tutorial(tutorial_id: str):

    if not ObjectId.is_valid(tutorial_id):
        raise HTTPException(status_code=400, detail="Invalid tutorial ID")

    result = await tutorials_collection.delete_one(
        {"_id": ObjectId(tutorial_id)}
    )

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    return {"message": "Tutorial deleted successfully"}