def research(task: str, memory) -> str:
    note = f"Research findings for: {task}"
    memory.set("research", note)
    return note
