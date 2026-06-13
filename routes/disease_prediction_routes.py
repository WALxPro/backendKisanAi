from fastapi import APIRouter, HTTPException, File, Form, Query, UploadFile
from database import db
from utils.disease import handle_prediction
from utils.leaf_detection import LeafValidationError

router = APIRouter()


def _serialize_prediction(prediction: dict) -> dict:
    if prediction is None:
        return prediction
    prediction = prediction.copy()
    if "_id" in prediction:
        prediction["_id"] = str(prediction["_id"])
    return prediction


@router.post("/predict")
async def predict_disease(
    image: UploadFile = File(...),
    farmer_id: str = Form(...),
    user_email: str | None = Form(default=None),
    image_name: str | None = Form(default=None),
    
):
    try:
        if image.content_type and not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Uploaded file must be an image")

        image_bytes = await image.read()

        result = await handle_prediction(
            image_bytes=image_bytes,
            farmer_id=farmer_id,
            user_email=user_email,
            image_name=image_name or image.filename,
            db=db,
        )

        return result

    except LeafValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(exc)}") from exc


@router.get("/all")
async def get_all_scans(farmer_id: str | None = Query(default=None)):
    try:
        query = {}
        if farmer_id:
            query["farmer_id"] = farmer_id

        scans = await db.disease_predictions.find(query).sort("createdAt", -1).to_list(length=200)
        return [_serialize_prediction(scan) for scan in scans]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve scans: {str(exc)}") from exc


@router.get("/user/{farmer_id}")
async def get_user_scans(farmer_id: str):
    try:
        scans = await db.disease_predictions.find({"farmer_id": farmer_id}).sort("createdAt", -1).to_list(length=200)
        return [_serialize_prediction(scan) for scan in scans]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user scans: {str(exc)}") from exc