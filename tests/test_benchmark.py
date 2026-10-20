import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from sklearn.ensemble import RandomForestRegressor

from gfp_active_learning.data import load_dataset, validate_records, encode_sequences, descriptors, nearest_hamming
from gfp_active_learning.benchmark import PoolOracle, choose_acquisition, simulate, scores

ROOT = Path(__file__).resolve().parents[1]


class DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.manifest = load_dataset(ROOT / 'data')

    def test_pinned_dataset_and_disjoint_roles(self):
        self.assertEqual(len(self.rows), 3600)
        self.assertEqual(len({r['sequence'] for r in self.rows}), 3600)
        self.assertEqual({role: sum(r['role'] == role for r in self.rows)
                          for role in ('pool', 'local_test', 'distant_test')},
                         {'pool': 2400, 'local_test': 400, 'distant_test': 800})

    def test_tampered_bytes_fail_before_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target/'manifest.json').write_bytes((ROOT/'data/manifest.json').read_bytes())
            (target/'dataset.csv').write_bytes((ROOT/'data/dataset.csv').read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                load_dataset(target)

    def test_duplicate_sequence_or_identifier_rejected(self):
        for field in ('record_id', 'sequence'):
            rows = copy.deepcopy(self.rows)
            rows[1][field] = rows[0][field]
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'Duplicate'):
                validate_records(rows)

    def test_invalid_labels_and_split_membership_rejected(self):
        for field, value in [('log_brightness', 'nan'), ('mutation_count', '1.5'),
                             ('source_split', 'test'), ('role', 'unrecognized')]:
            rows = copy.deepcopy(self.rows)
            rows[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_records(rows)

    def test_changed_sequence_rejected(self):
        rows = copy.deepcopy(self.rows)
        rows[0]['sequence'] = 'X' + rows[0]['sequence'][1:]
        rows[0]['sequence_sha256'] = hashlib.sha256(rows[0]['sequence'].encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'canonical'):
            validate_records(rows)

    def test_hand_calculated_descriptors_and_distance(self):
        codes = encode_sequences(['AACC', 'ACCC', 'AAAA'])
        features = descriptors(codes, [2, 3, 0])
        self.assertEqual(features.shape, (3, 21))
        np.testing.assert_allclose(features[:, 0], [.5, .25, 1])
        np.testing.assert_allclose(features[:, 1], [.5, .75, 0])
        np.testing.assert_allclose(features[:, :20].sum(axis=1), 1)
        np.testing.assert_equal(features[:, 20], [2, 3, 0])
        np.testing.assert_allclose(nearest_hamming(codes[:2], codes[2:]), [.5, .75])

    def test_invalid_descriptor_inputs_fail(self):
        for sequences in ([], [''], ['AA', 'A'], ['AX']):
            with self.subTest(sequences=sequences), self.assertRaises(ValueError):
                encode_sequences(sequences)
        for codes, mutation in [([[.5, 1]], [1]), ([[0, 1]], [1.5]),
                                ([[0, 20]], [1]), ([[0, 1]], [-1])]:
            with self.subTest(codes=codes, mutation=mutation), self.assertRaises(ValueError):
                descriptors(codes, mutation)
        with self.assertRaises(ValueError):
            nearest_hamming(np.zeros((1, 2)), np.zeros((1, 2)), chunk=0)


class SimulationTests(unittest.TestCase):
    @staticmethod
    def fixture():
        rng = np.random.default_rng(20)
        codes = rng.integers(0, 5, size=(24, 9), dtype=np.uint8)
        features = descriptors(codes, np.arange(24) % 4)
        labels = features[:, 0] * 3 + features[:, -1] * .15
        return features, codes, labels, {'local_test': (features[:6], labels[:6])}

    @staticmethod
    def model(seed):
        return RandomForestRegressor(n_estimators=8, max_depth=3, min_samples_leaf=1,
                                     random_state=seed, n_jobs=1)

    def run_small(self, strategy, evaluation=None, labels=None):
        features, codes, default_labels, default_eval = self.fixture()
        return simulate(features, codes, default_labels if labels is None else labels,
                        default_eval if evaluation is None else evaluation,
                        strategy, 71, budgets=(4, 8, 12), model_factory=self.model)

    def test_oracle_only_reveals_acquired_labels(self):
        oracle = PoolOracle([2, 3, 5])
        with self.assertRaisesRegex(ValueError, 'before acquisition'):
            oracle.labels([1])
        oracle.acquire([1])
        np.testing.assert_equal(oracle.labels([1]), [3])
        for indices in ([1], [0, 0], [-1], [3], [.5]):
            with self.subTest(indices=indices), self.assertRaises(ValueError):
                oracle.acquire(indices)
        with self.assertRaises(ValueError):
            oracle.labels([1.5])

    def test_initial_sets_match_and_queries_are_unique(self):
        random_records, random_history = self.run_small('random')
        active_records, active_history = self.run_small('uncertainty_diversity')
        self.assertEqual(random_history[:4], [dict(h, strategy='random') for h in active_history[:4]])
        for records, history in ((random_records, random_history), (active_records, active_history)):
            self.assertEqual(len(history), 12)
            self.assertEqual(len({h['pool_index'] for h in history}), 12)
            self.assertEqual([r['label_budget'] for r in records], [4, 8, 12])

    def test_evaluation_outcomes_cannot_change_acquisition(self):
        features, _, labels, evaluation = self.fixture()
        changed_eval = {'local_test': (features[:6], -1000 * labels[:6] + 17)}
        for strategy in ('random', 'uncertainty_diversity'):
            baseline_records, baseline_history = self.run_small(strategy)
            changed_records, changed_history = self.run_small(strategy, evaluation=changed_eval)
            self.assertEqual(baseline_history, changed_history)
            self.assertNotEqual(baseline_records, changed_records)

    def test_unrevealed_pool_labels_cannot_change_acquisition(self):
        _, _, labels, _ = self.fixture()
        for strategy in ('random', 'uncertainty_diversity'):
            records, history = self.run_small(strategy)
            acquired = {row['pool_index'] for row in history}
            changed = labels.copy()
            for i in range(len(changed)):
                if i not in acquired:
                    changed[i] = 12345 + i
            changed_records, changed_history = self.run_small(strategy, labels=changed)
            self.assertEqual(history, changed_history)
            self.assertEqual(records, changed_records)

    def test_fixed_seed_is_reproducible(self):
        for strategy in ('random', 'uncertainty_diversity'):
            self.assertEqual(self.run_small(strategy), self.run_small(strategy))

    def test_acquisition_rejects_bad_contract(self):
        x, codes, y, _ = self.fixture()
        model = self.model(3).fit(x[:4], y[:4])
        for available, selected, count in [([1, 2], [1], 1), ([1, 1], [], 1), ([1], [], 2)]:
            with self.subTest(available=available), self.assertRaises(ValueError):
                choose_acquisition('random', available, selected, x, codes, model, count, np.random.default_rng(1))

    def test_metrics_known_values_and_constant_rank(self):
        result = scores([0, 2], [1, 1])
        self.assertEqual(result, {'rmse': 1, 'mae': 1, 'spearman_rho': None})
        self.assertAlmostEqual(scores([1, 2, 3], [2, 4, 6])['spearman_rho'], 1)
        for truth, pred in [([], []), ([1], [1, 2]), ([float('nan')], [1])]:
            with self.assertRaises(ValueError):
                scores(truth, pred)

    def test_invalid_budgets_rejected(self):
        x, codes, labels, evaluation = self.fixture()
        for budgets in ((), (1, 4), (4, 4), (4, 25), (8, 4)):
            with self.subTest(budgets=budgets), self.assertRaises(ValueError):
                simulate(x, codes, labels, evaluation, 'random', 1, budgets, self.model)


if __name__ == '__main__':
    unittest.main()
