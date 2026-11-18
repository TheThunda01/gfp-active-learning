"""Guard the saved explorer and the sign convention used in its paired chart."""
import csv
from pathlib import Path
import tempfile
import unittest

from experiments.shortlist_review.build_explorer import DATA, HERE, load, render, shortlist_table


class ExplorerTest(unittest.TestCase):
    def test_committed_page_matches_archived_errors(self):
        html = render()
        self.assertEqual((HERE.parents[1] / 'docs' / 'index.html').read_text(encoding='utf-8'), html)
        self.assertIn('4b27c32047288e32a647e2e8b411f3b272d6113c', html)
        self.assertEqual(html.count('data-evaluation='), 10)

    def test_first_batch_verification_and_error_direction(self):
        source = HERE / 'results' / 'seed_comparison.csv'
        for column, value, error in (
            ('combined_order_match', 'False', 'Unverified shortlist'),
            ('distant_rmse_gap_128', '-0.09716090', 'disagrees'),
            ('diversity_excluded', '64', 'Inconsistent shortlist'),
        ):
            with self.subTest(column=column), tempfile.TemporaryDirectory() as folder:
                with source.open(newline='', encoding='utf-8') as stream:
                    rows = list(csv.DictReader(stream))
                rows[0][column] = value
                path = Path(folder) / 'comparison.csv'
                with path.open('w', newline='', encoding='utf-8') as stream:
                    writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
                with self.assertRaisesRegex(ValueError, error):
                    shortlist_table(path, DATA)

    def test_reversed_contrast_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            curves = 'learning_curves.csv'
            (target / curves).write_bytes((DATA / curves).read_bytes())
            contrast = 'distance_benefit_contrast.csv'
            with (DATA / contrast).open(newline='', encoding='utf-8') as source:
                rows = list(csv.DictReader(source))
            field = 'distant_minus_local_benefit'
            rows[0][field] = str(-float(rows[0][field]))
            with (target / contrast).open('w', newline='', encoding='utf-8') as destination:
                writer = csv.DictWriter(destination, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, 'paired errors'):
                load(target)
