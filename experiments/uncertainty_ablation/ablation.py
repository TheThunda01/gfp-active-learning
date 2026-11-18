"""Prespecified, exploratory isolation of GFP acquisition components."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.metadata
import itertools
import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from gfp_active_learning.benchmark import (BUDGETS, SEEDS, PoolOracle, choose_acquisition,
                                           make_model, scores, write_csv)
from gfp_active_learning.data import load_dataset, encode_sequences, descriptors, nearest_hamming

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
POLICIES = ('random', 'uncertainty_only', 'diversity_only', 'combined')
EVALUATIONS = ('local_test', 'distant_test')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rank_association(spread, error):
    spread, error = np.asarray(spread), np.asarray(error)
    if np.std(spread) == 0 or np.std(error) == 0:
        return None
    return float(spearmanr(spread, error).statistic)


def tree_spread(model, features):
    return np.array([tree.predict(features) for tree in model.estimators_]).std(axis=0)


def choose(policy, available, selected, features, codes, model, count, rng):
    available, selected = np.asarray(available, dtype=int), np.asarray(selected, dtype=int)
    if (count < 1 or count > len(available) or len(set(available)) != len(available)
            or set(available) & set(selected) or not len(selected)):
        raise ValueError('Acquisition candidate/count contract failed')
    if policy in ('random', 'combined'):
        original = 'random' if policy == 'random' else 'uncertainty_diversity'
        return choose_acquisition(original, available, selected, features, codes, model, count, rng)
    if policy == 'uncertainty_only':
        spread = tree_spread(model, features[available])
        order = np.lexsort((rng.random(len(available)), -spread))
        return available[order[:count]]
    if policy != 'diversity_only':
        raise ValueError('Unknown ablation policy')
    # No model predictions enter this branch. Random ties are fixed for a batch.
    tie = rng.random(len(available))
    distance = nearest_hamming(codes[available], codes[selected])
    picked = []
    for _ in range(count):
        position = np.lexsort((tie, -distance))[0]
        picked.append(int(available[position]))
        distance = np.minimum(distance, (codes[available] != codes[available[position]]).mean(axis=1))
        distance[np.isin(available, picked)] = -np.inf
    return np.array(picked, dtype=int)


def simulate(features, codes, labels, evaluation, policy, seed, budgets=BUDGETS,
             model_factory=make_model):
    budgets = tuple(budgets)
    if (policy not in POLICIES or not budgets or budgets[0] < 2
            or any(a >= b for a, b in zip(budgets, budgets[1:])) or budgets[-1] > len(labels)):
        raise ValueError('Invalid policy or budgets')
    selected = np.random.default_rng(seed).choice(len(labels), budgets[0], replace=False).tolist()
    rng = np.random.default_rng(seed + 10000)
    oracle = PoolOracle(labels); oracle.acquire(selected)
    history = [{'seed':seed,'policy':policy,'label_budget':budgets[0],'pool_index':i,
                'observed_log_brightness':float(oracle.labels([i])[0]),'acquisition':'initial_random'} for i in selected]
    records, final = [], []
    for step, budget in enumerate(budgets):
        model = model_factory(seed + budget).fit(features[selected], oracle.labels(selected))
        for role, (x, y) in evaluation.items():
            prediction = model.predict(x); spread = tree_spread(model, x)
            error = np.abs(prediction-y)
            records.append({'seed':seed,'policy':policy,'label_budget':budget,'evaluation':role,
                            'n_evaluation':len(y),**scores(y,prediction),
                            'spread_error_spearman':rank_association(spread,error)})
            if step == len(budgets)-1:
                final.extend({'seed':seed,'policy':policy,'label_budget':budget,'evaluation':role,
                              'evaluation_index':i,'prediction':float(p),'tree_sd':float(s),
                              'absolute_error':float(e)} for i,(p,s,e) in enumerate(zip(prediction,spread,error)))
        if step+1 < len(budgets):
            available = np.setdiff1d(np.arange(len(labels)), np.array(selected))
            acquired = choose(policy,available,selected,features,codes,model,budgets[step+1]-budget,rng)
            oracle.acquire(acquired);selected.extend(acquired.tolist())
            history.extend({'seed':seed,'policy':policy,'label_budget':budgets[step+1],'pool_index':int(i),
                            'observed_log_brightness':float(oracle.labels([i])[0]),'acquisition':policy} for i in acquired)
    return records, history, final


def aggregate(records):
    result=[]
    for role,policy,budget in itertools.product(EVALUATIONS,POLICIES,BUDGETS):
        subset=[r for r in records if (r['evaluation'],r['policy'],r['label_budget'])==(role,policy,budget)]
        row={'evaluation':role,'policy':policy,'label_budget':budget,'seeds':len(subset)}
        for metric in ('rmse','mae','spearman_rho','spread_error_spearman'):
            values=[r[metric] for r in subset if r[metric] is not None]
            row[metric+'_mean']=float(np.mean(values)) if values else None
            row[metric+'_sd_descriptive']=float(np.std(values,ddof=1)) if len(values)>1 else None
        result.append(row)
    return result


def historical_checks(records,history,original_dir):
    import csv
    with (original_dir/'learning_curves.csv').open() as handle: old=list(csv.DictReader(handle))
    with (original_dir/'query_history.csv').open() as handle: queries=list(csv.DictReader(handle))
    for policy, original in [('random','random'),('combined','uncertainty_diversity')]:
        for row in [r for r in records if r['policy']==policy]:
            match=next(r for r in old if r['strategy']==original and int(r['seed'])==row['seed']
                       and int(r['label_budget'])==row['label_budget'] and r['evaluation']==row['evaluation'])
            for key in ('rmse','mae','spearman_rho'):
                if not np.isclose(row[key],float(match[key]),rtol=1e-6,atol=1e-7):
                    raise ValueError('Historical metric mismatch')
        for seed in SEEDS:
            actual=[r['record_id'] for r in history if r['policy']==policy and r['seed']==seed]
            expected=[r['record_id'] for r in queries if r['strategy']==original and int(r['seed'])==seed]
            if actual != expected: raise ValueError('Historical acquisition order mismatch')


def figure(summary, target):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    styles = {
        'random': ('#555555', 'o', '--'),
        'uncertainty_only': ('#ac5724', 's', '-.'),
        'diversity_only': ('#675393', '^', ':'),
        'combined': ('#12695d', 'D', '-'),
    }
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), layout='constrained',
                             sharex=True, sharey=True)
    for ax, role in zip(axes, EVALUATIONS):
        for policy, (color, marker, line) in styles.items():
            rows = [r for r in summary if r['evaluation'] == role and r['policy'] == policy]
            x = [r['label_budget'] for r in rows]
            means = np.array([r['rmse_mean'] for r in rows])
            sd = np.array([r['rmse_sd_descriptive'] for r in rows])
            ax.plot(x, means, color=color, marker=marker, linestyle=line,
                    label=policy.replace('_', ' '))
            ax.fill_between(x, means - sd, means + sd, color=color, alpha=.10)
        ax.set(title={'local_test': 'Nearby sequences', 'distant_test': 'More mutated sequences'}[role],
               xlabel='Revealed pool labels', xticks=BUDGETS)
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(axis='y', alpha=.2)
    axes[0].set_ylabel('RMSE (log-brightness units)')
    axes[0].legend(fontsize=8)
    fig.suptitle('Prediction error as more labels are revealed\n'
                 'Lower is better. Shading shows one standard deviation across seeds.', fontsize=12)
    fig.savefig(target, dpi=160)
    plt.close(fig)


def contrast_description(contrasts):
    values = [row['distant_minus_local_benefit'] for row in contrasts]
    positive = sum(value > 0 for value in values)
    negative = sum(value < 0 for value in values)
    tied = len(values) - positive - negative
    mean = sum(values) / len(values)
    direction = ('larger on the distant set' if mean > 0 else
                 'larger on the local set' if mean < 0 else 'equal on the two sets')
    return (f'The mean benefit of combined selection was {direction}. '
            f'The distant-minus-local contrast averaged **{mean:+.4f}** RMSE units. '
            f'Across {len(values)} seeds the counts were {positive} positive, '
            f'{negative} negative, and {tied} tied.')


def write_report(output, summary, contrasts):
    final = [row for row in summary if row['label_budget'] == BUDGETS[-1]]
    report = [
        '# Does combined selection help more at distance?', '',
        'The original prediction was that combined selection would help most on more mutated sequences. '
        f'At {BUDGETS[-1]} revealed labels, each policy was evaluated on the same '
        'historical measurements. Lower root mean squared error (RMSE) means '
        'the predictions were closer to the recorded log-brightness values.', '',
        '| Evaluation | Policy | Mean RMSE | SD across seeds |',
        '| --- | --- | ---: | ---: |',
    ]
    for row in final:
        report.append(f"| {row['evaluation']} | {row['policy']} | {row['rmse_mean']:.4f} | {row['rmse_sd_descriptive']:.4f} |")
    distant = [row for row in final if row['evaluation'] == 'distant_test']
    minimum = min(row['rmse_mean'] for row in distant)
    best = ', '.join(row['policy'].replace('_', ' ') for row in distant if row['rmse_mean'] == minimum)
    report.extend(['', f'**Lowest distant-set mean RMSE ({minimum:.4f})** · {best}.', '',
                   '## Where did combined selection help?', '',
                   'For each seed, subtract the combined policy’s error from random sampling’s error. '
                   'A positive benefit means the combined policy predicted more accurately.', '',
                   contrast_description(contrasts), '',
                   '| Seed | Local benefit | Distant benefit | Distant minus local |',
                   '| ---: | ---: | ---: | ---: |'])
    for row in contrasts:
        report.append(f"| {row['seed']} | {row['local_benefit']:+.4f} | {row['distant_benefit']:+.4f} | {row['distant_minus_local_benefit']:+.4f} |")
    report.extend(['', 'Each seed reuses the same evaluation measurements. The differences describe this historical benchmark.', '',
                   '## Does tree disagreement track error?', '',
                   'Each cell averages the final-budget Spearman correlation across seeds. '
                   'Positive values mean that cases with greater disagreement between trees tended to have larger errors.', '',
                   '| Policy | Nearby sequences | More mutated sequences |',
                   '| --- | ---: | ---: |'])
    for policy in POLICIES:
        values = {r['evaluation']: r['spread_error_spearman_mean'] for r in final if r['policy'] == policy}
        report.append(f"| {policy} | {values['local_test']:.4f} | {values['distant_test']:.4f} |")
    report.extend(['', 'The correlations describe how errors rank within each set. They do not measure calibrated interval coverage.', '', '![Mean prediction error at each budget for nearby and more mutated sequences](learning_curves.png)', '',
                   'The models use composition and mutation count. The distant set extends beyond the pool’s mutation-count range. '
                   'The four policies share their initial labels and budgets within each seed.'])
    (output / 'report.md').write_text('\n'.join(report) + '\n', encoding='utf-8')


def run(output=HERE/'results'):
    output=Path(output)
    if not (HERE/'PLAN.md').is_file():raise ValueError('Write the analysis plan before running')
    protected=json.loads((HERE/'baseline_files.json').read_text())
    if any(sha256(ROOT/p)!=value for p,value in protected.items()):raise ValueError('Original benchmark files changed')
    if any(output.resolve()==p.resolve() or p.resolve() in output.resolve().parents for p in (ROOT/'results',ROOT/'data',ROOT/'gfp_active_learning')):
        raise ValueError('Use a separate experiment output directory')
    rows,data_manifest=load_dataset(ROOT/'data')
    codes=encode_sequences([r['sequence'] for r in rows]);labels=np.array([float(r['log_brightness']) for r in rows])
    features=descriptors(codes,[int(r['mutation_count']) for r in rows])
    role_rows={role:[r for r in rows if r['role']==role] for role in ('pool',*EVALUATIONS)}
    masks={role:np.array([r['role']==role for r in rows]) for role in role_rows}
    evaluation={role:(features[masks[role]],labels[masks[role]]) for role in EVALUATIONS}
    records,history,final=[],[],[]
    for seed,policy in itertools.product(SEEDS,POLICIES):
        print(f'Running {policy}, seed {seed}',flush=True)
        metrics,queries,predictions=simulate(features[masks['pool']],codes[masks['pool']],labels[masks['pool']],evaluation,policy,seed)
        records.extend(metrics)
        for q in queries:
            source=role_rows['pool'][q['pool_index']]
            q.update(record_id=source['record_id'],sequence_sha256=source['sequence_sha256'])
        for p in predictions:
            source=role_rows[p['evaluation']][p.pop('evaluation_index')]
            p.update(record_id=source['record_id'],source_split=source['source_split'])
        history.extend(queries);final.extend(predictions)
    historical_checks(records,history,ROOT/'results')
    summary=aggregate(records);paired=[];contrasts=[];overlap=[]
    final_index={(r['seed'],r['policy'],r['evaluation']):r for r in records if r['label_budget']==BUDGETS[-1]}
    for seed,role,policy in itertools.product(SEEDS,EVALUATIONS,POLICIES[1:]):
        delta=final_index[seed,policy,role]['rmse']-final_index[seed,'random',role]['rmse']
        paired.append({'seed':seed,'evaluation':role,'policy':policy,'label_budget':BUDGETS[-1],
                       'rmse_difference_policy_minus_random':delta,'rmse_benefit_random_minus_policy':-delta})
    for seed in SEEDS:
        benefit={r['evaluation']:r['rmse_benefit_random_minus_policy'] for r in paired if r['seed']==seed and r['policy']=='combined'}
        contrasts.append({'seed':seed,'local_benefit':benefit['local_test'],'distant_benefit':benefit['distant_test'],
                          'distant_minus_local_benefit':benefit['distant_test']-benefit['local_test']})
        sets={p:{r['record_id'] for r in history if r['seed']==seed and r['policy']==p} for p in POLICIES}
        initial={r['record_id'] for r in history if r['seed']==seed and r['policy']=='random' and r['label_budget']==BUDGETS[0]}
        for a,b in itertools.combinations(POLICIES,2):
            extra_a,extra_b=sets[a]-initial,sets[b]-initial
            overlap.append({'seed':seed,'policy_a':a,'policy_b':b,'initial_common':len(initial),
                            'final_intersection':len(sets[a]&sets[b]),'post_initial_jaccard':len(extra_a&extra_b)/len(extra_a|extra_b)})
    output.mkdir(parents=True,exist_ok=True)
    for name,items in [('learning_curves',records),('learning_summary',summary),('query_history',history),
                       ('paired_final',paired),('distance_benefit_contrast',contrasts),('acquisition_overlap',overlap)]:
        write_csv(output/(name+'.csv'),items)
    import csv,io
    text=io.StringIO(newline='');writer=csv.DictWriter(text,fieldnames=list(final[0]),lineterminator='\n');writer.writeheader();writer.writerows(final)
    with (output/'final_predictions.csv.gz').open('wb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='') as archive:archive.write(text.getvalue().encode())
    figure(summary,output/'learning_curves.png')
    metadata={'experiment':'uncertainty_ablation','mode':'exploratory reuse of historical public measurements',
              'user_prediction':'Combined policy will help most on more-distant variants','user_reason':None,
              'plan_sha256':sha256(HERE/'PLAN.md'),'dataset_sha256':data_manifest['dataset_sha256'],
              'split_fingerprints':{role:hashlib.sha256('\n'.join(r['record_id'] for r in items).encode()).hexdigest() for role,items in role_rows.items()},
              'policies':list(POLICIES),'budgets':list(BUDGETS),'seeds':list(SEEDS),'forest':make_model(0).get_params(),
              'model_seed_rule':'seed + budget','historical_random_combined_checks_passed':True,
              'code_sha256':sha256(__file__),'versions':{p:importlib.metadata.version(p) for p in ('numpy','scipy','scikit-learn','matplotlib')}}
    write_report(output, summary, contrasts)
    metadata['outputs_sha256']={p.name:sha256(p) for p in output.iterdir() if p.is_file() and p.name!='run_metadata.json'}
    (output/'run_metadata.json').write_text(json.dumps(metadata,indent=2,allow_nan=False)+'\n')
    if any(sha256(ROOT/p)!=value for p,value in protected.items()):raise ValueError('Original benchmark files changed during run')
    return metadata


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,default=HERE/'results');args=parser.parse_args(argv)
    run(args.output_dir);return 0
