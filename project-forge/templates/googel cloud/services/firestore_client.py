import os

from google.cloud import firestore


def get_client(project_id: str | None = None) -> firestore.Client:
    return firestore.Client(project=project_id or os.getenv("GOOGLE_CLOUD_PROJECT"))


def set_document(collection: str, doc_id: str, payload: dict) -> None:
    client = get_client()
    client.collection(collection).document(doc_id).set(payload)


def get_document(collection: str, doc_id: str) -> dict | None:
    client = get_client()
    snapshot = client.collection(collection).document(doc_id).get()
    if snapshot.exists:
        return snapshot.to_dict()
    return None
