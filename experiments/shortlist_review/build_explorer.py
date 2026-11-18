"""Build the standalone four-policy explorer from two archived result tables."""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "uncertainty_ablation" / "results"
REPORT = "https://github.com/TheThunda01/gfp-active-learning/blob/main/experiments/shortlist_review/README.md"
SOURCE = "https://github.com/TheThunda01/gfp-active-learning/blob/4b27c32047288e32a647e2e8b411f3b272d6113c/experiments/uncertainty_ablation/results"
POLICIES = {
    "random": "Random", "uncertainty_only": "Uncertainty only",
    "diversity_only": "Diversity only", "combined": "Combined",
}
SETS = {"local_test": ("Local", 400), "distant_test": ("Distant", 800)}
SEEDS = (11, 29, 47, 83)
BUDGET = 384


def load(directory: Path) -> tuple[dict, dict]:
    """Check the final-budget grid and each archived contrast against paired errors."""
    scores = {}
    with (directory / "learning_curves.csv").open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if int(row["label_budget"]) != BUDGET:
                continue
            key = (int(row["seed"]), row["evaluation"], row["policy"])
            if key in scores or key[1] not in SETS or int(row["n_evaluation"]) != SETS[key[1]][1]:
                raise ValueError(f"Invalid or duplicate evaluation {key}")
            score = float(row["rmse"])
            if not math.isfinite(score) or score < 0:
                raise ValueError(f"Invalid RMSE for {key}")
            scores[key] = score
    if set(scores) != {(s, e, p) for s in SEEDS for e in SETS for p in POLICIES}:
        raise ValueError("Expected four policies, four seeds and both evaluation sets at 384 labels")

    contrasts = {}
    with (directory / "distance_benefit_contrast.csv").open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            seed = int(row["seed"])
            if seed in contrasts or seed not in SEEDS:
                raise ValueError(f"Invalid or duplicate contrast for seed {seed}")
            local, distant = (scores[seed, e, "random"] - scores[seed, e, "combined"] for e in SETS)
            expected = (local, distant, distant - local)
            saved = tuple(float(row[c]) for c in ("local_benefit", "distant_benefit", "distant_minus_local_benefit"))
            if not all(math.isclose(a, b, abs_tol=1e-12) for a, b in zip(expected, saved)):
                raise ValueError(f"Saved contrast disagrees with paired errors for seed {seed}")
            contrasts[seed] = saved
    if set(contrasts) != set(SEEDS):
        raise ValueError("Expected four paired contrasts")
    return scores, contrasts


def signed(value: float) -> str:
    return f"{value:+.4f}".replace("-", "−")


def strip_rows(scores: dict, selection: str | int, evaluation: str, low: float, high: float) -> str:
    seeds = SEEDS if selection == "mean" else [selection]
    values = {p: mean(scores[s, evaluation, p] for s in seeds) for p in POLICIES}
    def position(value: float) -> float:
        return 100 * (value - low) / (high - low)
    rows = []
    for policy, label in POLICIES.items():
        value = values[policy]
        rows.append(
            f'<tr><th scope="row">{label}</th><td class="plotcell"><div aria-hidden="true" class="track" '
            f'style="--reference:{position(values["random"]):.5f}%;--point:{position(value):.5f}%">'
            f'<i class="mark {policy}"></i></div></td><td class="number">{value:.4f}</td></tr>'
        )
    return "".join(rows)


