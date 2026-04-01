from agents.research_agent import research
from agents.writer_agent import write
from memory import SharedMemory


def run_graph(task: str) -> str:
    memory = SharedMemory()
    notes = research(task, memory)
    return write(notes, memory)


if __name__ == "__main__":
    print(run_graph("Design plan for {{project_name}}"))
