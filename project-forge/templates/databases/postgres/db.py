from __future__ import annotations

import os
from pathlib import Path
from typing import Any

def get_connection() -> Any:
    import psycopg  # type: ignore[import-not-found]

    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "app_db"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )


def init_schema() -> None:
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    sql = schema_path.read_text(encoding="utf-8")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()


def create_user(name: str, email: str, age: int) -> int:
    query = """
        INSERT INTO users (name, email, age)
        VALUES (%s, %s, %s)
        RETURNING id;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (name, email, age))
            user_id = cur.fetchone()[0]
        conn.commit()
    return user_id


def list_users(limit: int = 50) -> list[dict[str, Any]]:
    query = """
        SELECT id, name, email, age, created_at
        FROM users
        ORDER BY id DESC
        LIMIT %s;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (limit,))
            rows = cur.fetchall()

    users: list[dict[str, Any]] = []
    for row in rows:
        users.append(
            {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "age": row[3],
                "created_at": row[4].isoformat(),
            }
        )
    return users


def update_user_age(email: str, age: int) -> int:
    query = """
        UPDATE users
        SET age = %s
        WHERE email = %s;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (age, email))
            changed = cur.rowcount
        conn.commit()
    return changed


if __name__ == "__main__":
    init_schema()
    user_id = create_user("Alice", "alice@example.com", 28)
    print(f"Inserted user id: {user_id}")
    print("Users:", list_users())
    changed = update_user_age("alice@example.com", 29)
    print(f"Updated rows: {changed}")
