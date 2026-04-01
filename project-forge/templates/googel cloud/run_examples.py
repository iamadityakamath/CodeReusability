import os

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False

from services.bigquery_client import run_query
from services.cloud_sql_client import create_mysql_engine, test_connection
from services.firestore_client import get_document, set_document
from services.logging_client import setup_cloud_logging
from services.pubsub_client import publish_message
from services.secret_manager_client import access_secret
from services.storage_client import upload_file
from services.tasks_client import create_http_task


load_dotenv()


def demo_bigquery() -> None:
    rows = run_query("SELECT 1 AS ok")
    print("BigQuery:", rows)


def demo_firestore() -> None:
    collection = os.getenv("FIRESTORE_COLLECTION", "demo")
    set_document(collection, "sample-doc", {"hello": "world"})
    print("Firestore:", get_document(collection, "sample-doc"))


def demo_pubsub() -> None:
    topic = os.getenv("PUBSUB_TOPIC")
    if topic:
        message_id = publish_message(topic, "hello from project-forge")
        print("PubSub message id:", message_id)


def demo_secret_manager() -> None:
    secret_id = os.getenv("SECRET_ID")
    if secret_id:
        value = access_secret(secret_id)
        print("Secret length:", len(value))


def demo_storage() -> None:
    bucket = os.getenv("GCS_BUCKET")
    if bucket and os.path.exists("README.md"):
        upload_file(bucket, "README.md", "uploads/readme-copy.md")
        print("Uploaded README.md to GCS")


def demo_cloud_sql() -> None:
    if os.getenv("INSTANCE_CONNECTION_NAME"):
        engine = create_mysql_engine()
        print("Cloud SQL test:", test_connection(engine))


def demo_tasks() -> None:
    queue = os.getenv("TASKS_QUEUE")
    url = os.getenv("TASKS_URL")
    if queue and url:
        task_name = create_http_task(queue, url, {"event": "demo"}, delay_seconds=5)
        print("Task created:", task_name)


def demo_logging() -> None:
    logger = setup_cloud_logging()
    logger.info("Cloud Logging connected")
    print("Cloud Logging: message sent")


if __name__ == "__main__":
    demo_logging()
    demo_bigquery()
    demo_firestore()
    demo_pubsub()
    demo_secret_manager()
    demo_storage()
    demo_cloud_sql()
    demo_tasks()
