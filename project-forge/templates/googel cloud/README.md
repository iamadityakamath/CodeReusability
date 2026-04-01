# Google Cloud Python Service Templates

This folder contains ready-to-use Python examples for major Google Cloud services.

## Services Included

- BigQuery
- Cloud Storage
- Pub/Sub
- Secret Manager
- Firestore
- Cloud SQL (MySQL via Cloud SQL Python Connector)
- Cloud Logging
- Cloud Tasks

## Setup

1. Create and activate a Python virtual environment.
2. Install dependencies:
   pip install -r requirements.txt
3. Copy environment file:
   cp .env.example .env
4. Set values in .env, especially GOOGLE_CLOUD_PROJECT and credentials.

## Authentication

These examples use Application Default Credentials.

- Local service account key method:
  export GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/service-account.json
- Or use gcloud user credentials:
  gcloud auth application-default login

## Files

- services/bigquery_client.py
- services/storage_client.py
- services/pubsub_client.py
- services/secret_manager_client.py
- services/firestore_client.py
- services/cloud_sql_client.py
- services/logging_client.py
- services/tasks_client.py
- run_examples.py

## Quick Test

python run_examples.py

Only configured services will run successfully; some demos skip if required env vars are missing.
