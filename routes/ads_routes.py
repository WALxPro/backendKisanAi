from fastapi import APIRouter, HTTPException
from models.ads_models import Ad, UpdateAd
from datetime import datetime
from database import db
from bson import ObjectId

router = APIRouter()
ads_collection = db["ads"]


# CREATE
@router.post("/create")
async def create_ad(ad: Ad):
    ad_dict = ad.dict()
    ad_dict["created_at"] = datetime.utcnow()
    ad_dict["image"] = str(ad_dict["image"])  # HttpUrl -> string

    result = await ads_collection.insert_one(ad_dict)
    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Ad creation failed")

    return {"message": "Ad created successfully", "id": str(result.inserted_id)}


# READ ALL
@router.get("/all")
async def get_all_ads():
    ads = await ads_collection.find().sort("created_at", -1).to_list(length=100)
    for ad in ads:
        ad["_id"] = str(ad["_id"])
        if "created_at" in ad and isinstance(ad["created_at"], datetime):
            ad["created_at"] = ad["created_at"].strftime("%d %b %Y")  # 10 Mar 2026
    return ads


# UPDATE
@router.put("/update/{ad_id}")
async def update_ad(ad_id: str, update: UpdateAd):
    ad_dict = {k: v for k, v in update.dict().items() if v is not None}
    if "image" in ad_dict:
        ad_dict["image"] = str(ad_dict["image"])

    result = await ads_collection.update_one(
        {"_id": ObjectId(ad_id)}, {"$set": ad_dict}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Ad not found or no changes")
    return {"message": "Ad updated successfully"}


# DELETE
@router.delete("/delete/{ad_id}")
async def delete_ad(ad_id: str):
    result = await ads_collection.delete_one({"_id": ObjectId(ad_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Ad not found")
    return {"message": "Ad deleted successfully"}