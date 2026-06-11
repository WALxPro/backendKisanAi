from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime
from typing import Optional

from models.complain_models import ComplaintCreate, ComplaintStatusUpdate
from database import db

router = APIRouter()
col = db["complaints"]


def to_oid(id: str) -> ObjectId:
    try:
        return ObjectId(id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID")


def serialize(c: dict) -> dict:
    c["_id"] = str(c["_id"])
    for f in ("created_at", "updated_at"):
        if isinstance(c.get(f), datetime):
            c[f] = c[f].strftime("%d %b %Y, %I:%M %p")
    for step in c.get("timeline", []):
        if isinstance(step.get("date"), datetime):
            step["date"] = step["date"].strftime("%d %b %Y, %I:%M %p")
    return c


# ── FARMER ─────────────────────────────────────────

# Complaint submit
@router.post("/create", status_code=201)
async def create_complaint(body: ComplaintCreate):
    now = datetime.utcnow()
    doc = {
        **body.dict(),
        "status": "Pending",
        "note": None,
        "created_at": now,
        "updated_at": now,
        "timeline": [{"step": "Submitted", "date": now}],
    }
    result = await col.insert_one(doc)
    return {"message": "Complaint submitted", "id": str(result.inserted_id)}


# Farmer apni complaints dekhe
@router.get("/my/{farmer_id}")
async def my_complaints(farmer_id: str):
    complaints = (
        await col.find({"farmer_id": farmer_id})
        .sort("created_at", -1)
        .to_list(100)
    )
    return [serialize(c) for c in complaints]


# ── ADMIN ──────────────────────────────────────────

# Saari complaints (filter optional)
@router.get("/admin/all")
async def all_complaints(
    status: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
):
    query = {}
    if status:
        query["status"] = status
    if category:
        query["category"] = category

    total = await col.count_documents(query)
    results = (
        await col.find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
        .to_list(limit)
    )
    return {"total": total, "results": [serialize(c) for c in results]}


# Status + note update (admin)
@router.put("/admin/update/{complaint_id}")
async def update_complaint(complaint_id: str, body: ComplaintStatusUpdate):
    now = datetime.utcnow()
    timeline_step = {"step": body.status.value, "date": now}

    result = await col.update_one(
        {"_id": to_oid(complaint_id)},
        {
            "$set": {
                "status": body.status.value,
                "note": body.note,
                "updated_at": now,
            },
            "$push": {"timeline": timeline_step},
        },
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return {"message": "Updated successfully"}

@router.get("/admin/counts")
async def complaint_counts():
    pipeline = [
        {
            "$group": {
                "_id": "$farmer_id",
                "count": {"$sum": 1}
            }
        }
    ]

    results = await col.aggregate(pipeline).to_list(None)

    return {
        item["_id"]: item["count"]
        for item in results
    }