import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import numpy as np
from gfp_active_learning.predictions import mean_ranks,independent_metrics,export_predictions,verify_predictions

ROOT=Path(__file__).resolve().parents[1]


class PredictionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory();cls.folder=Path(cls.temporary.name)/'export'
        cls.report=export_predictions(ROOT/'data',ROOT/'results',cls.folder)
    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    def test_ties_and_independent_known_metrics(self):
        np.testing.assert_equal(mean_ranks([3,1,1]),[3,1.5,1.5])
        self.assertEqual(independent_metrics([0,2],[1,1]),{'rmse':1.,'mae':1.,'spearman_rho':None})
        self.assertAlmostEqual(independent_metrics([1,1,3],[2,2,6])['spearman_rho'],1)

    def test_all_final_predictions_reproduce_saved_metrics(self):
        self.assertEqual(self.report['status'],'passed')
        self.assertEqual(self.report['prediction_rows'],9600);self.assertEqual(self.report['metric_rows'],16)
        self.assertLess((self.folder/'final_predictions.csv.gz').stat().st_size,300000)

    def variant(self,change):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);p=Path(t.name)/'data';shutil.copytree(self.folder,p)
        raw=gzip.decompress((p/'final_predictions.csv.gz').read_bytes()).decode();reader=csv.DictReader(io.StringIO(raw));fields=reader.fieldnames;rows=list(reader)
        change(rows);out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(rows)
        raw=gzip.compress(out.getvalue().encode(),mtime=0);(p/'final_predictions.csv.gz').write_bytes(raw)
        m=json.loads((p/'manifest.json').read_text());m['prediction_sha256']=hashlib.sha256(raw).hexdigest();m['rows']=len(rows);(p/'manifest.json').write_text(json.dumps(m))
        return p

    def test_wrong_prediction_changes_recomputed_score(self):
        p=self.variant(lambda rows:rows[0].update(predicted_log_brightness='100'))
        self.assertEqual(verify_predictions(ROOT/'data',ROOT/'results',p)['status'],'failed')

    def test_missing_duplicate_wrong_role_and_nonfinite_records_fail(self):
        for change in [lambda rows:rows.pop(),lambda rows:rows.__setitem__(1,rows[0].copy()),
                       lambda rows:rows[0].update(evaluation='pool'),lambda rows:rows[0].update(predicted_log_brightness='nan')]:
            with self.subTest(change=change),self.assertRaises(ValueError):verify_predictions(ROOT/'data',ROOT/'results',self.variant(change))

    def test_fingerprint_failure_precedes_parsing(self):
        p=self.variant(lambda rows:None);(p/'final_predictions.csv.gz').write_bytes(b'bad')
        with self.assertRaisesRegex(ValueError,'fingerprint'):verify_predictions(ROOT/'data',ROOT/'results',p)


if __name__=='__main__':unittest.main()
