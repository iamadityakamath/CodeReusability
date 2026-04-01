from __future__ import annotations

import os
from typing import Any


def get_collection() -> Any:
    from pymongo import MongoClient  # type: ignore[import-not-found]

    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB", "app_db")
    collection_name = os.getenv("MONGODB_COLLECTION", "users")

    client = MongoClient(uri)
    db = client[db_name]
    return db[collection_name]


def create_user(name: str, email: str, age: int) -> str:
    collection = get_collection()
    doc = {"name": name, "email": email, "age": age}
    result = collection.insert_one(doc)
    return str(result.inserted_id)


def list_users(limit: int = 50) -> list[dict[str, Any]]:
    collection = get_collection()
    users = list(collection.find({}, {"_id": 0}).limit(limit))
    return users


def update_user_age(email: str, age: int) -> int:
    collection = get_collection()
    result = collection.update_one({"email": email}, {"$set": {"age": age}})
    return result.modified_count


if __name__ == "__main__":
    user_id = create_user("Alice", "alice@example.com", 28)
    print(f"Inserted user id: {user_id}")
    print("Users:", list_users())
    changed = update_user_age("alice@example.com", 29)
    print(f"Updated rows: {changed}")
