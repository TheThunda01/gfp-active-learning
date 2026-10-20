"""Rebuild the label-blind subset from checksum-pinned public source files.

This reconstructs already measured source records only; it proposes no variants.
The default analysis uses the included CSV and never downloads these sources.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'source_fluorescence.tar.gz': ('https://s3.amazonaws.com/songlabdata/proteindata/data_raw_pytorch/fluorescence.tar.gz', '3c7caffd28a40f0dc8791fa311f90af4423654bd90c72fdc1e5bb191c79e175a'),
    'amino_acid_genotypes_to_brightness.tsv': ('https://ndownloader.figshare.com/files/4820647', '5581230b9888f9960708a4769ce1c9b4453561f0b5f0374525445b4a984d54d5'),
}
MEMBER_HASHES = {
    'train': '0a57cc0d1424ae67777bf3f836b559acab7f73063f6a928ddb833eb04640a156',
    'valid': '7aab37c3b7ff18553d16ce172b828178ecd7fd4968e9b29852192953f9b90a0f',
    'test': '54880bbf5007a2fcdcd4c512a595183a938b8f0ef03e4a254554b09aa865c7b4',
}
AA = set('ACDEFGHIKLMNPQRSTVWY')

def read_source(cache, name, download):
    path = cache / name
    url, expected = SOURCES[name]
    if not path.exists():
        if not download:
            raise ValueError(f'Missing {path}; pass --download to obtain pinned sources')
        with urllib.request.urlopen(url, timeout=60) as response:
            raw = response.read(20_000_001)
        if len(raw) > 20_000_000:
            raise ValueError('Source exceeds the 20 MB limit')
        cache.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f'Checksum mismatch for {name}; source was not silently updated')
    return raw


def build(cache, output, download=False):
    archive = read_source(cache, 'source_fluorescence.tar.gz', download)
    raw_table = read_source(cache, 'amino_acid_genotypes_to_brightness.tsv', download)
    splits = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tar:
        for split, expected in MEMBER_HASHES.items():
            raw = tar.extractfile(f'fluorescence/fluorescence_{split}.json').read()
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError(f'Member checksum mismatch: {split}')
            splits[split] = json.loads(raw)
    wt = [row['primary'] for row in splits['train'] if row['num_mutations'] == 0]
    if len(wt) != 1 or len(wt[0]) != 237:
        raise ValueError('Expected one recorded 237-residue reference in TAPE training data')
    original, excluded_stops = {}, 0
    for line, row in enumerate(csv.DictReader(io.StringIO(raw_table.decode()), delimiter='\t'), 2):
        sequence = list(wt[0])
        for token in filter(None, row['aaMutations'].split(':')):
            match = re.fullmatch(r'S([A-Z])([0-9]+)([A-Z*])', token)
            if not match:
                raise ValueError(f'Unrecognized original substitution token at line {line}')
            before, position, after = match.groups()
            position = int(position)
            if sequence[position] != before:
                raise ValueError(f'Original reference disagreement at line {line}')
            sequence[position] = after
        sequence = ''.join(sequence)
        if '*' in sequence:
            excluded_stops += 1
            continue
        if sequence in original:
            raise ValueError('Duplicate source amino-acid sequence')
        original[sequence] = {'label': row['medianBrightness'], 'original_line': line}
    candidates = {'pool': [], 'test': []}
    seen, max_difference, source_counts = set(), 0.0, {}
    for split, rows in splits.items():
        retained = 0
        for index, row in enumerate(rows):
            sequence = row['primary']
            if len(sequence) != 237 or set(sequence) - AA:
                continue
            if sequence in seen or sequence not in original:
                raise ValueError('Duplicate or unmapped full-length TAPE sequence')
            seen.add(sequence)
            source = original[sequence]
            difference = abs(float(source['label']) - float(row['log_fluorescence'][0]))
            if difference > 1e-6:
                raise ValueError('Original and TAPE phenotype do not agree within float precision')
            max_difference = max(max_difference, difference)
            role = 'test' if split == 'test' else 'pool'
            candidates[role].append({
                'record_id': f'{split}_{index}', 'role': role, 'source_split': split,
                'source_index': index, 'original_table_line': source['original_line'],
                'sequence': sequence, 'mutation_count': row['num_mutations'],
                'log_brightness': source['label'], 'sequence_sha256': hashlib.sha256(sequence.encode()).hexdigest(),
            })
            retained += 1
        source_counts[split] = {'raw_rows': len(rows), 'full_length_mapped_rows': retained}
    selected = []
    for role, count in [('pool', 2800), ('test', 800)]:
        ranked = sorted(candidates[role], key=lambda r: hashlib.sha256(('gfp-active-learning-v1|' + r['sequence']).encode()).hexdigest())
        for index, row in enumerate(ranked[:count]):
            row = dict(row)
            row['role'] = ('pool' if index < 2400 else 'local_test') if role == 'pool' else 'distant_test'
            selected.append(row)
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'dataset.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(selected[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(selected)
    raw = (output / 'dataset.csv').read_bytes()
    manifest = {
        'schema_version': '1.0', 'dataset': 'Sarkisyan 2016 avGFP, original phenotype with TAPE split membership',
        'source_dataset_doi': '10.6084/m9.figshare.3102154.v1', 'source_study_doi': '10.1038/nature17995',
        'original_data_license': 'CC BY 4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
        'sources': {name: {'url': url, 'sha256': sha} for name, (url, sha) in SOURCES.items()},
        'tape_member_sha256': MEMBER_HASHES, 'source_counts': source_counts,
        'original_full_length_sequences_mapped': len(original), 'original_stop_containing_rows_excluded': excluded_stops,
        'max_original_vs_tape_label_difference': max_difference,
        'subset': {'pool': 2400, 'local_test': 400, 'distant_test': 800, 'sequence_length': 237,
                   'selection': 'Train+valid ranked by SHA256(gfp-active-learning-v1| + sequence): first 2400 pool, next 400 local_test; test ranked separately: first 800 distant_test; no labels used',
                   'pool_source_splits': ['train', 'valid'], 'local_test_source_splits': ['train', 'valid'], 'distant_test_source_splits': ['test']},
        'phenotype': 'Original amino-acid-level medianBrightness: median log-brightness across associated barcodes; TAPE float32 labels verified within 1e-6',
        'dataset_sha256': hashlib.sha256(raw).hexdigest(), 'dataset_bytes': len(raw),
        'verified_on': '2026-10-20',
    }
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'rows': len(selected), 'dataset_sha256': manifest['dataset_sha256'], 'source_counts': source_counts}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / '.source-cache')
    parser.add_argument('--output', type=Path, default=ROOT / 'data')
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    build(args.cache, args.output, args.download)
