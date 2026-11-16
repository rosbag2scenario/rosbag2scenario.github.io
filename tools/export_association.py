"""Export the archived Zhu-inspired gate sweep; no new experiment is run.

Usage: python3 tools/export_association.py --study PATH --output data/association.json
PATH is the town10-gap-checks-20261112 study directory.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def export(study, output):
    sweep_path = study / 'out/rejoin_sweep.json'
    pairs_path = study / 'out/rejoin_pairs.csv'
    sweep = json.loads(sweep_path.read_text())
    with pairs_path.open() as stream:
        pairs = list(csv.DictReader(stream))
    assert len(pairs) == 111
    assert sum(p['motion'] == 'moving' for p in pairs) == 56
    rows = []
    for distance in (5, 10):
        for gate in (2, 5):
            matches = [r for r in sweep['sweep'] if r['gate_s'] == gate and r['dist_m'] == distance]
            assert len(matches) == 1
            row = matches[0]
            fine = [r for r in sweep['fine'] if r['gate_s'] == gate and r['dist_m'] == distance]
            assert fine == [row]
            assert row['rejoined'] == row['moving'] + row['stationary']
            rows.append(row | {'source': 'paper_table_ii' if distance == 5 else 'archived_supplementary_sweep'})
    assert [(r['rejoined'], r['moving'], r['links']['wrong']) for r in rows[:2]] == [(58, 17, 2), (62, 15, 8)]
    result = {
        'population': {'all': 111, 'moving': 56, 'near_stationary': 55, 'drives': 3},
        'method': 'Zhu-inspired proximity association; greedy one-to-one links ordered by endpoint distance and then time gap.',
        'definitions': {
            'gates': 'Strict upper bounds on elapsed time and smoothed XY endpoint distance.',
            'rejoined': 'The two fragments of a benchmark gap occur in the same output chain; the chain can contain other wrong links.',
            'wrong_links': 'Links between different ground-truth vehicle identities across the full candidate pool, not only the 111 benchmark gaps.',
            'unscorable': 'At least one endpoint lacks a supported ground-truth identity; excluded from correct/wrong link counts.'
        },
        'rows': rows,
        'provenance': {
            'study': study.name,
            'execution': 'Existing archived sweep; no new run for the website. Its script checks both 5 m rows against all 111 published pair outcomes and checks the coarse sweep links against the baseline implementation.',
            'files': {str(p.relative_to(study)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (sweep_path, pairs_path, study / 'scripts/rejoin.py', study / 'scripts/common_local.py')}
        }
    }
    output.write_text(json.dumps(result, indent=2) + '\n')
    for r in rows:
        print(f"{r['gate_s']:g} s / {r['dist_m']:g} m: {r['rejoined']} rejoined, {r['moving']} moving, {r['links']['wrong']} wrong")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    export(args.study, args.output)
