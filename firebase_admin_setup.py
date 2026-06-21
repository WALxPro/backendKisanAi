import os
import json
import firebase_admin
from firebase_admin import credentials

firebase_config = os.getenv("FIREBASE_CONFIG")

if not firebase_config:
    raise Exception("FIREBASE_CONFIG not found in environment variables")

cred_json = json.loads(firebase_config)

cred = credentials.Certificate(cred_json)

firebase_admin.initialize_app(cred)