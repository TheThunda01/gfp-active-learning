"""Draw the archived GFP shortlist comparison. Run from any working directory."""
import argparse
import csv
from math import ceil, floor, isfinite, log10
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter

HERE = Path(__file__).resolve().parent
INK = "#192f34"
TEAL = "#086962"
RUST = "#9d4a23"
MUTED = "#465a61"
PALE = "#dce6e3"
RULE = "#a8b7b7"
PAPER = "#fcfbf7"
WIDTH = 6.25


def canvas(height):
    return plt.figure(figsize=(WIDTH, height), facecolor=PAPER, layout=None)


def write(fig, x, y, words, size=14, color=INK, **kwargs):
    return fig.text(x, y, words, size=size, color=color, va="center", **kwargs)


def export(fig, path):
    fig.savefig(path, dpi=200, facecolor=PAPER, metadata={
        "Title": path.stem.replace("-", " "),
        "Source": "Retrospective GFP benchmark, experiments/shortlist_review/results/seed_comparison.csv",
        "Description": (
            "Summary of archived model comparisons on GFP log-brightness data adapted from "
            "Sarkisyan et al. (2016), https://doi.org/10.6084/m9.figshare.3102154.v1, "
            "CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)."
        ),
    })
    plt.close(fig)


def shared_counts(rows, field):
    values = {int(row[field]) for row in rows}
    if len(values) != 1:
        raise ValueError(f"The diagram needs a shared {field} across all four runs")
    return values.pop()


def diagram(rows, output):
    initial = shared_counts(rows, "initial_labels")
    available = shared_counts(rows, "available_records")
    shortlist = shared_counts(rows, "shortlist_size")
    batch = shared_counts(rows, "diversity_batch_size")
    fig = canvas(4.65)
    write(fig, .055, .91, "Which records did the two rules share?", 18, weight="bold")
    write(fig, .055, .805, f"Each run starts with {initial} known measurements", 14)
    write(fig, .055, .745, f"and {available:,} available GFP records.", 14)
    ax = fig.add_axes([0, 0, 1, 1], frameon=False)
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    # Both branches start from the same pool within a seed.
    ax.plot([.5, .5], [.685, .65], color=RULE)
    ax.plot([.267, .735], [.65, .65], color=RULE)
    for x in (.267, .735):
        ax.annotate("", xy=(x, .586), xytext=(x, .657),
                    arrowprops={"arrowstyle": "-|>", "color": MUTED, "lw": 1.1})
    for left, label, value, meaning, color in [
        (.055, "Combined rule", shortlist, "records on the\nuncertainty shortlist", TEAL),
        (.523, "Diversity-only rule", batch, "records in the\nfirst chosen batch", INK),
    ]:
        box = FancyBboxPatch((left, .273), .425, .31,
                             boxstyle="round,pad=0.004,rounding_size=0.009",
                             facecolor="#f0f4ef", edgecolor=RULE)
        ax.add_patch(box)
        write(fig, left + .025, .528, label, 13, weight="bold", color=color)
        write(fig, left + .025, .44, f"{value:,}", 23, weight="bold", color=color)
        write(fig, left + .025, .338, meaning, 12.5, color=MUTED, linespacing=1.17)
    write(fig, .055, .168, "Count how many first-batch choices made the shortlist.", 13,
          weight="bold")
    write(fig, .055, .084, "The shortlist is an intermediate step for the combined rule.", 12, color=MUTED)
    export(fig, output / "shortlist-path.png")


def retention(rows, output):
    fig = canvas(3.65)
    batch = shared_counts(rows, "diversity_batch_size")
    write(fig, .055, .90, "Which choices reached the shortlist?", 18, weight="bold")
    write(fig, .055, .765, f"Of {batch} diversity-only choices, the dark segment shows", 13)
    write(fig, .055, .695, "how many appeared on the combined rule’s shortlist.", 13)
    ax = fig.add_axes([.21, .12, .55, .48], facecolor=PAPER)
    for i, row in enumerate(rows):
        retained, excluded = row["diversity_retained"], row["diversity_excluded"]
        if retained == excluded == "":
            ax.text(0, i, "Shortlist reconstruction unverified", va="center",
                    fontsize=12.5, color=MUTED, style="italic")
            continue
        n, m = int(retained), int(excluded)
        if n < 0 or m < 0 or n + m != batch:
            raise ValueError("Retention counts must sum to the diversity batch size")
        ax.barh(i, n, height=.54, color=TEAL)
        ax.barh(i, m, height=.54, left=n, color=PALE)
        ax.text(batch + 2, i, f"{n} of {batch}", fontsize=13, va="center",
                color=INK, weight="bold", clip_on=False)
    ax.set(xlim=(0, batch), ylim=(len(rows)-.47, -.53), xticks=[])
    ax.set_yticks(range(len(rows)), [f"Seed {r['seed']}" for r in rows], fontsize=13, color=INK)
    ax.tick_params(axis="y", length=0, pad=8)
    ax.spines[:].set_visible(False)
    export(fig, output / "shortlist-retention.png")