def shortlist_table(comparison: Path, directory: Path) -> tuple[str, str]:
    """Publish only verified counts and check first-batch gaps against the source scores."""
    batch_scores = {}
    with (directory / "learning_curves.csv").open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            if int(row["label_budget"]) != 128 or row["policy"] not in ("combined", "diversity_only"):
                continue
            key = (int(row["seed"]), row["evaluation"], row["policy"])
            if key in batch_scores:
                raise ValueError(f"Duplicate first-batch score {key}")
            batch_scores[key] = float(row["rmse"])
    expected = {(s, e, p) for s in SEEDS for e in SETS for p in ("combined", "diversity_only")}
    if set(batch_scores) != expected:
        raise ValueError("Incomplete first-batch error grid")
    rows = {}
    retained_counts, shared_counts = [], []
    with comparison.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            seed = int(row["seed"])
            if seed not in SEEDS or seed in rows:
                raise ValueError(f"Invalid or duplicate diagnostic seed {seed}")
            if row["uncertainty_order_match"] != "True" or row["combined_order_match"] != "True":
                raise ValueError(f"Unverified shortlist for seed {seed}")
            initial, available, shortlist, total = (int(row[c]) for c in (
                "initial_labels", "available_records", "shortlist_size", "diversity_batch_size"))
            retained, excluded, overlap = (int(row[c]) for c in (
                "diversity_retained", "diversity_excluded", "combined_diversity_overlap"))
            if (initial, available, shortlist, total) != (64, 2336, 256, 64):
                raise ValueError(f"Unexpected matched comparison for seed {seed}")
            if retained + excluded != total or not 0 <= overlap <= retained <= total:
                raise ValueError(f"Inconsistent shortlist counts for seed {seed}")
            cells = []
            for evaluation in SETS:
                field = evaluation.removesuffix("_test") + "_rmse_gap_128"
                gap = float(row[field])
                reference = batch_scores[seed, evaluation, "combined"] - batch_scores[seed, evaluation, "diversity_only"]
                if not math.isclose(gap, reference, rel_tol=0, abs_tol=5.1e-9):
                    raise ValueError(f"First-batch error gap disagrees with archived scores for seed {seed}")
                hidden = " hidden" if evaluation == "local_test" else ""
                cells.append(f'<td class="number" data-audit-set="{evaluation}"{hidden}>{signed(gap)}</td>')
            retained_counts.append(retained)
            shared_counts.append(overlap)
            rows[seed] = (f'<tr data-audit-seed="{seed}"><th scope="row">{seed}</th><td>{retained}</td>'
                          f'<td>{overlap}</td>{"".join(cells)}</tr>')
    if set(rows) != set(SEEDS):
        raise ValueError("Expected four verified shortlist diagnostics")
    lead = (f"Of the 64 records chosen by diversity alone, <strong>{min(retained_counts)}–{max(retained_counts)} "
            f"remained eligible</strong> after screening across the four runs. The two rules ultimately "
            f"chose <strong>{min(shared_counts)}–{max(shared_counts)} of the same records</strong> per run.")
    return lead, "\n".join(rows[seed] for seed in SEEDS)


