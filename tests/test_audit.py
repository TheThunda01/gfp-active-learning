import csv
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from gfp_active_learning.audit import audit, main

ROOT = Path(__file__).resolve().parents[1]


class SavedRunAuditTests(unittest.TestCase):
    def mutate(self, filename, change):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        folder = Path(temporary.name) / 'results'
        shutil.copytree(ROOT / 'results', folder)
        path = folder / filename
        with path.open(newline='') as stream:
            reader = csv.DictReader(stream)
            fields, rows = reader.fieldnames, list(reader)
        change(rows)
        with path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader(); writer.writerows(rows)
        return folder

    def test_baseline_saved_run_passes(self):
        result = audit(ROOT / 'data', ROOT / 'results')
        self.assertEqual(result['query_rows'], 3072)
        self.assertEqual(result['metric_rows'], 80)
        self.assertEqual(result['status'], 'passed')

    def test_wrong_queried_source_label_is_rejected(self):
        folder = self.mutate('query_history.csv', lambda rows: rows[0].update(observed_log_brightness='9.0'))
        with self.assertRaisesRegex(ValueError, 'source label'):
            audit(ROOT / 'data', folder)

    def test_repeated_query_is_rejected(self):
        folder = self.mutate('query_history.csv', lambda rows: rows.__setitem__(1, rows[0].copy()))
        with self.assertRaisesRegex(ValueError, 'repeated acquisition'):
            audit(ROOT / 'data', folder)

    def test_evaluation_identity_cannot_appear_as_pool_query(self):
        folder = self.mutate('query_history.csv', lambda rows: rows[0].update(record_id='local_test_record'))
        with self.assertRaisesRegex(ValueError, 'pool record'):
            audit(ROOT / 'data', folder)

    def test_changed_model_configuration_is_rejected(self):
        folder = self.mutate('query_history.csv', lambda rows: None)
        path = folder / 'run_metadata.json'
        metadata = json.loads(path.read_text())
        metadata['forest']['n_estimators'] = 1
        path.write_text(json.dumps(metadata))
        with self.assertRaisesRegex(ValueError, 'Model configuration'):
            audit(ROOT / 'data', folder)

    def test_wrong_evaluation_count_is_rejected(self):
        folder = self.mutate('learning_curves.csv', lambda rows: rows[0].update(n_evaluation='1'))
        with self.assertRaisesRegex(ValueError, 'Evaluation count'):
            audit(ROOT / 'data', folder)

    def test_missing_metric_is_rejected(self):
        folder = self.mutate('learning_curves.csv', lambda rows: rows.pop())
        with self.assertRaisesRegex(ValueError, 'Missing metric'):
            audit(ROOT / 'data', folder)

    def test_wrong_aggregate_and_paired_difference_are_rejected(self):
        for filename, field, expected in [('learning_summary.csv', 'rmse_mean', 'mean'),
                                          ('paired_final_differences.csv', 'rmse_difference_active_minus_random', 'paired')]:
            folder = self.mutate(filename, lambda rows: rows[0].update({field: '9'}))
            with self.subTest(filename=filename), self.assertRaisesRegex(ValueError, expected):
                audit(ROOT / 'data', folder)

    def test_cli_cannot_overwrite_an_input(self):
        self.assertEqual(main(['--data-dir', str(ROOT / 'data'), '--results-dir', str(ROOT / 'results'),
                               '--out', str(ROOT / 'results/query_history.csv')]), 2)


if __name__ == '__main__':
    unittest.main()
