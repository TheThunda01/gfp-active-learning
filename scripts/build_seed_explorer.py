"""Inspect paired acquisition seeds without fitting or selecting another model."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVALUATIONS = {'local_test': 'Local (400 sequences)', 'distant_test': 'More mutated (800 sequences)'}
STRATEGIES = {'random': 'Random', 'uncertainty_diversity': 'Uncertainty + diversity'}
SEEDS = (11, 29, 47, 83)
BUDGETS = (64, 128, 192, 256, 384)


def load_results(directory: Path) -> tuple[list[dict], list[dict], dict]:
    """Require the frozen benchmark's complete paired grid and saved deltas."""
    sources = ('learning_curves.csv', 'paired_final_differences.csv')
    loaded = {}
    fingerprints = {}
    for name in sources:
        path = directory / name
        fingerprints[name] = hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        with path.open(encoding='utf-8-sig', newline='') as handle:
            loaded[name] = list(csv.DictReader(handle))
    curves = []
    keys = set()
    for raw in loaded[sources[0]]:
        key = (int(raw['seed']), raw['strategy'], int(raw['label_budget']), raw['evaluation'])
        if key in keys:
            raise ValueError(f'Duplicate learning-curve key: {key}')
        keys.add(key)
        rmse = float(raw['rmse'])
        if not math.isfinite(rmse) or rmse < 0:
            raise ValueError('RMSE must be finite and nonnegative')
        expected_n = {'local_test': 400, 'distant_test': 800}.get(raw['evaluation'])
        if int(raw['n_evaluation']) != expected_n:
            raise ValueError('Unsupported evaluation denominator')
        curves.append(dict(seed=key[0], strategy=key[1], budget=key[2], evaluation=key[3], rmse=rmse))
    expected = set(itertools.product(SEEDS, STRATEGIES, BUDGETS, EVALUATIONS))
    if keys != expected:
        raise ValueError('Expected all 80 seed/policy/budget/evaluation combinations')
    scores = {(r['seed'], r['strategy'], r['budget'], r['evaluation']): r['rmse'] for r in curves}
    for seed, evaluation in itertools.product(SEEDS, EVALUATIONS):
        if not math.isclose(scores[seed, 'random', 64, evaluation], scores[seed, 'uncertainty_diversity', 64, evaluation], abs_tol=1e-12):
            raise ValueError('Paired policies must have the same initial-budget score')
    deltas = []
    seen = set()
    for raw in loaded[sources[1]]:
        key = (int(raw['seed']), raw['evaluation'])
        if key in seen or key not in set(itertools.product(SEEDS, EVALUATIONS)) or int(raw['label_budget']) != 384:
            raise ValueError('Invalid or duplicate final-budget comparison')
        seen.add(key)
        delta = float(raw['rmse_difference_active_minus_random'])
        calculated = scores[key[0], 'uncertainty_diversity', 384, key[1]] - scores[key[0], 'random', 384, key[1]]
        if not math.isfinite(delta) or not math.isclose(delta, calculated, rel_tol=1e-9, abs_tol=1e-12):
            raise ValueError('Saved paired difference disagrees with curve scores')
        deltas.append(dict(seed=key[0], evaluation=key[1], delta=delta))
    if seen != set(itertools.product(SEEDS, EVALUATIONS)):
        raise ValueError('Missing paired final-budget comparison')
    return curves, deltas, fingerprints


