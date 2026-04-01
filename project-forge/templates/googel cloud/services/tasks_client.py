import datetime
import json
import os

from google.cloud import tasks_v2


def get_client() -> tasks_v2.CloudTasksClient:
    return tasks_v2.CloudTasksClient()


def create_http_task(queue_id: str, url: str, payload: dict, delay_seconds: int = 0) -> str:
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    if not project:
        raise ValueError("GOOGLE_CLOUD_PROJECT is required")

    client = get_client()
    parent = client.queue_path(project, location, queue_id)

    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": url,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(payload).encode(),
        }
    }

    if delay_seconds > 0:
        schedule_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=delay_seconds)
        task["schedule_time"] = schedule_time

    response = client.create_task(request={"parent": parent, "task": task})
    return response.name
