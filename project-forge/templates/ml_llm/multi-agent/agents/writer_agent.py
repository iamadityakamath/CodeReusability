def write(notes: str, memory) -> str:
    summary = f"Final response from notes: {notes}"
    memory.set("summary", summary)
    return summary
