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


def figure(summary,target):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors={'random':'#777777','uncertainty_only':'#bf6726','diversity_only':'#79599a','combined':'#167d90'}
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained',sharex=True)
    for ax,role in zip(axes,EVALUATIONS):
        for policy in POLICIES:
            rows=[r for r in summary if r['evaluation']==role and r['policy']==policy]
            x=np.array([r['label_budget'] for r in rows]);y=np.array([r['rmse_mean'] for r in rows]);sd=np.array([r['rmse_sd_descriptive'] for r in rows])
            ax.plot(x,y,'o-',color=colors[policy],label=policy.replace('_',' '))
            ax.fill_between(x,y-sd,y+sd,color=colors[policy],alpha=.10)
        ax.set(title=role.replace('_',' '),xlabel='Revealed pool labels',ylabel='RMSE (source log-brightness scale)')
        ax.spines[['top','right']].set_visible(False);ax.grid(alpha=.2)
    axes[0].legend(fontsize=8)
    fig.suptitle('Four acquisition policies · same initial labels, budgets and forest\nExploratory reused data; shading is descriptive SD across four seeds',fontsize=12)
    fig.savefig(target,dpi=160);plt.close(fig)


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
    (output/'run_metadata.json').write_text(json.dumps(metadata,indent=2,allow_nan=False)+'\n')
    report=['# GFP policy ablation: learning checkpoint','',
            'Prediction recorded before this ablation: **combined selection would help most on more-distant variants**. No reason was supplied. These are reused historical outcomes, not a new blind holdout.','',
            '| Evaluation | Policy | Final mean RMSE | Descriptive SD |','| --- | --- | ---: | ---: |']
    for r in summary:
        if r['label_budget']==BUDGETS[-1]:report.append(f"| {r['evaluation']} | {r['policy']} | {r['rmse_mean']:.4f} | {r['rmse_sd_descriptive']:.4f} |")
    contrast=float(np.mean([r['distant_minus_local_benefit'] for r in contrasts]))
    distant=[r for r in summary if r['label_budget']==BUDGETS[-1] and r['evaluation']=='distant_test']
    best=min(distant,key=lambda r:r['rmse_mean'])['policy']
    report+=['',f'The lowest distant-set mean RMSE was **{best}**. The mean distant-minus-local combined benefit was **{contrast:+.4f}** RMSE units; positive would favor the predicted distance pattern.',
             '', 'This fixed exploratory extension does not support the recorded combined-at-distance prediction. The result is specific to these outcomes, seeds and model; it is not a general ranking of acquisition algorithms.',
             '', '| Seed | Combined benefit locally | Combined benefit distantly | Distant minus local benefit |',
             '| ---: | ---: | ---: | ---: |']
    report += [f"| {r['seed']} | {r['local_benefit']:+.4f} | {r['distant_benefit']:+.4f} | {r['distant_minus_local_benefit']:+.4f} |" for r in contrasts]
    report += ['', 'Benefit means random RMSE minus combined RMSE; positive is better for combined. The contrast is positive in two seeds and negative in two. Four seeds share the same evaluation observations; these are descriptive comparisons, not a significance test.',
               '', '## Does tree disagreement track error?', '',
               '| Policy | Local mean rank association | Distant mean rank association |',
               '| --- | ---: | ---: |']
    for policy in POLICIES:
        values={r['evaluation']:r['spread_error_spearman_mean'] for r in summary if r['policy']==policy and r['label_budget']==BUDGETS[-1]}
        report.append(f"| {policy} | {values['local_test']:.4f} | {values['distant_test']:.4f} |")
    report += ['', 'Each value averages four separately computed Spearman associations between tree spread and absolute prediction error at the final budget. The observations are reused across seeds. These are heuristic association diagnostics, not calibration, error bars, or confidence-interval coverage.',
               '', 'Spread/error association is much weaker on this distant set. This is consistent with disagreement being a less useful warning of error there, but does not prove why the combined acquisition policy lost. Uncertainty screening can exclude candidates that diversity-only would consider; its causal contribution would need a further fixed comparison.',
               '', '![Learning curves](learning_curves.png)', '',
               'The existing random and combined acquisition orders and metrics were reproduced. Uncertainty-only removes the diversity step; diversity-only removes uncertainty screening. All models still discard residue position, and the distant set extends beyond the pool’s mutation-count range. Neither this ablation nor its reused evaluation labels establish prospective or protein-family generalization.']
    (output/'report.md').write_text('\n'.join(report)+'\n')
    metadata['outputs_sha256']={p.name:sha256(p) for p in output.iterdir() if p.is_file() and p.name!='run_metadata.json'}
    (output/'run_metadata.json').write_text(json.dumps(metadata,indent=2,allow_nan=False)+'\n')
    if any(sha256(ROOT/p)!=value for p,value in protected.items()):raise ValueError('Original benchmark files changed during run')
    return metadata


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,default=HERE/'results');args=parser.parse_args(argv)
    run(args.output_dir);return 0
