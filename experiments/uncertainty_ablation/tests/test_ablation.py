import unittest
from unittest.mock import patch

import numpy as np
from sklearn.ensemble import RandomForestRegressor

from experiments.uncertainty_ablation.ablation import POLICIES, choose, contrast_description, rank_association, simulate
from gfp_active_learning.benchmark import choose_acquisition
from gfp_active_learning.data import descriptors


def fixture():
    rng=np.random.default_rng(20)
    codes=rng.integers(0,5,size=(24,9),dtype=np.uint8)
    x=descriptors(codes,np.arange(24)%4)
    y=x[:,0]*3+x[:,-1]*.15
    return x,codes,y,{'local_test':(x[:6],y[:6])}


def forest(seed):
    return RandomForestRegressor(n_estimators=8,max_depth=3,min_samples_leaf=1,random_state=seed,n_jobs=1)


class AblationTests(unittest.TestCase):
    def run_small(self,policy,evaluation=None,labels=None):
        x,codes,y,e=fixture()
        return simulate(x,codes,y if labels is None else labels,e if evaluation is None else evaluation,
                        policy,71,budgets=(4,8,12),model_factory=forest)

    def test_initial_sets_metrics_and_budgets_match_all_policies(self):
        runs=[self.run_small(p) for p in POLICIES]
        first=runs[0]
        for metrics,history,_ in runs:
            self.assertEqual([h['pool_index'] for h in history[:4]],[h['pool_index'] for h in first[1][:4]])
            self.assertEqual(len(history),12);self.assertEqual(len({h['pool_index'] for h in history}),12)
            self.assertEqual([r['label_budget'] for r in metrics],[4,8,12])
            self.assertEqual(metrics[0]['rmse'],first[0][0]['rmse'])

    def test_old_policy_selectors_remain_exact(self):
        x,codes,y,_=fixture();model=forest(3).fit(x[:4],y[:4])
        for policy,old in [('random','random'),('combined','uncertainty_diversity')]:
            expected=choose_acquisition(old,np.arange(4,24),np.arange(4),x,codes,model,4,np.random.default_rng(6))
            actual=choose(policy,np.arange(4,24),np.arange(4),x,codes,model,4,np.random.default_rng(6))
            np.testing.assert_array_equal(actual,expected)

    def test_diversity_only_never_reads_model_predictions(self):
        x,codes,_,_=fixture()
        with patch('experiments.uncertainty_ablation.ablation.tree_spread',side_effect=AssertionError('uncertainty used')):
            selected=choose('diversity_only',np.arange(4,24),np.arange(4),x,codes,None,4,np.random.default_rng(1))
        self.assertEqual(len(set(selected)),4)

    def test_uncertainty_only_never_reads_hamming_distance(self):
        x,codes,y,_=fixture();model=forest(3).fit(x[:4],y[:4])
        with patch('experiments.uncertainty_ablation.ablation.nearest_hamming',side_effect=AssertionError('diversity used')):
            selected=choose('uncertainty_only',np.arange(4,24),np.arange(4),x,codes,model,4,np.random.default_rng(1))
        self.assertEqual(len(set(selected)),4)

    def test_evaluation_outcomes_do_not_change_any_acquisition(self):
        x,_,y,_=fixture()
        for p in POLICIES:
            baseline=self.run_small(p)
            changed=self.run_small(p,evaluation={'local_test':(x[:6],1000-y[:6])})
            self.assertEqual(baseline[1],changed[1]);self.assertNotEqual(baseline[0],changed[0])

    def test_never_revealed_labels_do_not_change_any_policy(self):
        _,_,y,_=fixture()
        for p in POLICIES:
            baseline=self.run_small(p);changed=y.copy()
            revealed={h['pool_index'] for h in baseline[1]}
            for i in set(range(len(y)))-revealed:changed[i]=12345+i
            self.assertEqual(baseline,self.run_small(p,labels=changed))

    def test_contrast_description_tracks_the_measured_directions(self):
        for values, direction, counts in [
            ([1, 2], "larger on the distant set", "2 positive, 0 negative, and 0 tied"),
            ([-1, 1, 0], "equal on the two sets", "1 positive, 1 negative, and 1 tied"),
            ([-3, 1, -2, 1], "larger on the local set", "2 positive, 2 negative, and 0 tied"),
        ]:
            with self.subTest(values=values):
                text = contrast_description([{"distant_minus_local_benefit": x} for x in values])
                self.assertIn(direction, text)
                self.assertIn(counts, text)

    def test_constant_association_is_undefined(self):
        self.assertIsNone(rank_association([1,1,1],[1,2,3]))
        self.assertIsNone(rank_association([1,2,3],[1,1,1]))
        self.assertAlmostEqual(rank_association([1,2,3],[3,2,1]),-1)


if __name__=='__main__':unittest.main()
