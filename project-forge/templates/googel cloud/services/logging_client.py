import logging
import os

import google.cloud.logging


def setup_cloud_logging(project_id: str | None = None) -> logging.Logger:
    client = google.cloud.logging.Client(project=project_id or os.getenv("GOOGLE_CLOUD_PROJECT"))
    client.setup_logging()
    return logging.getLogger("gcp-app")
