"""Export final-budget predictions and independently reconstruct their metrics."""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import zlib
import numpy as np

from .audit import audit, integer, number, read_table, require
from .benchmark import BUDGETS, SEEDS, STRATEGIES, make_model
from .data import load_dataset, descriptors, encode_sequences

FIELDS = ['seed','strategy','label_budget','evaluation','record_id','predicted_log_brightness']
RTOL, ATOL = 1e-8, 1e-10


def mean_ranks(values):
    values = np.asarray(values, dtype=float)
    order = np.argsort(values, kind='stable'); result = np.empty(len(values))
    start = 0
    while start < len(order):
        stop = start + 1
        while stop < len(order) and values[order[stop]] == values[order[start]]: stop += 1
        result[order[start:stop]] = (start + 1 + stop)/2
        start = stop
    return result


def independent_metrics(truth, prediction):
    truth, prediction = np.asarray(truth,dtype=float),np.asarray(prediction,dtype=float)
    require(truth.ndim == 1 and truth.shape == prediction.shape and len(truth)>0, 'Invalid scoring shape')
    require(np.isfinite(truth).all() and np.isfinite(prediction).all(), 'Nonfinite scoring value')
    errors = [float(a-b) for a,b in zip(truth,prediction)]
    a,b=mean_ranks(truth),mean_ranks(prediction)
    a-=a.mean();b-=b.mean()
    denom=math.sqrt(float(a@a)*float(b@b))
    rho=None if denom==0 else max(-1.,min(1.,float(a@b)/denom))
    return {'rmse':math.sqrt(math.fsum(e*e for e in errors)/len(errors)),
            'mae':math.fsum(abs(e) for e in errors)/len(errors),'spearman_rho':rho}


