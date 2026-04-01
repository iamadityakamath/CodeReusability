import os
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from sqlalchemy import create_engine


def create_mysql_engine() -> Engine:
    try:
        from google.cloud.sql.connector import Connector  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "google-cloud-sql-connector is required. Install with: pip install google-cloud-sql-connector[pymysql]"
        ) from exc

    instance_connection_name = os.getenv("INSTANCE_CONNECTION_NAME")
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS")
    db_name = os.getenv("DB_NAME")

    if not all([instance_connection_name, db_user, db_pass, db_name]):
        raise ValueError("INSTANCE_CONNECTION_NAME, DB_USER, DB_PASS, and DB_NAME are required")

    connector = Connector()

    def getconn() -> Any:
        return connector.connect(
            instance_connection_name,
            "pymysql",
            user=db_user,
            password=db_pass,
            db=db_name,
            ip_type="PUBLIC",
        )

    engine = create_engine(
        "mysql+pymysql://",
        creator=getconn,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=2,
    )
    return engine


def test_connection(engine: Engine) -> int:
    with engine.connect() as conn:
        return conn.execute(text("SELECT 1")).scalar_one()
