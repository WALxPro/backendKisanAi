from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from routes.admin_routes import router as admin_router
from routes.farmer_routes import router as farmer_router
from routes.ads_routes import router as ads_router
from routes.blog_routes import router as blog_router
from routes.complain_routes import router as complain_router
from routes.crop_assistant_routes import router as crop_assistant_router
from routes.notification_routes  import router as notification_router
from routes.disease_prediction_routes import router as disease_prediction_router
from routes.disease_chat_routes import router as disease_chat_router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()
from database import db

app.include_router(admin_router, prefix="/admin", tags=["Admin"])
app.include_router(farmer_router, prefix="/farmers", tags=["Farmers"])
app.include_router(ads_router, prefix="/ads", tags=["Ads"])
app.include_router(blog_router, prefix="/blogs", tags=["Blogs"])
app.include_router(complain_router, prefix="/complain", tags=["Complain"])
app.include_router(crop_assistant_router, prefix="/assistant", tags=["Crop Assistant"])
app.include_router(notification_router, prefix="/notifications", tags=["Notifications"])
app.include_router(disease_prediction_router, prefix="/disease", tags=["Disease Prediction"])
app.include_router(disease_chat_router, prefix="/disease-chat", tags=["Disease Chat"])



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ANY frontend can connect
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    user_id = websocket.query_params.get("user_id")
    await manager.connect(websocket, user_id=user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Optional: handle messages from client
            print("WS message from client:", data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

@app.get("/test-db")
async def test_db():
    try:
        collections = await db.list_collection_names()
        return {"status": "connected", "collections": collections}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@app.get("/")
def root():
    return {"status": "Admin Backend Running"}
