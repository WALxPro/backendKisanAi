from fastapi import APIRouter, HTTPException
from models.complain_models import ComplaintCreate, TimelineStep
from datetime import datetime
from database import db
from bson import ObjectId

router = APIRouter()
complaints_collection = db["complaints"]

# CREATE Complaint
@router.post("/create")
async def create_complaint(complaint: ComplaintCreate):
    complaint_dict = complaint.dict()
    complaint_dict["status"] = "Pending"
    complaint_dict["created_at"] = datetime.utcnow()
    complaint_dict["updated_at"] = datetime.utcnow()
    complaint_dict["timeline"] = [{"step": "Submitted", "done": True, "date": datetime.utcnow()}]

    result = await complaints_collection.insert_one(complaint_dict)
    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Complaint creation failed")
    return {"message": "Complaint created successfully", "id": str(result.inserted_id)}


# READ ALL Complaints (optional filter: farmer_id or status)
@router.get("/all")
async def get_all_complaints(farmer_id: str = None, status: str = None):
    query = {}
    if farmer_id:
        query["farmer_id"] = farmer_id
    if status:
        query["status"] = status

    complaints = await complaints_collection.find(query).sort("created_at", -1).to_list(length=100)
    for c in complaints:
        c["_id"] = str(c["_id"])
        if "created_at" in c and isinstance(c["created_at"], datetime):
            c["created_at"] = c["created_at"].strftime("%d %b %Y")
        if "updated_at" in c and isinstance(c["updated_at"], datetime):
            c["updated_at"] = c["updated_at"].strftime("%d %b %Y")
    return complaints


# GET single complaint by ID
@router.get("/{complaint_id}")
async def get_complaint(complaint_id: str):
    complaint = await complaints_collection.find_one({"_id": ObjectId(complaint_id)})
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    complaint["_id"] = str(complaint["_id"])
    return complaint


# UPDATE Complaint (status or add timeline step)
@router.put("/update/{complaint_id}")
async def update_complaint(
    complaint_id: str,
    status: str = None,
    timeline_step: TimelineStep = None
):
    update_data = {}
    if status:
        update_data["status"] = status
    if timeline_step:
        update_data["timeline"] = {"$push": timeline_step.dict()}
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    update_data["updated_at"] = datetime.utcnow()
    result = await complaints_collection.update_one(
        {"_id": ObjectId(complaint_id)},
        {"$set": {k: v for k, v in update_data.items() if k != "timeline"},
         "$push": {"timeline": timeline_step.dict()} if timeline_step else {}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return {"message": "Complaint updated successfully"}


# DELETE Complaint
@router.delete("/delete/{complaint_id}")
async def delete_complaint(complaint_id: str):
    result = await complaints_collection.delete_one({"_id": ObjectId(complaint_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return {"message": "Complaint deleted successfully"}