def export_predictions(data_dir, results_dir, out):
    data_dir,results_dir,out=Path(data_dir),Path(results_dir),Path(out)
    require(out.resolve() not in {data_dir.resolve(),results_dir.resolve()}, 'Use a separate prediction directory')
    audit(data_dir,results_dir)
    rows,source=load_dataset(data_dir)
    pool=[r for r in rows if r['role']=='pool']
    features=descriptors(encode_sequences([r['sequence'] for r in pool]),[int(r['mutation_count']) for r in pool])
    labels=np.array([float(r['log_brightness']) for r in pool])
    history=read_table(results_dir/'query_history.csv')
    predictions=[]
    for seed in SEEDS:
        for policy in STRATEGIES:
            chosen=[integer(r['pool_index']) for r in history if integer(r['seed'])==seed and r['strategy']==policy]
            model=make_model(seed+BUDGETS[-1]).fit(features[chosen],labels[chosen])
            for role in ('local_test','distant_test'):
                evaluation=[r for r in rows if r['role']==role]
                x=descriptors(encode_sequences([r['sequence'] for r in evaluation]),[int(r['mutation_count']) for r in evaluation])
                for record,predicted in zip(evaluation,model.predict(x)):
                    predictions.append(dict(zip(FIELDS,[seed,policy,BUDGETS[-1],role,record['record_id'],float(predicted)])))
    text=io.StringIO(newline='');writer=csv.DictWriter(text,fieldnames=FIELDS,lineterminator='\n');writer.writeheader();writer.writerows(predictions)
    compressed=gzip.compress(text.getvalue().encode('utf-8'),mtime=0)
    out.mkdir(parents=True,exist_ok=True)
    (out/'final_predictions.csv.gz').write_bytes(compressed)
    manifest={'schema':'gfp-final-predictions/1','rows':len(predictions),'label_budget':BUDGETS[-1],
              'data_sha256':source['dataset_sha256'],'prediction_sha256':hashlib.sha256(compressed).hexdigest(),
              'source_result_sha256':{name:hashlib.sha256((results_dir/name).read_bytes()).hexdigest()
                                     for name in ('query_history.csv','learning_curves.csv','run_metadata.json')},
              'model_seed_rule':'seed + final label budget',
              'scope':'Stored evaluation predictions only; source labels are joined during verification. No new acquisition or biological experiment.'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return verify_predictions(data_dir,results_dir,out)


def verify_predictions(data_dir, results_dir, directory):
    data_dir,results_dir,directory=Path(data_dir),Path(results_dir),Path(directory)
    audit(data_dir,results_dir)
    data,source=load_dataset(data_dir)
    manifest=json.loads((directory/'manifest.json').read_text())
    require(manifest['schema']=='gfp-final-predictions/1' and manifest['label_budget']==BUDGETS[-1], 'Unsupported prediction manifest')
    require(manifest['data_sha256']==source['dataset_sha256'], 'Prediction source hash differs')
    for name in ('query_history.csv','learning_curves.csv','run_metadata.json'):
        require(manifest['source_result_sha256'][name]==hashlib.sha256((results_dir/name).read_bytes()).hexdigest(), 'Source result hash differs')
    with (directory/'final_predictions.csv.gz').open('rb') as stream:
        raw=stream.read(4_000_001)
    require(len(raw)<=4_000_000 and hashlib.sha256(raw).hexdigest()==manifest['prediction_sha256'], 'Prediction fingerprint or size differs')
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream: decoded=stream.read(4_000_001)
    require(len(decoded)<=4_000_000,'Expanded predictions exceed limit')
    reader=csv.DictReader(io.StringIO(decoded.decode('utf-8')))
    require(reader.fieldnames==FIELDS,'Prediction columns differ')
    records=list(reader)
    require(len(records)==manifest['rows'],'Prediction row count differs')
    sources={r['record_id']:r for r in data if r['role']!='pool'}
    expected={(s,p,BUDGETS[-1],role,rid) for s in SEEDS for p in STRATEGIES
              for rid,r in sources.items() for role in [r['role']]}
    groups={};seen=set()
    for r in records:
        require(None not in r and None not in r.values(),'Malformed prediction row')
        key=(integer(r['seed']),r['strategy'],integer(r['label_budget']),r['evaluation'],r['record_id'])
        require(key in expected and key not in seen,'Unknown, wrong-role or duplicate prediction key')
        seen.add(key);groups.setdefault(key[:4],[]).append((float(sources[key[4]]['log_brightness']),number(r['predicted_log_brightness'])))
    require(seen==expected,'Missing final prediction records')
    baselines={ (integer(r['seed']),r['strategy'],integer(r['label_budget']),r['evaluation']):r
               for r in read_table(results_dir/'learning_curves.csv') if integer(r['label_budget'])==BUDGETS[-1] }
    metrics=[];all_agree=True
    for key,pairs in sorted(groups.items()):
        result=independent_metrics(*zip(*pairs));reference=baselines[key]
        matches=[]
        for name,value in result.items():
            matches.append(reference[name]=='' if value is None else reference[name]!='' and math.isclose(value,number(reference[name]),rel_tol=RTOL,abs_tol=ATOL))
        agrees=all(matches);all_agree=all_agree and agrees
        metrics.append(dict(zip(['seed','strategy','label_budget','evaluation'],key)) | result | {'n_evaluation':len(pairs),'agrees_with_saved_metrics':agrees})
    with (directory/'recomputed_metrics.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(metrics[0]),lineterminator='\n');writer.writeheader();writer.writerows(metrics)
    report={'schema':'gfp-final-prediction-verification/1','status':'passed' if all_agree else 'failed',
            'prediction_rows':len(records),'metric_rows':len(metrics),'rtol':RTOL,'atol':ATOL,
            'prediction_sha256':manifest['prediction_sha256'],'data_sha256':source['dataset_sha256'],
            'method':'Join source outcomes by record ID; independently compute errors and average-tie rank correlation.',
            'limits':['Predictions were generated by the same declared final-budget model family.',
                      'Agreement verifies numerical reporting, not biological validity, calibration or unseen-family generalization.']}
    (directory/'verification.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    for command in ('export','verify'):
        p=sub.add_parser(command);p.add_argument('--data-dir',type=Path,default=Path('data'))
        p.add_argument('--results-dir',type=Path,default=Path('results'))
        p.add_argument('--directory',type=Path,default=Path('examples/final-predictions'))
    args=parser.parse_args(argv)
    try:
        function=export_predictions if args.command=='export' else verify_predictions
        report=function(args.data_dir,args.results_dir,args.directory)
        print(json.dumps(report,indent=2));return 0 if report['status']=='passed' else 1
    except (ValueError,OSError,KeyError,TypeError,EOFError,zlib.error) as error:
        print(f'Prediction verification stopped: {error}',file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