def next_step(rows, output):
    fig = canvas(4.65)
    budget = shared_counts(rows, "initial_labels") + shared_counts(rows, "diversity_batch_size")
    write(fig, .055, .923, "Which rule had lower prediction error?", 18, weight="bold")
    write(fig, .055, .823, f"At {budget} labels, compare combined minus diversity-only", 13)
    write(fig, .055, .762, "root mean squared error (RMSE) in log-brightness units.", 13)
    series = [[float(row[f"{role}_rmse_gap_{budget}"]) for row in rows]
              for role in ("local", "distant")]
    if not all(isfinite(v) for group in series for v in group):
        raise ValueError("Each seed needs both finite error contrasts")
    extreme = max(abs(v) for group in series for v in group)
    if extreme:
        step = 10 ** floor(log10(extreme))
        limit = ceil(extreme / step) * step
    else:
        limit = .01
    for j, (values, heading, color, marker) in enumerate(zip(
            series, ("Local variants", "Distant variants"), (TEAL, RUST), ("o", "s"))):
        ax = fig.add_axes([.193 + .42*j, .275, .30, .317], facecolor=PAPER)
        ax.set_title(heading, size=14, color=INK, weight="bold", pad=13)
        ax.axvline(0, color=MUTED, lw=1)
        for i, value in enumerate(values):
            ax.plot([0, value], [i, i], lw=2.0, color=color, solid_capstyle="round")
            ax.plot(value, i, marker=marker, color=color, markersize=7.2)
            # Keep signed labels inside each panel, including gaps close to zero.
            left_label = value < 0 or value > limit * .55
            if value < -limit * .55:
                left_label = False
            gap_label = f"{value:+.3f}".replace("-", "−") if value else "0.000"
            ax.annotate(gap_label, (value, i), xytext=(-6 if left_label else 6, 0),
                        textcoords="offset points", ha="right" if left_label else "left",
                        va="center", size=10.8, color=INK,
                        bbox={"facecolor": PAPER, "edgecolor": "none", "pad": .35})
        ax.set(xlim=(-limit*1.15, limit*1.15), ylim=(len(rows)-.48, -.52),
               xticks=[-limit, 0, limit])
        ax.set_yticks(range(len(rows)), [f"Seed {r['seed']}" for r in rows] if j == 0 else [""]*len(rows),
                      size=12.5, color=INK)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:+g}".replace("-", "−") if v else "0"))
        ax.tick_params(axis="x", labelsize=11.6, colors=MUTED, length=3)
        ax.tick_params(axis="y", length=0, pad=6)
        ax.spines[["right", "left", "top"]].set_visible(False)
        ax.spines["bottom"].set_color(RULE)
    write(fig, .055, .132, "Values left of zero favor the combined rule.", 12.5, color=MUTED)
    write(fig, .055, .068, "Values right of zero favor the diversity-only rule.", 12.5, color=MUTED)
    export(fig, output / "next-step-errors.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=HERE / "results" / "seed_comparison.csv")
    parser.add_argument("--output", type=Path, default=HERE / "figures")
    args = parser.parse_args()
    with args.input.open(encoding="utf-8", newline="") as f:
        rows = sorted(csv.DictReader(f), key=lambda r: int(r["seed"]))
    if [int(r["seed"]) for r in rows] != [11, 29, 47, 83]:
        raise ValueError("Expected one row per archived seed (11, 29, 47, 83)")
    args.output.mkdir(exist_ok=True, parents=True)
    diagram(rows, args.output)
    retention(rows, args.output)
    next_step(rows, args.output)


if __name__ == "__main__":
    main()
