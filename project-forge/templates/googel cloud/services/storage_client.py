import os

from google.cloud import storage


def get_client(project_id: str | None = None) -> storage.Client:
    return storage.Client(project=project_id or os.getenv("GOOGLE_CLOUD_PROJECT"))


def upload_file(bucket_name: str, source_path: str, blob_name: str) -> None:
    client = get_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(source_path)


def download_file(bucket_name: str, blob_name: str, destination_path: str) -> None:
    client = get_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.download_to_filename(destination_path)
