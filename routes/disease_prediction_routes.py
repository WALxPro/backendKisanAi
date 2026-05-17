from fastapi import APIRouter, HTTPException, File, Form, UploadFile
from database import db
from utils.disease import handle_prediction
from utils.leaf_detection import LeafValidationError

router = APIRouter()


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