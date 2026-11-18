import json
import sys, os
import textwrap
from collections import Counter
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.use("Agg")  # no display needed, we only save files
OUTPUT_DIR = Path(os.path.dirname(__file__)) / "analysis"
MAX_BARS = 30  # plots show the top N categories; summary.json keeps all of them


def load_records(path):
    """Read the JSON file and return the list of case dictionaries."""
    with open(path) as f:
        return list(json.load(f).values())


def collect_values(records):
    """Return {key: [value for every record]}, with None where a record lacks the key."""
    keys = dict.fromkeys(key for record in records for key in record)
    return {key: [record.get(key) for record in records] for key in keys}


def kind_of(value):
    """Classify a single value. bool is checked first because bool is a subclass of int."""
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "numeric"
    if isinstance(value, list):
        return "list"
    return "text"


def detect_type(values):
    """Classify a key from its non-null values. Mixed types fall back to text."""
    kinds = {kind_of(v) for v in values if v is not None}
    if not kinds:
        return "empty"
    return kinds.pop() if len(kinds) == 1 else "text"


def count_bool(values):
    """Count how many True and how many False."""
    trues = sum(values)
    return {"True": trues, "False": len(values) - trues}


def count_text(values):
    """Count each unique value, most common first."""
    return dict(Counter(str(v) for v in values).most_common())


def count_list_items(values):
    """Count each unique item across all the lists, most common first."""
    return dict(Counter(str(item) for v in values for item in v).most_common())


def summarise_numeric(values):
    """Five-number summary plus mean and standard deviation."""
    data = np.array(values, dtype=float)
    q1, median, q3 = np.percentile(data, [25, 50, 75])
    stats = {
        "min": data.min(),
        "q1": q1,
        "median": median,
        "q3": q3,
        "max": data.max(),
        "mean": data.mean(),
        "std": data.std(ddof=1) if len(data) > 1 else 0.0,
    }
    return {name: round(float(value), 3) for name, value in stats.items()}


def plot_counts(counts, title, path):
    """Horizontal bar chart, most common category at the top."""
    items = list(counts.items())[:MAX_BARS][::-1]
    labels = [textwrap.fill(label, 40) for label, _ in items]
    heights = [count for _, count in items]

    fig, ax = plt.subplots(figsize=(9, max(2.5, 0.45 * len(items) + 1)))
    bars = ax.barh(labels, heights)
    ax.bar_label(bars, padding=3)
    ax.set_xlabel("Cases")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_box(values, title, path):
    """Box plot of a numeric key, with the mean marked."""
    fig, ax = plt.subplots(figsize=(3.5, 5))
    ax.boxplot(values, showmeans=True)
    ax.set_xticks([])
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_summary(summary, path):
    """Write the full summary as JSON."""
    with open(path, "w") as f:
        json.dump(summary, f, indent=2)


def print_entry(key, entry):
    """Print one key's summary to the console."""
    print(f"\n{key}  [{entry['type']}]  present={entry['present']}  missing={entry['missing']}")
    for name, value in entry.get("counts", entry.get("stats", {})).items():
        print(f"    {name}: {value}")


def analyse(path):
    """Run the whole analysis. Remove any step below that you do not need."""
    records = load_records(path)
    columns = collect_values(records)

    plots_dir = OUTPUT_DIR / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    summary = {"total_records": len(records), "keys": {}}

    for key, values in columns.items():
        present = [v for v in values if v is not None]
        kind = detect_type(values)
        entry = {"type": kind, "present": len(present), "missing": len(values) - len(present)}
        plot_path = plots_dir / f"{key}.png"
        title = f"{key} (n={len(present)})"

        if kind == "bool":
            entry["counts"] = count_bool(present)
            plot_counts(entry["counts"], title, plot_path)
        elif kind == "numeric":
            entry["stats"] = summarise_numeric(present)
            plot_box(present, title, plot_path)
        elif kind == "text":
            entry["counts"] = count_text(present)
            plot_counts(entry["counts"], title, plot_path)
        elif kind == "list":
            entry["counts"] = count_list_items(present)
            plot_counts(entry["counts"], title, plot_path)

        summary["keys"][key] = entry
        print_entry(key, entry)

    save_summary(summary, OUTPUT_DIR / "summary.json")
    print(f"\n{len(records)} records, {len(columns)} keys. Saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    analyse("Agents/data/metadata/90_OT_Reference_Summaries_metadata.json")