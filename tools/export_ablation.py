"""Verify and export the existing end-aware completion ablation; no new runs."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path


def export(cases_path, scores_path, diagnostic_code, output):
    cases = [r for r in json.loads(gzip.decompress(cases_path.read_bytes()))
             if r['kind'] == 'natural_output_gap' and r['status'] == 'scored']
    scores = {(r['seed'], r['tracklet']): r for r in json.loads(scores_path.read_text())}
    assert len(cases) == len(scores) == 111
    records = []
    for index, case in enumerate(cases):
        saved = scores[case['case'], case['tracklet']]
        assert len(case['error_m']['joint']) == saved['n']
        assert all(abs(a - b) < 1e-10 for a, b in zip(case['error_m']['joint'], saved['errors']['joint']))
        methods = {}
        for name in ['joint_uniform', 'joint']:
            errors = case['error_m'][name]
            assert len(errors) == saved['n']
            methods[name] = dict(samples=len(errors), sum_squared_error=sum(e * e for e in errors),
                                 accepted=case['flags'][name]['accepted'])
        records.append(dict(case=f'T{index + 1:03d}', motion=saved['motion'], methods=methods))
    summary = {}
    for group in ['all', 'moving', 'near_stationary']:
        selected = [r for r in records if group == 'all' or r['motion'] == group]
        methods = {}
        for name in ['joint_uniform', 'joint']:
            samples = sum(r['methods'][name]['samples'] for r in selected)
            methods[name] = dict(samples=samples,
                rmse_m=math.sqrt(sum(r['methods'][name]['sum_squared_error'] for r in selected) / samples),
                rejected=sum(not r['methods'][name]['accepted'] for r in selected))
        summary[group] = dict(gaps=len(selected), methods=methods)
    assert summary['moving']['gaps'] == 56
    assert summary['all']['methods']['joint']['samples'] == 3296
    assert [round(summary[g]['methods']['joint_uniform']['rmse_m'], 2) for g in ['all', 'moving']] == [.93, 1.02]
    assert [round(summary[g]['methods']['joint']['rmse_m'], 2) for g in ['all', 'moving']] == [.88, .96]
    output.write_text(json.dumps(dict(
        scope='Correct fragment pairs supplied; same inputs and completion method; all 111 gaps including rejected fits.',
        ablation='joint_uniform disables the extra observation uncertainty near trajectory starts and ends; joint retains end-aware weighting.',
        summary=summary, per_case=records,
        provenance=dict(execution='Recomputed aggregates from existing per-sample errors; no reconstruction or simulator rerun.',
            source_sha256={name: hashlib.sha256(p.read_bytes()).hexdigest() for name, p in
                [('cases.json.gz', cases_path), ('fill_cases.json', scores_path), ('run_gap_diagnostics.py', diagnostic_code)]})
    ), indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['cases', 'scores', 'diagnostic-code', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    export(a.cases, a.scores, a.diagnostic_code, a.output)
