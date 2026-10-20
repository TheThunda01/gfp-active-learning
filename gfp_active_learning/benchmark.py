"""Retrospective pool-based acquisition on measured GFP observations only."""
from __future__ import annotations
import csv
import importlib.metadata
import json
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestRegressor
from .data import load_dataset, encode_sequences, descriptors, nearest_hamming

BUDGETS = (64, 128, 192, 256, 384)
SEEDS = (11, 29, 47, 83)
STRATEGIES = ('random', 'uncertainty_diversity')


class PoolOracle:
    """The simulator reveals measured pool labels only when an ID is acquired."""
    def __init__(self, values):
        self._values = np.asarray(values, dtype=float)
        if self._values.ndim != 1 or not np.isfinite(self._values).all():
            raise ValueError('Pool labels must be finite')
        self.revealed = {}

    def acquire(self, indices):
        indices = list(indices)
        if len(set(indices)) != len(indices):
            raise ValueError('Cannot acquire the same record twice in a batch')
        if any(not isinstance(i, (int, np.integer)) or i < 0 or i >= len(self._values) or i in self.revealed for i in indices):
            raise ValueError('Acquisition must use unseen pool records only')
        for i in indices:
            self.revealed[int(i)] = float(self._values[i])

    def labels(self, indices):
        indices = list(indices)
        if any(not isinstance(i, (int, np.integer)) for i in indices):
            raise ValueError('Pool indices must be integers')
        try:
            return np.array([self.revealed[int(i)] for i in indices])
        except KeyError as error:
            raise ValueError('Label requested before acquisition') from error


def make_model(seed):
    return RandomForestRegressor(n_estimators=64, max_depth=10, min_samples_leaf=2,
                                 max_features=1.0, random_state=seed, n_jobs=1)


def scores(truth, prediction):
    truth, prediction = np.asarray(truth), np.asarray(prediction)
    if truth.shape != prediction.shape or truth.ndim != 1 or not len(truth) or not np.isfinite(truth).all() or not np.isfinite(prediction).all():
        raise ValueError('Scoring requires equal finite nonempty vectors')
    error = prediction - truth
    rank = float(spearmanr(truth, prediction).statistic) if np.std(truth) > 0 and np.std(prediction) > 0 else None
    return {'rmse': float(np.sqrt(np.mean(error**2))), 'mae': float(np.mean(np.abs(error))), 'spearman_rho': rank}


def choose_acquisition(strategy, available, selected, features, codes, model, count, rng):
    """No labels, target outcomes, or evaluation metrics are accepted here."""
    available, selected = np.asarray(available, dtype=int), np.asarray(selected, dtype=int)
    if count < 1 or count > len(available) or len(set(available)) != len(available) or set(available) & set(selected):
        raise ValueError('Acquisition candidate/count contract failed')
    if strategy == 'random':
        return rng.choice(available, count, replace=False)
    if strategy != 'uncertainty_diversity':
        raise ValueError('Unknown acquisition strategy')
    if not len(selected):
        raise ValueError('Uncertainty acquisition requires an initial labeled set')
    tree_predictions = np.array([tree.predict(features[available]) for tree in model.estimators_])
    spread = tree_predictions.std(axis=0)
    # Seeded random tie-breaking avoids always choosing the first hashed record.
    order = np.lexsort((rng.random(len(available)), -spread))
    shortlist_positions = order[:min(len(available), 4 * count)]
    candidates = available[shortlist_positions]
    uncertainty = spread[shortlist_positions]
    distance = nearest_hamming(codes[candidates], codes[selected])
    picked = []
    for _ in range(count):
        # Main priority: distance from labeled/current-batch records; next: spread.
        position = np.lexsort((np.arange(len(candidates)), -uncertainty, -distance))[0]
        picked.append(int(candidates[position]))
        new_distance = (codes[candidates] != codes[candidates[position]]).mean(axis=1)
        distance = np.minimum(distance, new_distance)
        distance[[i for i, candidate in enumerate(candidates) if candidate in picked]] = -np.inf
    return np.array(picked, dtype=int)


