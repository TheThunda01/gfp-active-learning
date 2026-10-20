"""Validate the pinned public subset and compute label-free descriptors."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import numpy as np

AA = 'ACDEFGHIKLMNPQRSTVWY'
FIELDS = ['record_id', 'role', 'source_split', 'source_index', 'original_table_line',
          'sequence', 'mutation_count', 'log_brightness', 'sequence_sha256']
ROLES = ('pool', 'local_test', 'distant_test')


def validate_records(rows):
    if not rows:
        raise ValueError('Dataset must contain records')
    ids, sequences = set(), set()
    for row in rows:
        if row['record_id'] in ids or row['sequence'] in sequences:
            raise ValueError('Duplicate record ID or sequence across data roles')
        ids.add(row['record_id']); sequences.add(row['sequence'])
        if row['role'] not in ROLES:
            raise ValueError('Unknown data role')
        sequence = row['sequence']
        if len(sequence) != 237 or set(sequence) - set(AA):
            raise ValueError('Expected 237 canonical amino acids per sequence')
        if hashlib.sha256(sequence.encode()).hexdigest() != row['sequence_sha256']:
            raise ValueError('Sequence hash mismatch')
        try:
            mutation = int(row['mutation_count'])
            label = float(row['log_brightness'])
        except (ValueError, TypeError) as error:
            raise ValueError('Invalid numeric observation') from error
        if mutation < 0 or str(mutation) != str(row['mutation_count']) or not np.isfinite(label):
            raise ValueError('Nonfinite label or malformed mutation count')
        if row['role'] == 'distant_test':
            if row['source_split'] != 'test' or mutation < 4:
                raise ValueError('Distant evaluation must retain the original test split with >=4 substitutions')
        elif row['source_split'] not in ('train', 'valid') or mutation > 3:
            raise ValueError('Pool and local evaluation must have <=3 substitutions from original train/valid')
    if {row['role'] for row in rows} != set(ROLES):
        raise ValueError('All three separated data roles are required')


def load_dataset(directory):
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text())
    raw = (directory / 'dataset.csv').read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest['dataset_sha256'] or len(raw) != manifest['dataset_bytes']:
        raise ValueError('Dataset checksum or byte count does not match manifest')
    with (directory / 'dataset.csv').open(newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != FIELDS:
            raise ValueError('Dataset columns changed')
        rows = list(reader)
    validate_records(rows)
    for role in ROLES:
        if sum(row['role'] == role for row in rows) != manifest['subset'][role]:
            raise ValueError('Role count does not match manifest')
    return rows, manifest


def encode_sequences(sequences):
    lookup = {letter: i for i, letter in enumerate(AA)}
    if not sequences or not len(sequences[0]) or len({len(sequence) for sequence in sequences}) != 1:
        raise ValueError('Sequences must be nonempty and aligned to one length')
    try:
        return np.array([[lookup[letter] for letter in sequence] for sequence in sequences], dtype=np.uint8)
    except KeyError as error:
        raise ValueError('Noncanonical residue') from error


def descriptors(codes, mutations):
    """20 residue fractions plus known reference-relative substitution count.

    These deliberately coarse descriptors ignore where most residues occur.
    """
    codes, mutations = np.asarray(codes), np.asarray(mutations, dtype=float)
    if codes.ndim != 2 or codes.shape[1] == 0 or mutations.shape != (len(codes),):
        raise ValueError('Descriptor shapes disagree')
    if not np.isfinite(mutations).all() or np.any(mutations < 0) or np.any(mutations != np.floor(mutations)) or not np.isfinite(codes).all() or np.any(codes != np.floor(codes)) or np.any(codes >= len(AA)) or np.any(codes < 0):
        raise ValueError('Invalid residue code or mutation count')
    fractions = np.column_stack([(codes == i).mean(axis=1) for i in range(len(AA))])
    return np.column_stack([fractions, mutations]).astype(np.float32)


def nearest_hamming(query_codes, reference_codes, chunk=16):
    """Minimum mismatch fraction to reference records; no labels enter."""
    query_codes, reference_codes = np.asarray(query_codes), np.asarray(reference_codes)
    if query_codes.ndim != 2 or reference_codes.ndim != 2 or query_codes.shape[1] == 0 or query_codes.shape[1] != reference_codes.shape[1] or not len(reference_codes) or not isinstance(chunk, int) or chunk < 1:
        raise ValueError('Need nonempty equal-width sequence matrices')
    minimum = np.empty(len(query_codes))
    for start in range(0, len(query_codes), chunk):
        distances = (query_codes[start:start+chunk, None, :] != reference_codes[None, :, :]).mean(axis=2)
        minimum[start:start+chunk] = distances.min(axis=1)
    return minimum
