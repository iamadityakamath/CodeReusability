import os

from google.cloud import bigquery


def get_client(project_id: str | None = None) -> bigquery.Client:
    return bigquery.Client(project=project_id or os.getenv("GOOGLE_CLOUD_PROJECT"))


def run_query(sql: str, project_id: str | None = None) -> list[dict]:
    client = get_client(project_id)
    rows = client.query(sql).result()
    return [dict(row.items()) for row in rows]


def insert_json_rows(dataset: str, table: str, rows: list[dict], project_id: str | None = None) -> list[dict]:
    client = get_client(project_id)
    table_ref = f"{client.project}.{dataset}.{table}"
    errors = client.insert_rows_json(table_ref, rows)
    return errors