def simulate(pool_features, pool_codes, pool_labels, evaluation, strategy, seed,
             budgets=BUDGETS, model_factory=make_model):
    """Evaluation outcomes affect returned metrics only, never acquisition."""
    budgets = tuple(budgets)
    if not budgets or budgets[0] < 2 or any(a >= b for a, b in zip(budgets, budgets[1:])) or budgets[-1] > len(pool_labels):
        raise ValueError('Budgets must strictly increase within the available pool')
    initial_rng = np.random.default_rng(seed)
    acquisition_rng = np.random.default_rng(seed + 10000)
    selected = initial_rng.choice(len(pool_labels), budgets[0], replace=False).tolist()
    oracle = PoolOracle(pool_labels)
    oracle.acquire(selected)
    history = [{'seed':seed, 'strategy':strategy, 'label_budget':budgets[0], 'pool_index':i,
                'observed_log_brightness':float(oracle.labels([i])[0]), 'acquisition':'initial_random'} for i in selected]
    records = []
    for step, budget in enumerate(budgets):
        if len(selected) != budget:
            raise RuntimeError('Acquired labels do not equal the declared budget')
        model = model_factory(seed + budget)
        model.fit(pool_features[selected], oracle.labels(selected))
        for name, (features, labels) in evaluation.items():
            records.append({'seed':seed, 'strategy':strategy, 'label_budget':budget,
                            'evaluation':name, 'n_evaluation':len(labels), **scores(labels, model.predict(features))})
        if step + 1 < len(budgets):
            available = np.setdiff1d(np.arange(len(pool_labels)), np.array(selected))
            acquired = choose_acquisition(strategy, available, selected, pool_features,
                                          pool_codes, model, budgets[step+1]-budget, acquisition_rng)
            oracle.acquire(acquired)
            selected.extend(acquired.tolist())
            history.extend({'seed':seed, 'strategy':strategy, 'label_budget':budgets[step+1],
                            'pool_index':int(i), 'observed_log_brightness':float(oracle.labels([i])[0]),
                            'acquisition':strategy} for i in acquired)
    return records, history


def write_csv(path, rows):
    with Path(path).open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)


def aggregate(records):
    rows = []
    for evaluation in ('local_test', 'distant_test'):
        for strategy in STRATEGIES:
            for budget in BUDGETS:
                selected = [r for r in records if r['evaluation']==evaluation and r['strategy']==strategy and r['label_budget']==budget]
                item = {'evaluation':evaluation, 'strategy':strategy, 'label_budget':budget, 'repeated_seeds':len(selected)}
                for metric in ('rmse', 'mae', 'spearman_rho'):
                    values = np.array([r[metric] for r in selected if r[metric] is not None])
                    item[metric+'_mean'] = float(values.mean()) if len(values) else None
                    item[metric+'_sd_descriptive'] = float(values.std(ddof=1)) if len(values)>1 else None
                rows.append(item)
    return rows


def draw_learning_curves(summary, reference, target):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors = {'random':'#986326', 'uncertainty_diversity':'#156d83'}
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.6), layout='constrained')
    for column, evaluation in enumerate(('local_test', 'distant_test')):
        for row_index, metric in enumerate(('rmse', 'spearman_rho')):
            ax = axes[row_index, column]
            for strategy in STRATEGIES:
                rows = [r for r in summary if r['evaluation']==evaluation and r['strategy']==strategy]
                x = np.array([r['label_budget'] for r in rows])
                y = np.array([r[metric+'_mean'] for r in rows], dtype=float)
                sd = np.array([r[metric+'_sd_descriptive'] for r in rows], dtype=float)
                ax.plot(x, y, 'o-', color=colors[strategy], label=strategy.replace('_',' '))
                ax.fill_between(x, y-sd, y+sd, color=colors[strategy], alpha=.12)
            value = next(r[metric] for r in reference if r['evaluation']==evaluation)
            ax.axhline(value, color='#666666', linestyle='--', linewidth=1, label='all-pool-label reference')
            ax.set(xlabel='Revealed pool labels', ylabel='RMSE (log-brightness units)' if metric=='rmse' else 'Spearman rank correlation',
                   title=evaluation.replace('_',' ') if row_index==0 else None)
            ax.spines[['top','right']].set_visible(False)
            ax.grid(alpha=.2)
            if row_index==0 and column==0: ax.legend(fontsize=8)
    fig.suptitle('Retrospective GFP acquisition · means ± descriptive SD across 4 seeds',fontsize=14)
    fig.savefig(target, dpi=160, metadata={'Software':'gfp-active-learning 0.1.0'})
    plt.close(fig)


