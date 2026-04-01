import os

VECTOR_STORE = os.getenv("VECTOR_STORE", "chroma")
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DOCUMENTS_PATH = os.getenv("DOCUMENTS_PATH", "./data")
