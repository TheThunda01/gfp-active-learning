"""Independently check saved benchmark records without fitting a model."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

from .benchmark import BUDGETS, SEEDS, STRATEGIES, make_model
from .data import ROLES, load_dataset, encode_sequences, nearest_hamming

FILES = ('query_history.csv', 'learning_curves.csv', 'learning_summary.csv',
         'paired_final_differences.csv', 'all_pool_reference.csv', 'distance_audit.csv')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    result = float(value)
    require(np.isfinite(result), 'Nonfinite numeric result')
    return result


def integer(value):
    result = number(value)
    require(result == int(result), 'Expected integer result')
    return int(result)


def near(value, expected, label):
    require(np.isclose(number(value), expected, rtol=1e-10, atol=1e-12), f'Mismatched {label}')


def read_table(path):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames and len(reader.fieldnames) == len(set(reader.fieldnames)), f'Invalid header: {path.name}')
        rows = list(reader)
    require(rows and all(None not in row and None not in row.values() for row in rows), f'Empty or malformed table: {path.name}')
    return rows


def audit(data_dir, results_dir):
    """Validate one complete standard run; an audit cannot prove human blinding."""
    data_dir, results_dir = Path(data_dir), Path(results_dir)
    rows, manifest = load_dataset(data_dir)
    metadata = json.loads((results_dir / 'run_metadata.json').read_text())
    require(metadata['data_sha256'] == manifest['dataset_sha256'], 'Run uses different input hash')
    require(metadata['budgets'] == list(BUDGETS) and metadata['seeds'] == list(SEEDS)
            and metadata['strategies'] == list(STRATEGIES), 'Run configuration differs from the standard benchmark')
    require(metadata['feature_count'] == 21 and metadata['forest'] == make_model(2026).get_params(), 'Model configuration differs')
    require(metadata['model_seed_rule'] == 'Simulation fits use seed + label_budget; all-pool reference uses 2026', 'Model seed rule differs')
    counts = {role: sum(row['role'] == role for row in rows) for role in ROLES}
    require(metadata['data_roles'] == counts, 'Data role counts differ')
    tables = {name: read_table(results_dir / name) for name in FILES}
    pool = [row for row in rows if row['role'] == 'pool']
    histories = {(seed, policy): [] for seed in SEEDS for policy in STRATEGIES}
    for row in tables['query_history.csv']:
        key = (integer(row['seed']), row['strategy'])
        require(key in histories, 'Unknown query seed or policy')
        index, budget = integer(row['pool_index']), integer(row['label_budget'])
        require(0 <= index < len(pool) and budget in BUDGETS, 'Invalid pool index or budget')
        source = pool[index]
        require(row['record_id'] == source['record_id'] and row['sequence_sha256'] == source['sequence_sha256'], 'Query identity is not its declared pool record')
        near(row['observed_log_brightness'], number(source['log_brightness']), 'queried source label')
        require(row['acquisition'] == ('initial_random' if budget == BUDGETS[0] else row['strategy']), 'Query acquisition label differs')
        histories[key].append((budget, index))
    for seed in SEEDS:
        expected_initial = np.random.default_rng(seed).choice(len(pool), BUDGETS[0], replace=False).tolist()
        for policy in STRATEGIES:
            history = histories[(seed, policy)]
            require(len(history) == BUDGETS[-1] and len({i for _, i in history}) == len(history), 'Missing or repeated acquisition')
            require([b for b, _ in history] == sorted(b for b, _ in history), 'Acquisition budget order differs')
            require([i for b, i in history if b == BUDGETS[0]] == expected_initial, 'Initial set is not the paired seeded sample')
            previous = 0
            for budget in BUDGETS:
                require(sum(b == budget for b, _ in history) == budget - previous, 'Acquisition batch size differs')
                previous = budget
    metrics = {}
    for row in tables['learning_curves.csv']:
        key = (integer(row['seed']), row['strategy'], integer(row['label_budget']), row['evaluation'])
        require(key not in metrics, 'Duplicate metric record')
        require(key[0] in SEEDS and key[1] in STRATEGIES and key[2] in BUDGETS and key[3] in ROLES[1:], 'Unknown metric key')
        require(integer(row['n_evaluation']) == counts[key[3]], 'Evaluation count differs')
        require(number(row['rmse']) >= 0 and number(row['mae']) >= 0, 'Negative error metric')
        rho = None if row['spearman_rho'] == '' else number(row['spearman_rho'])
        require(rho is None or -1 <= rho <= 1, 'Invalid rank correlation')
        metrics[key] = row
    require(len(metrics) == len(SEEDS) * len(STRATEGIES) * len(BUDGETS) * 2, 'Missing metric records')
    seen = set()
    for row in tables['learning_summary.csv']:
        key = (row['strategy'], integer(row['label_budget']), row['evaluation'])
        require(key not in seen and all((s, *key) in metrics for s in SEEDS), 'Duplicate or unknown summary')
        seen.add(key)
        require(integer(row['repeated_seeds']) == len(SEEDS), 'Summary seed count differs')
        for metric in ('rmse', 'mae', 'spearman_rho'):
            values = [number(metrics[(s, *key)][metric]) for s in SEEDS if metrics[(s, *key)][metric] != '']
            if values:
                near(row[metric + '_mean'], np.mean(values), metric + ' mean')
                if len(values) > 1:
                    near(row[metric + '_sd_descriptive'], np.std(values, ddof=1), metric + ' SD')
                else:
                    require(row[metric + '_sd_descriptive'] == '', 'Undefined SD must be empty')
            else:
                require(row[metric + '_mean'] == row[metric + '_sd_descriptive'] == '', 'Undefined metric must be empty')
    require(len(seen) == len(STRATEGIES) * len(BUDGETS) * 2, 'Missing summaries')
    seen = set()
    for row in tables['paired_final_differences.csv']:
        key = (integer(row['seed']), row['evaluation'])
        require(key not in seen and key[0] in SEEDS and key[1] in ROLES[1:], 'Duplicate or unknown paired record')
        seen.add(key)
        require(integer(row['label_budget']) == BUDGETS[-1], 'Paired budget differs')
        active = metrics[(key[0], 'uncertainty_diversity', BUDGETS[-1], key[1])]
        random = metrics[(key[0], 'random', BUDGETS[-1], key[1])]
        near(row['rmse_difference_active_minus_random'], number(active['rmse']) - number(random['rmse']), 'paired difference')
    require(len(seen) == len(SEEDS) * 2, 'Missing paired records')
    seen = set()
    for row in tables['all_pool_reference.csv']:
        require(row['evaluation'] in ROLES[1:] and row['evaluation'] not in seen, 'Invalid all-pool reference')
        seen.add(row['evaluation'])
        require(integer(row['labels_used']) == len(pool), 'Reference label count differs')
        require(number(row['rmse']) >= 0 and number(row['mae']) >= 0, 'Invalid reference error')
        require(-1 <= number(row['spearman_rho']) <= 1, 'Invalid reference correlation')
    require(len(seen) == 2, 'Missing all-pool reference')
    seen = set()
    pool_codes = encode_sequences([row['sequence'] for row in pool])
    for row in tables['distance_audit.csv']:
        role = row['evaluation']
        require(role in ROLES[1:] and role not in seen, 'Invalid distance role')
        seen.add(role)
        codes = encode_sequences([r['sequence'] for r in rows if r['role'] == role])
        values = np.rint(nearest_hamming(codes, pool_codes) * codes.shape[1])
        require(integer(row['n']) == len(values), 'Distance count differs')
        for field, expected in [('min', values.min()), ('median', np.median(values)), ('max', values.max())]:
            near(row['nearest_pool_mismatches_' + field], expected, 'sequence distance ' + field)
    require(len(seen) == 2, 'Missing distance audit')
    return {'schema_version': '1.0', 'status': 'passed', 'input_sha256': manifest['dataset_sha256'],
            'query_rows': sum(len(h) for h in histories.values()), 'metric_rows': len(metrics),
            'summary_rows': len(tables['learning_summary.csv']), 'paired_rows': len(tables['paired_final_differences.csv']),
            'checks': ['source hashes and roles', 'fixed model configuration', 'pool-only unique queries and source labels',
                       'seeded paired initial sets and batch sizes', 'complete metric keys', 'recomputed means and sample SDs',
                       'recomputed paired differences', 'reference counts', 'recomputed sequence distances'],
            'result_sha256': {name: hashlib.sha256((results_dir / name).read_bytes()).hexdigest()
                              for name in (*FILES, 'run_metadata.json')},
            'limits': ['Does not refit models or independently recompute prediction errors.',
                       'Consistent saved records do not prove that code or humans never saw hidden labels.']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path('data'))
    parser.add_argument('--results-dir', type=Path, default=Path('results'))
    parser.add_argument('--out', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.out:
            inputs = [args.results_dir / name for name in (*FILES, 'run_metadata.json')]
            inputs += [args.data_dir / name for name in ('dataset.csv', 'manifest.json')]
            require(args.out.resolve() not in {p.resolve() for p in inputs}, 'Audit output must not overwrite its inputs')
        result = audit(args.data_dir, args.results_dir)
        text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n'
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text)
        print(text, end='')
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f'Audit stopped: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
