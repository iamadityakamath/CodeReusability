from dataset import load_dataset


def train() -> None:
    rows = load_dataset("data/train.jsonl")
    print(f"Training rows: {len(rows)} for {{project_name}}")


if __name__ == "__main__":
    train()
