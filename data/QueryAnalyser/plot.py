import json
import re
from pathlib import Path

import matplotlib.pyplot as plt

DATA_DIR = Path("data/QueryAnalyser")
INPUT_PATH = DATA_DIR / "accuracy_results.json"
OUTPUT_PATH = DATA_DIR / "accuracy_results.png"


def parse_size_billions(model_name: str) -> float:
    """Extract the parameter count in billions from a model name like 'qwen2.5-coder:7b'."""
    match = re.search(r":(\d+(?:\.\d+)?)b", model_name)
    if not match:
        raise ValueError(f"Could not parse model size from '{model_name}'")
    return float(match.group(1))


def load_records(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    records = []
    for entry in raw:
        # each entry is a single-key dict: {model_name: {tier_file: score, ...}}
        model_name, scores = next(iter(entry.items()))
        records.append(
            {
                "model": model_name,
                "size_b": parse_size_billions(model_name),
                "tier3": scores.get("prompts_tier3.csv"),
                "tier8": scores.get("prompts_tier8.csv"),
            }
        )
    return records


def main() -> None:
    records = load_records(INPUT_PATH)
    records.sort(key=lambda r: r["size_b"])

    models = [r["model"] for r in records]
    sizes = [r["size_b"] for r in records]
    tier3 = [r["tier3"] for r in records]
    tier8 = [r["tier8"] for r in records]

    fig, (ax_bar, ax_line) = plt.subplots(2, 1, figsize=(11, 10))

    # Bar chart: models as categories, ordered by size, tier3 vs tier8 side by side
    x_positions = range(len(models))
    bar_width = 0.35

    ax_bar.bar(
        [x - bar_width / 2 for x in x_positions],
        tier3,
        width=bar_width,
        label="tier3",
        color="#4C72B0",
    )
    ax_bar.bar(
        [x + bar_width / 2 for x in x_positions],
        tier8,
        width=bar_width,
        label="tier8",
        color="#DD8452",
    )
    ax_bar.set_xticks(list(x_positions))
    ax_bar.set_xticklabels(
        [f"{m}\n({s}b)" for m, s in zip(models, sizes)], rotation=45, ha="right"
    )
    ax_bar.set_ylabel("Accuracy")
    ax_bar.set_title("Accuracy by model, ordered by parameter size")
    ax_bar.legend()
    ax_bar.grid(axis="y", alpha=0.3)

    # Line chart: true numeric size axis, to see scaling trend
    ax_line.plot(sizes, tier3, marker="o", label="tier3", color="#4C72B0")
    ax_line.plot(sizes, tier8, marker="o", label="tier8", color="#DD8452")

    for x, y, name in zip(sizes, tier3, models):
        ax_line.annotate(
            name, (x, y), textcoords="offset points", xytext=(0, 8), fontsize=7, alpha=0.8
        )

    ax_line.set_xlabel("Model size (billions of parameters)")
    ax_line.set_ylabel("Accuracy")
    ax_line.set_title("Accuracy vs model size")
    ax_line.legend()
    ax_line.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(OUTPUT_PATH, dpi=150)
    print(f"Saved plot to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()