def render(curves: list[dict], deltas: list[dict], fingerprints: dict, output: Path) -> None:
    import plotly
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    figure = make_subplots(rows=2, cols=2, subplot_titles=(
        'Local: each paired seed', 'More mutated: each paired seed',
        'Local: final paired difference', 'More mutated: final paired difference'),
        row_heights=[0.64, 0.36], vertical_spacing=0.20)
    colors = {'random': '#245b82', 'uncertainty_diversity': '#b24a2d'}
    for col, evaluation in enumerate(EVALUATIONS, 1):
        for strategy in STRATEGIES:
            for seed in SEEDS:
                rows = sorted((r for r in curves if r['evaluation'] == evaluation and r['strategy'] == strategy and r['seed'] == seed), key=lambda r: r['budget'])
                figure.add_trace(go.Scatter(x=[r['budget'] for r in rows], y=[r['rmse'] for r in rows], mode='lines+markers',
                    name=f'{STRATEGIES[strategy]} · seed {seed}', legendgroup=str(seed), showlegend=col == 1,
                    line=dict(color=colors[strategy], dash={11: 'solid', 29: 'dash', 47: 'dot', 83: 'dashdot'}[seed]),
                    hovertemplate=f'{html.escape(STRATEGIES[strategy])}<br>Seed {seed}<br>Budget %{{x}}<br>RMSE %{{y:.4f}}<extra>{EVALUATIONS[evaluation]}</extra>'), row=1, col=col)
        paired = [next(r for r in deltas if r['evaluation'] == evaluation and r['seed'] == seed) for seed in SEEDS]
        figure.add_trace(go.Bar(x=[f'Seed {r["seed"]}' for r in paired], y=[r['delta'] for r in paired],
            marker_color='#74578d', showlegend=False,
            hovertemplate='Active − random RMSE: %{y:.5f}<extra>%{x}</extra>'), row=2, col=col)
        figure.add_hline(y=0, line_width=1, line_color='#222', row=2, col=col)
        figure.update_xaxes(title_text='Revealed pool labels', tickvals=list(BUDGETS), row=1, col=col)
        figure.update_yaxes(title_text='RMSE (source log-brightness scale)', row=1, col=col)
        figure.update_yaxes(title_text='Active − random RMSE', row=2, col=col)
    # Shared ranges prevent the two evaluation sets or delta panels from implying different scales.
    all_scores = [r['rmse'] for r in curves]
    for col in (1, 2):
        figure.update_yaxes(range=[min(all_scores) - 0.04, max(all_scores) + 0.04], row=1, col=col)
        limit = max(abs(r['delta']) for r in deltas) * 1.2
        figure.update_yaxes(range=[-limit, limit], row=2, col=col)
    figure.update_layout(template='plotly_white', width=1220, height=1015,
        title='GFP acquisition: the average is not every seed', font=dict(family='Arial', size=13),
        legend=dict(orientation='h', y=-0.12, yanchor='top', groupclick='toggleitem'), margin=dict(l=80, r=35, t=95, b=260))
    figure.add_annotation(x=0, y=-0.24, xref='paper', yref='paper', xanchor='left', yanchor='top', showarrow=False, align='left', font=dict(size=12),
        text='Four acquisition seeds reuse the same observed evaluation data. Negative deltas favor active selection.<br>Descriptive comparison only; no confidence intervals, biological replication, or new evaluation.')
    output.mkdir(parents=True, exist_ok=True)
    caption = ('These are the original two-policy results, not the separate four-policy ablation. '
        'Lower RMSE is better. Negative final differences favor uncertainty + diversity; positive differences favor random. '
        'Four acquisition seeds reuse the same observed evaluation sequences; they are not biological replicates or confidence intervals. '
        'The two panels share a vertical scale. Use the legend to inspect a trajectory and hover for exact values. No model was refit.')
    fragment = figure.to_html(full_html=False, include_plotlyjs=True, div_id='gfp-seed-explorer', config={'displaylogo': False, 'responsive': True})
    content = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GFP paired-seed explorer</title><style>body{font:16px/1.55 Arial,sans-serif;margin:24px auto;max-width:1280px;padding:0 20px;color:#20303c}p{max-width:1050px}pre{white-space:pre-wrap;font-size:12px}</style><h1>Inspect acquisition variability</h1><p>' + caption + '</p>' + fragment + '<h2>Source fingerprints (LF-normalized SHA-256)</h2><pre>' + html.escape(json.dumps(fingerprints, indent=2)) + '</pre></html>'
    (output / 'seed-explorer.html').write_text(content, encoding='utf-8')
    figure.write_image(str(output / 'seed-explorer.png'), width=1220, height=1015, scale=1.5)
    (output / 'source-manifest.json').write_text(json.dumps({'schema_version': 1, 'plotly_version': plotly.__version__, 'source_sha256_lf_normalized': fingerprints, 'curve_rows': len(curves), 'paired_differences': len(deltas), 'scope': caption}, indent=2) + '\n', encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir', type=Path, default=ROOT / 'results')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'docs/figures/seed-explorer')
    parser.add_argument('--check-only', action='store_true', help='Validate tables without optional plotting packages')
    args = parser.parse_args()
    curves, deltas, fingerprints = load_results(args.results_dir)
    if not args.check_only:
        render(curves, deltas, fingerprints, args.output_dir)
    print(json.dumps({'curve_rows': len(curves), 'paired_differences': len(deltas), 'validated': True}))


if __name__ == '__main__':
    main()
