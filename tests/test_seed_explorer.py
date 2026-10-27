"""Check that the optional view cannot silently lose pairing or alter deltas."""
import csv
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('seed_explorer', ROOT / 'scripts/build_seed_explorer.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SeedExplorerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        for name in ('learning_curves.csv', 'paired_final_differences.csv'):
            shutil.copyfile(ROOT / 'results' / name, self.path / name)

    def edit(self, name, change):
        path = self.path / name
        with path.open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        fields = list(rows[0])
        change(rows)
        with path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_reference_has_complete_pairing(self):
        curves, deltas, hashes = MODULE.load_results(self.path)
        self.assertEqual((len(curves), len(deltas), len(hashes)), (80, 8, 2))

    def test_missing_budget_is_rejected(self):
        self.edit('learning_curves.csv', lambda rows: rows.pop())
        with self.assertRaisesRegex(ValueError, '80'):
            MODULE.load_results(self.path)

    def test_duplicate_key_is_rejected(self):
        self.edit('learning_curves.csv', lambda rows: rows.append(rows[0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            MODULE.load_results(self.path)

    def test_wrong_evaluation_denominator_is_rejected(self):
        self.edit('learning_curves.csv', lambda rows: rows[0].update(n_evaluation='800'))
        with self.assertRaisesRegex(ValueError, 'denominator'):
            MODULE.load_results(self.path)

    def test_nonfinite_metric_is_rejected(self):
        self.edit('learning_curves.csv', lambda rows: rows[0].update(rmse='nan'))
        with self.assertRaisesRegex(ValueError, 'finite'):
            MODULE.load_results(self.path)

    def test_changed_delta_is_rejected(self):
        self.edit('paired_final_differences.csv', lambda rows: rows[0].update(rmse_difference_active_minus_random='0.9'))
        with self.assertRaisesRegex(ValueError, 'disagrees'):
            MODULE.load_results(self.path)

    def test_initial_pair_mismatch_is_rejected(self):
        self.edit('learning_curves.csv', lambda rows: rows[0].update(rmse='0.5'))
        with self.assertRaisesRegex(ValueError, 'initial-budget'):
            MODULE.load_results(self.path)