def render(directory: Path = DATA) -> str:
    scores, contrasts = load(directory)
    low = math.floor(min(scores.values()) * 10) / 10
    high = max(low + .1, math.ceil(max(scores.values()) * 10) / 10)
    lead, audit_rows = shortlist_table(HERE / "results" / "seed_comparison.csv", directory)
    panels = []
    for evaluation, (label, count) in SETS.items():
        for selection in ("mean", *SEEDS):
            sample = "Mean across four seeds" if selection == "mean" else f"Seed {selection}"
            active = evaluation == "distant_test" and selection == "mean"
            panels.append(
                f'<div data-evaluation="{evaluation}" data-sample="{selection}"{"" if active else " hidden"}>'
                f'<table class="strip"><caption>{sample} · {label.lower()} set · {count} variants</caption>'
                '<thead><tr><th scope="col">Rule</th><th scope="col" class="axis">RMSE scale</th>'
                '<th scope="col" class="number">RMSE</th></tr></thead><tbody>'
                + strip_rows(scores, selection, evaluation, low, high)
                + f'</tbody><tfoot><tr aria-hidden="true"><td></td><td class="ticks"><span>{low:.1f}</span>'
                  f'<span>{(low+high)/2:.1f}</span><span>{high:.1f}</span></td><td></td></tr></tfoot></table></div>'
            )

    mean_values = tuple(mean(contrasts[s][i] for s in SEEDS) for i in range(3))
    limit = max(.05, math.ceil(max(abs(v[2]) for v in contrasts.values()) * 20) / 20)
    paired, details = [], []
    for seed, (local, distant, delta) in [*[(s, contrasts[s]) for s in SEEDS], ("Mean", mean_values)]:
        row_label = str(seed)
        position = 50 + 50 * delta / limit
        paired.append(
            f'<tr data-seed="{row_label}"><th scope="row">{row_label}</th><td class="plotcell">'
            f'<div class="contrast-track" aria-hidden="true"><i class="delta {"positive" if delta >= 0 else "negative"}" '
            f'style="left:{min(50,position):.5f}%;width:{abs(50-position):.5f}%"></i></div></td>'
            f'<td class="number">{signed(delta)}</td></tr>'
        )
        details.append(f'<tr><th scope="row">{row_label}</th><td>{signed(local)}</td><td>{signed(distant)}</td><td>{signed(delta)}</td></tr>')
    options = "".join(f'<option value="{s}">Seed {s}</option>' for s in SEEDS)
    replacements = {
        "REPORT": REPORT, "SOURCE": SOURCE, "OPTIONS": options, "PANELS": "\n".join(panels),
        "PAIRED": "\n".join(paired), "LIMIT": f"{limit:.2f}", "DETAILS": "\n".join(details),
        "AUDIT_LEAD": lead, "AUDIT_ROWS": audit_rows,
    }
    document = TEMPLATE
    for key, value in replacements.items():
        document = document.replace("{{" + key + "}}", value)
    return document


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>GFP shortlist choices and prediction error</title>
<style>
:root {
  --ink: #172d32;
  --muted: #445d60;
  --teal: #17645e;
  --ochre: #99522e;
  --line: #c6d2cc;
  --soft: #eef3eb;
  --paper: #fbfcf7;
  color-scheme: light;
}
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font: 1rem/1.5 system-ui,sans-serif;
}
a {
  color: var(--teal);
  text-decoration-thickness: .075em;
  text-underline-offset: .18em;
}
a:focus-visible,select:focus-visible,summary:focus-visible {
  outline: 3px solid #165cba;
  outline-offset: 3px;
}
main,footer {
  max-width: 79rem;
  margin: auto;
  padding: 0 clamp(1rem,4vw,4rem);
}
header {
  padding: clamp(1.7rem,4vw,3.5rem) 0 1.3rem;
  border-bottom: 1px solid var(--line);
}
header>a {
  font-size: .95rem;
  font-weight: 650;
}
h1,h2 {
  font-family: Georgia,serif;
  font-weight: 550;
  letter-spacing: -.035em;
  line-height: 1.1;
}
h1 {
  font-size: clamp(2.3rem,5vw,4.5rem);
  margin: .62em 0 .25em;
  max-width: 22ch;
  text-wrap: balance;
}
h2 {
  font-size: clamp(1.5rem,2.8vw,2.28rem);
  margin: 0 0 .45rem;
}
header p {
  max-width: 76ch;
  font-size: 1.07rem;
  margin: .7rem 0;
}
.controls {
  display: flex;
  gap: 1.3rem;
  align-items: end;
  flex-wrap: wrap;
  margin: 1.4rem 0 2rem;
}
.controls label {
  display: grid;
  gap: .23rem;
  font-size: .87rem;
  font-weight: 650;
}
.controls select {
  font: inherit;
  background: white;
  color: var(--ink);
  border: 1px solid #748c84;
  border-radius: .3rem;
  padding: .6rem 1.65rem .6rem .65rem;
  min-height: 44px;
}
[hidden] {
  display: none!important;
}
.sheet {
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  gap: clamp(1.5rem,4.5vw,4.2rem);
}
section {
  min-width: 0;
  border-top: 3px solid var(--teal);
  padding: 1.1rem 0 .5rem;
}
section>p,.note {
  color: var(--muted);
  margin: .3rem 0 1rem;
  font-size: .95rem;
}
table {
  border-collapse: collapse;
  width: 100%;
  font-variant-numeric: tabular-nums;
  font-size: .94rem;
}
caption {
  text-align: left;
  font-weight: 650;
  padding: .55rem 0 .7rem;
}
th,td {
  text-align: left;
  padding: .62rem .25rem;
  border-bottom: 1px solid var(--line);
}
th[scope=row] {
  font-weight: 580;
}
thead th {
  font-size: .8rem;
  color: var(--muted);
  font-weight: 650;
  border-block: 1px solid var(--line);
}
th:first-child,td:first-child {
  padding-left: 0;
}
td:last-child,th:last-child {
  padding-right: 0;
}
.number {
  text-align: right;
  white-space: nowrap;
}
.axis {
  text-align: center;
}
.plotcell {
  width: 44%;
  padding-inline: .55rem;
}
.track,.contrast-track {
  height: .83rem;
  position: relative;
  background: linear-gradient(0deg,transparent 46%,var(--line) 46%,var(--line) 54%,transparent 54%);
}
.track:before {
  content: "";
  position: absolute;
  left: var(--reference);
  height: 1.4rem;
  top: -.27rem;
  border-left: 1.5px dashed #555;
}
.mark {
  position: absolute;
  top: 50%;
  left: var(--point);
  height: .58rem;
  width: .58rem;
  border-radius: 50%;
  background: #28474b;
  transform: translate(-50%,-50%);
}
.mark.random {
  background: white;
  border: 2px solid #28474b;
}
.mark.combined {
  background: var(--teal);
  border-radius: .04rem;
  transform: translate(-50%,-50%) rotate(45deg);
}
.contrast-track:before {
  content: "";
  position: absolute;
  left: 50%;
  height: 1.1rem;
  top: -.14rem;
  border-left: 1px solid #586c69;
}
.delta {
  position: absolute;
  top: .13rem;
  height: .56rem;
}
.positive {
  background: var(--teal);
}
.negative {
  background: var(--ochre);
}
tr[data-seed=Mean] {
  border-top: 2px solid var(--ink);
}
tr[data-seed=Mean] td,tr[data-seed=Mean] th {
  font-weight: 700;
}
tr[aria-current=true] {
  background: #e1eee3;
}
tfoot td {
  border: 0;
  padding: .3rem .5rem;
  color: var(--muted);
  font-size: .76rem;
}
td.ticks>span {
  display: inline-block;
  width: 33.333%;
}
td.ticks>span:nth-child(2) {
  text-align: center;
}
td.ticks>span:last-child {
  text-align: right;
}
details {
  margin: .9rem 0 1rem;
}
summary {
  cursor: pointer;
  font-weight: 620;
  color: var(--teal);
  padding: .3rem 0;
}
details td,details thead th:not(:first-child) {
  text-align: right;
}
.note {
  margin-top: .7rem;
  font-size: .88rem;
}
footer {
  margin: 1.6rem auto 2rem;
}
footer>div {
  border-top: 1px solid var(--line);
  padding-top: .9rem;
  max-width: 100%;
}
footer p {
  max-width: 83ch;
  font-size: .9rem;
  margin: .4rem 0;
}
@media(max-width:55rem) {
  .sheet {
    grid-template-columns: 1fr;
    gap: 1.25rem;
  }
  .controls {
    margin-bottom: 1.25rem;
  }
  h1 {
    max-width: 21ch;
  }
}
@media(max-width:24rem) {
  main,footer {
    padding-inline: 1rem;
  }
  .controls {
    gap: .6rem;
  }
  table {
    font-size: .84rem;
  }
  .plotcell {
    width: 38%;
  }
  th,td {
    padding-block: .56rem;
  }
  caption {
    font-size: .88rem;
  }
}
@media print {
  .controls {
    display: none;
  }
  main,footer {
    padding: 0;
  }
  .sheet {
    grid-template-columns: 1fr;
  }
  section {
    break-inside: avoid;
  }
}
.audit {
  margin: 0 0 2.2rem;
  padding: 1.1rem 0 .3rem;
}
.audit-layout {
  display: grid;
  grid-template-columns: minmax(15rem,.73fr) minmax(0,1.27fr);
  gap: clamp(1.25rem,4vw,3.5rem);
  align-items: start;
}
.audit-layout p { margin: .5rem 0 0; color: var(--muted); }
.audit table td { text-align: right; }
.audit table th[scope=col]:not(:first-child) { text-align: right; }
.audit table caption { padding-top: .1rem; }
.audit-row-note { font-size: .88rem; color: var(--muted); }
@media (max-width: 55rem) {
  .audit-layout { grid-template-columns: 1fr; gap: .8rem; }
  .audit { margin-bottom: 1.4rem; }
}
</style></head><body>
<main>
<header><a href="{{REPORT}}">GFP case study</a>
<h1>What did the first shortlist leave out?</h1>
<p>Two rules started with the same 64 archived green fluorescent protein (GFP) measurements. One chose 64 more records from the full pool. The combined rule first narrowed the pool from 2,336 records to 256. {{AUDIT_LEAD}}</p></header>
<div class="controls" hidden id="controls">
<label for="evaluation">Evaluation set<select id="evaluation"><option value="distant_test" selected>Distant · 800 variants</option><option value="local_test">Local · 400 variants</option></select></label>
<label for="sample">Starting sample<select id="sample"><option value="mean">All four seeds</option>{{OPTIONS}}</select></label></div>
<noscript><p>The page shows all four seeds and the distant evaluation set. The source tables include the local results.</p></noscript>
<section class="audit" aria-labelledby="audit-heading">
<div class="audit-layout"><div><h2 id="audit-heading">The first 64 choices</h2>
<p>“Eligible” counts the full-pool choices that survived the screen. “Chosen by both” counts the records both rules actually selected.</p>
<p>After this batch, each rule had 128 labels. We measure prediction error in log-brightness units using root mean squared error (RMSE). The gap is combined RMSE minus diversity-only RMSE. Positive values mean the combined rule had higher error.</p></div>
<div><table id="audit-table"><caption><span id="audit-place">Distant set</span> · 64 choices per seed</caption>
<thead><tr><th scope="col">Seed</th><th scope="col">Eligible</th><th scope="col">Chosen by both</th><th scope="col">Error gap (RMSE)</th></tr></thead><tbody>{{AUDIT_ROWS}}</tbody></table>
<p class="audit-row-note">Both archived choice orders matched the reconstruction for every seed. The error gaps describe what followed each batch. They cannot establish which choices caused the difference. <a href="{{REPORT}}">Read the audit</a>.</p></div></div>
</section>
<div class="sheet"><section aria-labelledby="errors"><h2 id="errors">Final error at 384 labels</h2>
<p>After 384 labels, lower RMSE means closer predictions on the selected evaluation set. The dashed line marks random selection in the current view.</p>
<div id="score-panels" aria-live="polite" aria-atomic="true">{{PANELS}}</div>
</section>
<section aria-labelledby="contrast"><h2 id="contrast">Did the benefit grow at distance?</h2>
<p>For each seed, subtract the combined rule’s error from random selection’s error. Then compare that benefit on distant and local variants. A positive difference favors the original expectation.</p>
<table><caption>Change in benefit, distant minus local</caption><thead><tr><th scope="col">Seed</th><th scope="col" class="axis">Difference</th><th scope="col" class="number">RMSE units</th></tr></thead>
<tbody>{{PAIRED}}</tbody><tfoot><tr aria-hidden="true"><td></td><td class="ticks"><span>−{{LIMIT}}</span><span>0</span><span>+{{LIMIT}}</span></td><td></td></tr></tfoot></table>
<details><summary>Inspect both benefits for each seed</summary>
<table><caption>Random RMSE minus combined RMSE</caption><thead><tr><th scope="col">Seed</th><th scope="col">Local</th><th scope="col">Distant</th><th scope="col">Difference</th></tr></thead><tbody>{{DETAILS}}</tbody></table></details></section></div>
</main><footer><div><p>Each seed starts from a different sample of 64 records. All four runs reuse the same evaluation observations. The differences describe these runs on historical data.</p>
<p><a href="https://github.com/TheThunda01/gfp-active-learning/blob/main/experiments/shortlist_review/results/seed_comparison.csv">First-batch diagnostic data</a> · <a href="{{SOURCE}}/learning_curves.csv">Archived errors by rule and seed</a> · <a href="{{SOURCE}}/distance_benefit_contrast.csv">Paired contrasts</a> · <a href="{{REPORT}}">Read the shortlist case study</a></p></div></footer>
<script>
const evaluation = document.getElementById('evaluation');
const sample = document.getElementById('sample');
function showSelection() {
  document.getElementById('audit-place').textContent = evaluation.value === 'distant_test' ? 'Distant set' : 'Local set';
  for (const cell of document.querySelectorAll('[data-audit-set]')) {
    cell.hidden = cell.dataset.auditSet !== evaluation.value;
  }
  for (const row of document.querySelectorAll('[data-audit-seed]')) {
    row.hidden = sample.value !== 'mean' && row.dataset.auditSeed !== sample.value;
  }
  for (const panel of document.querySelectorAll('[data-evaluation]')) {
    panel.hidden = panel.dataset.evaluation !== evaluation.value || panel.dataset.sample !== sample.value;
  }
  for (const row of document.querySelectorAll('[data-seed]')) {
    const selected = row.dataset.seed.toLowerCase() === sample.value;
    if (selected) row.setAttribute('aria-current','true');
    else row.removeAttribute('aria-current');
  }
}
document.getElementById('controls').hidden = false;
evaluation.addEventListener('change',showSelection);
sample.addEventListener('change',showSelection);
showSelection();
</script></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify that the committed HTML matches the archived tables")
    args = parser.parse_args()
    output = HERE.parents[1] / "docs" / "index.html"
    document = render()
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != document:
            raise SystemExit("Explorer differs from archived data or template. Rebuild it with this script.")
    else:
        with output.open("w", encoding="utf-8", newline="\n") as f:
            f.write(document)


if __name__ == "__main__":
    main()
