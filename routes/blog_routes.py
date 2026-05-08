from fastapi import APIRouter, HTTPException
from models.blog_models import Blog, UpdateBlog
from datetime import datetime
from database import db
from bson import ObjectId

router = APIRouter()
blogs_collection = db["blogs"]

# CREATE
@router.post("/create")
async def create_blog(blog: Blog):
    blog_dict = blog.dict()
    blog_dict["created_at"] = datetime.utcnow()
    blog_dict["image"] = str(blog_dict["image"])

    result = await blogs_collection.insert_one(blog_dict)

    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Blog creation failed")

    return {
        "message": "Blog created successfully",
        "id": str(result.inserted_id)
    }

# ADMIN - ALL BLOGS (draft + published)
@router.get("/all")
async def get_all_blogs():
    blogs = await blogs_collection.find().sort("created_at", -1).to_list(length=100)

    for blog in blogs:
        blog["_id"] = str(blog["_id"])

        if "created_at" in blog and isinstance(blog["created_at"], datetime):
            blog["created_at"] = blog["created_at"].strftime("%d %b %Y")

    return blogs

# PUBLIC - ONLY PUBLISHED (mobile app)
@router.get("/public")
async def get_public_blogs():
    blogs = await blogs_collection.find(
        {"status": "Published"}
    ).sort("created_at", -1).to_list(length=100)

    for blog in blogs:
        blog["_id"] = str(blog["_id"])

        if "created_at" in blog and isinstance(blog["created_at"], datetime):
            blog["created_at"] = blog["created_at"].strftime("%d %b %Y")

    return blogs

# UPDATE
@router.put("/update/{blog_id}")
async def update_blog(blog_id: str, update: UpdateBlog):
    blog_dict = {k: v for k, v in update.dict().items() if v is not None}

    if "image" in blog_dict:
        blog_dict["image"] = str(blog_dict["image"])

    result = await blogs_collection.update_one(
        {"_id": ObjectId(blog_id)},
        {"$set": blog_dict}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Blog not found or no changes")

    return {"message": "Blog updated successfully"}

# DELETE
@router.delete("/delete/{blog_id}")
async def delete_blog(blog_id: str):
    result = await blogs_collection.delete_one({"_id": ObjectId(blog_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Blog not found")

    return {"message": "Blog deleted successfully"}

# SINGLE
@router.get("/single/{blog_id}")
async def get_single_blog(blog_id: str):
    blog = await blogs_collection.find_one({"_id": ObjectId(blog_id)})

    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    blog["_id"] = str(blog["_id"])

    if "created_at" in blog and isinstance(blog["created_at"], datetime):
        blog["created_at"] = blog["created_at"].strftime("%d %b %Y")

    return blog