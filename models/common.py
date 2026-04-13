from bson import ObjectId

def serialize_doc(doc):
    doc["_id"] = str(doc["_id"])  # ObjectId ko string me convert
    return doc