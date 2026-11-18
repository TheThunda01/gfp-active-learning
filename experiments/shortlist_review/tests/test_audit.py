import unittest

from experiments.shortlist_review.audit import rmse_gaps, screen_counts


class ScreenAuditTest(unittest.TestCase):
    def setUp(self):
        self.archived = {
            'combined': [3, 1],
            'uncertainty_only': [1, 2],
            'diversity_only': [3, 5],
        }

    def test_eligible_records_differ_from_actual_selections(self):
        archived = {**self.archived, 'diversity_only': [2, 3]}
        row = screen_counts([1, 2, 3, 4], [3, 1], archived)
        self.assertEqual(row['diversity_retained'], 2)
        self.assertEqual(row['diversity_excluded'], 0)
        self.assertEqual(row['combined_diversity_overlap'], 1)

    def test_mismatched_order_withholds_counts_but_retains_archived_overlap(self):
        for ranking, chosen in (([2, 1, 3, 4], [3, 1]), ([1, 2, 3, 4], [1, 3])):
            with self.subTest(ranking=ranking, chosen=chosen):
                row = screen_counts(ranking, chosen, self.archived)
                self.assertIsNone(row['diversity_retained'])
                self.assertIsNone(row['diversity_excluded'])
                self.assertEqual(row['combined_diversity_overlap'], 1)

    def test_replayed_choices_must_be_eligible(self):
        with self.assertRaisesRegex(ValueError, 'inconsistent'):
            screen_counts([1, 2, 4, 6], [3, 1], self.archived)

    def test_rmse_gaps_use_same_seed_role_and_budget(self):
        curves = []
        for budget, difference in ((128, 0.25), (384, 0.5)):
            for evaluation, sign in (('local_test', 1), ('distant_test', -1)):
                for policy, value in (('combined', 1 + sign * difference), ('diversity_only', 1)):
                    curves.append(dict(seed=11, label_budget=budget, evaluation=evaluation,
                                       policy=policy, rmse=value))
        self.assertEqual(rmse_gaps(curves, 11), {
            'local_rmse_gap_128': '0.25000000', 'distant_rmse_gap_128': '-0.25000000',
            'local_rmse_gap_384': '0.50000000', 'distant_rmse_gap_384': '-0.50000000',
        })


if __name__ == '__main__':
    unittest.main()
