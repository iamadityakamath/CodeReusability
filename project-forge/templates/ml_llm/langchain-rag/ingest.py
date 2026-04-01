from pathlib import Path

from config import DOCUMENTS_PATH


def ingest_documents() -> list[str]:
    docs = []
    for path in Path(DOCUMENTS_PATH).glob("*.txt"):
        docs.append(path.read_text(encoding="utf-8"))
    return docs


if __name__ == "__main__":
    docs = ingest_documents()
    print(f"Ingested {len(docs)} documents for {{project_name}}")
