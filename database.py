
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
# client = AsyncIOMotorClient(MONGO_URL)
# MONGO_URL = "mongodb+srv://waleedsheikh15486_db_user:wwaallee@kisanai.csr1dce.mongodb.net/?appName=KISANAI"
client = AsyncIOMotorClient(MONGO_URL)
db = client.Kisan_database

