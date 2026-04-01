from retriever import retrieve


def run_rag(query: str) -> str:
    result = retrieve(query)
    return f"Answer based on: {result['context']}"


if __name__ == "__main__":
    print(run_rag("What is project forge?"))
