"""Compare committed and reproduced numeric outputs, allowing float roundoff."""
import argparse
import csv
import json
from pathlib import Path
import math

FILES = ('learning_curves.csv', 'learning_summary.csv', 'query_history.csv',
         'distance_audit.csv', 'all_pool_reference.csv', 'paired_final_differences.csv')


def compare(expected, actual):
    for filename in FILES:
        with (expected/filename).open(newline='') as stream:
            left = list(csv.reader(stream))
        with (actual/filename).open(newline='') as stream:
            right = list(csv.reader(stream))
        if not left or left[0] != right[0] or len(left) != len(right):
            raise ValueError(f'Changed schema/row count: {filename}')
        for line, (a, b) in enumerate(zip(left[1:], right[1:]), 2):
            if len(a) != len(b):
                raise ValueError(f'Changed column count: {filename}:{line}')
            for column, (x, y) in enumerate(zip(a, b)):
                try:
                    one, two = float(x), float(y)
                except ValueError:
                    equal = x == y
                else:
                    equal = math.isfinite(one) and math.isfinite(two) and math.isclose(one, two, rel_tol=1e-6, abs_tol=1e-7)
                if not equal:
                    raise ValueError(f'Changed result: {filename}:{line}:{column}: {x!r} vs {y!r}')
    left = json.loads((expected/'run_metadata.json').read_text())
    right = json.loads((actual/'run_metadata.json').read_text())
    for key in ('data_sha256', 'data_roles', 'feature_count', 'budgets', 'seeds', 'strategies', 'forest', 'model_seed_rule'):
        if left[key] != right[key]:
            raise ValueError(f'Changed run metadata: {key}')
    print('Six CSVs match: exact text, numeric rtol=1e-6/atol=1e-7; input hash and run configuration match.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('expected', type=Path)
    parser.add_argument('actual', type=Path)
    args = parser.parse_args()
    compare(args.expected, args.actual)
