"""Reconstruct the first screen in the archived GFP comparison and report aggregate counts."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

from experiments.uncertainty_ablation.ablation import choose
from gfp_active_learning.benchmark import BUDGETS, SEEDS, make_model
from gfp_active_learning.data import descriptors, encode_sequences, load_dataset

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / 'experiments' / 'uncertainty_ablation' / 'results'
INITIAL, NEXT = BUDGETS[:2]
FINAL = BUDGETS[-1]
BATCH = NEXT - INITIAL
POLICIES = ('combined', 'diversity_only', 'uncertainty_only')


def checked_rows(name, metadata):
    path = ARCHIVE / name
    if hashlib.sha256(path.read_bytes()).hexdigest() != metadata['outputs_sha256'][name]:
        raise ValueError(f'The archived input differs from its recorded digest: {name}')
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def archived_batches(history, seed, pool):
    batches = {(policy, budget): [] for policy in POLICIES for budget in (INITIAL, NEXT)}
    for row in history:
        key = (row['policy'], int(row['label_budget']))
        if int(row['seed']) != seed or key not in batches:
            continue
        index = int(row['pool_index'])
        if not 0 <= index < len(pool) or pool[index]['record_id'] != row['record_id']:
            raise ValueError('Archived acquisition no longer identifies the same pool record')
        batches[key].append(index)
    initial = batches['combined', INITIAL]
    for policy in POLICIES:
        batch = batches[policy, NEXT]
        if batches[policy, INITIAL] != initial or len(initial) != INITIAL or len(batch) != BATCH:
            raise ValueError('Incomplete acquisition history or different starting state')
        if len(set(initial + batch)) != NEXT:
            raise ValueError('Duplicate acquisition in archived first round')
    return initial, {policy: batches[policy, NEXT] for policy in POLICIES}


def screen_counts(shortlist, replayed_combined, archived):
    combined = archived['combined']
    diversity = set(archived['diversity_only'])
    size = len(diversity)
    # Each archived choice is an ordered sequence. Agreement of unordered sets
    # could conceal a different ranking or a tie-breaking change.
    uncertainty_matches = list(shortlist[:size]) == archived['uncertainty_only']
    combined_matches = list(replayed_combined) == combined
    verified = uncertainty_matches and combined_matches
    retained = len(diversity.intersection(shortlist)) if verified else None
    overlap = len(diversity.intersection(combined))
    if verified and (not set(combined).issubset(shortlist) or overlap > retained):
        raise ValueError('The reconstructed screen and recorded choices are inconsistent')
    return {
        'diversity_batch_size': size,
        'diversity_retained': retained,
        'diversity_excluded': size - retained if verified else None,
        'combined_diversity_overlap': overlap,
        'uncertainty_order_match': uncertainty_matches,
        'combined_order_match': combined_matches,
    }


def rmse_gaps(curves, seed):
    indexed = {}
    for row in curves:
        policy, budget = row['policy'], int(row['label_budget'])
        if int(row['seed']) == seed and policy in ('combined', 'diversity_only') and budget in (NEXT, FINAL):
            key = (policy, budget, row['evaluation'])
            if key in indexed:
                raise ValueError(f'Duplicate archived error for {key}')
            indexed[key] = float(row['rmse'])
    gaps = {}
    for budget in (NEXT, FINAL):
        for role in ('local', 'distant'):
            key = (budget, role + '_test')
            diff = indexed[('combined', *key)] - indexed[('diversity_only', *key)]
            gaps[f'{role}_rmse_gap_{budget}'] = f'{diff:.8f}'
    return gaps


def audit():
    metadata = json.loads((ARCHIVE / 'run_metadata.json').read_text(encoding='utf-8'))
    history = checked_rows('query_history.csv', metadata)
    curves = checked_rows('learning_curves.csv', metadata)
    rows, manifest = load_dataset(ROOT / 'data')
    if manifest['dataset_sha256'] != metadata['dataset_sha256']:
        raise ValueError('The pool cannot be matched to the archived ablation')
    pool = [row for row in rows if row['role'] == 'pool']
    codes = encode_sequences([row['sequence'] for row in pool])
    features = descriptors(codes, [int(row['mutation_count']) for row in pool])
    results = []
    for seed in SEEDS:
        initial, archived = archived_batches(history, seed, pool)
        available = np.setdiff1d(np.arange(len(pool)), initial)
        labels = [float(pool[i]['log_brightness']) for i in initial]
        model = make_model(seed + INITIAL).fit(features[initial], labels)
        # For the first batch the two rules use the same ranking and tie stream.
        # Calling the historical ranker for the full 4 x batch screen recovers
        # eligibility; the second call independently runs the combined rule.
        def historical_choices(policy, count):
            return choose(policy, available, initial, features, codes, model, count,
                          np.random.default_rng(seed + 10000))
        shortlist = historical_choices('uncertainty_only', min(4 * BATCH, len(available)))
        combined = historical_choices('combined', BATCH)
        results.append({
            'seed': seed, 'initial_labels': len(initial), 'available_records': len(available),
            'shortlist_size': len(shortlist), **screen_counts(shortlist, combined, archived),
            **rmse_gaps(curves, seed),
        })
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Write an aggregate CSV (default: standard output)')
    args = parser.parse_args()
    results = audit()
    with_rows = all(row['diversity_retained'] is not None for row in results)
    if not with_rows:
        mismatches = [row['seed'] for row in results if row['diversity_retained'] is None]
        print(f'Exact screen counts withheld for seeds {mismatches}: ordered first-round replay differs.',
              file=sys.stderr)
    def write(stream):
        writer = csv.DictWriter(stream, fieldnames=results[0], lineterminator='\n')
        writer.writeheader()
        writer.writerows(results)
    if args.output is None:
        write(sys.stdout)
    else:
        if args.output.exists():
            parser.error(f'Output already exists: {args.output}. Choose a fresh path to compare runs.')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8', newline='') as stream:
            write(stream)


if __name__ == '__main__':
    main()