def run(data_dir, output_dir):
    rows, manifest = load_dataset(data_dir)
    output_dir = Path(output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    codes = encode_sequences([r['sequence'] for r in rows])
    labels = np.array([float(r['log_brightness']) for r in rows])
    features = descriptors(codes, [int(r['mutation_count']) for r in rows])
    mask = {role:np.array([r['role']==role for r in rows]) for role in ('pool','local_test','distant_test')}
    pool_rows = [r for r in rows if r['role']=='pool']
    pool_x, pool_codes, pool_y = features[mask['pool']], codes[mask['pool']], labels[mask['pool']]
    evaluation = {role:(features[mask[role]], labels[mask[role]]) for role in ('local_test','distant_test')}
    distance_rows = []
    for role in ('local_test','distant_test'):
        minimum = np.rint(nearest_hamming(codes[mask[role]], pool_codes) * codes.shape[1])
        distance_rows.append({'evaluation':role, 'n':int(mask[role].sum()),
                              'nearest_pool_mismatches_min':float(minimum.min()),
                              'nearest_pool_mismatches_median':float(np.median(minimum)),
                              'nearest_pool_mismatches_max':float(minimum.max())})
    records, history = [], []
    for seed in SEEDS:
        for strategy in STRATEGIES:
            result, queries = simulate(pool_x, pool_codes, pool_y, evaluation, strategy, seed)
            records.extend(result)
            for query in queries:
                query['record_id'] = pool_rows[query['pool_index']]['record_id']
                query['sequence_sha256'] = pool_rows[query['pool_index']]['sequence_sha256']
            history.extend(queries)
    summary = aggregate(records)
    reference_model = make_model(2026).fit(pool_x, pool_y)
    reference = [{'evaluation':name, 'labels_used':len(pool_y), **scores(y, reference_model.predict(x))} for name,(x,y) in evaluation.items()]
    paired = []
    for evaluation_name in evaluation:
        for seed in SEEDS:
            rand = next(r for r in records if r['evaluation']==evaluation_name and r['seed']==seed and r['strategy']=='random' and r['label_budget']==BUDGETS[-1])
            active = next(r for r in records if r['evaluation']==evaluation_name and r['seed']==seed and r['strategy']=='uncertainty_diversity' and r['label_budget']==BUDGETS[-1])
            paired.append({'evaluation':evaluation_name,'seed':seed,'label_budget':BUDGETS[-1],
                           'rmse_difference_active_minus_random':active['rmse']-rand['rmse']})
    write_csv(output_dir/'learning_curves.csv',records)
    write_csv(output_dir/'learning_summary.csv',summary)
    write_csv(output_dir/'query_history.csv',history)
    write_csv(output_dir/'distance_audit.csv',distance_rows)
    write_csv(output_dir/'all_pool_reference.csv',reference)
    write_csv(output_dir/'paired_final_differences.csv',paired)
    report = {'version':'0.1.0','mode':'retrospective pool-based active learning on already measured observations',
              'data_sha256':manifest['dataset_sha256'], 'data_roles':{r:int(m.sum()) for r,m in mask.items()},
              'feature_count':int(features.shape[1]),'feature_definition':'20 residue fractions + source reference-relative substitution count',
              'budgets':list(BUDGETS),'seeds':list(SEEDS), 'strategies':list(STRATEGIES),
              'forest':reference_model.get_params(),
              'model_seed_rule':'Simulation fits use seed + label_budget; all-pool reference uses 2026',
              'uncertainty_scope':'Tree disagreement is an acquisition heuristic, not calibrated epistemic or aleatoric uncertainty',
              'evaluation_scope':'Fixed related-sequence local and mutation-distance test subsets; no novel protein-family or prospective generalization claim',
              'paired_difference_scope':'Paired random-seed differences are descriptive; shared pool/test outcomes preclude independent-study interpretation',
              'versions':{p:importlib.metadata.version(p) for p in ('numpy','scipy','scikit-learn','matplotlib')}}
    (output_dir/'run_metadata.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    draw_learning_curves(summary,reference,output_dir/'learning_curves.png')
    text = ['# Retrospective GFP acquisition: current run','',
            'All labels already existed before this simulation. Acquisition reveals stored observations; it performs no new experiment and creates no new sequence.','',
            '| Evaluation | Policy | Labels | Mean RMSE | Descriptive SD | Mean Spearman |',
            '| --- | --- | ---: | ---: | ---: | ---: |']
    text += [f"| {r['evaluation']} | {r['strategy']} | {r['label_budget']} | {r['rmse_mean']:.4f} | {r['rmse_sd_descriptive']:.4f} | {r['spearman_rho_mean']:.4f} |" for r in summary if r['label_budget']==BUDGETS[-1]]
    text += ['', '![Learning curves](learning_curves.png)','',
             'Shading is one descriptive SD over four random seeds, not a confidence interval. Policies share each seed’s initial labeled set. Local and distant evaluation sequences remain outside the acquisition pool.', '',
             'The dashed reference uses all 2,400 pool labels with the same model family. It is not an attainable guarantee or a mathematical performance bound.', '',
             'The distant split has at least four source-reported substitutions; pool/local-test sequences have at most three. Nearby sequences can still occur across this boundary; see `distance_audit.csv`. Residue composition discards position information and the forest cannot extrapolate the mutation-count feature beyond its training range.', '',
             'A favorable seed or average does not establish a reliable laboratory advantage. Tree disagreement is not calibrated uncertainty, and these measured-pool results do not include assay costs, failures, new noise, or changes in biology. See [methods](../docs/methods.md).','']
    (output_dir/'report.md').write_text('\n'.join(text))
    return report
