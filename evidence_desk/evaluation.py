"""Reproducible validator ablation on transparent, authored synthetic candidates."""
from __future__ import annotations
import csv
import io
import json
from pathlib import Path
import platform
import time
from .core import ROOT, DEFAULT_AS_OF, digest, load_corpus, validate_candidate


def evaluate() -> dict:
    corpus_path, benchmark_path = ROOT/'data'/'documents.json', ROOT/'data'/'benchmark.json'
    benchmark = json.loads(benchmark_path.read_text())
    documents = load_corpus()
    rows = []
    started = time.perf_counter()
    for case in benchmark['cases']:
        checked = validate_candidate(case['candidate'], documents, DEFAULT_AS_OF)
        # Pass-through baseline deliberately has no verifier and executes no tools.
        baseline_status = 'VERIFIED'
        rows.append({**case, 'baseline_status': baseline_status, 'checked_status': checked['status'],
                     'issues': checked['issues'], 'baseline_correct': baseline_status == case['expected_status'],
                     'checked_correct': checked['status'] == case['expected_status']})
    elapsed = (time.perf_counter()-started)*1000
    safe = [r for r in rows if r['safe_to_accept']]
    unsafe = [r for r in rows if not r['safe_to_accept']]
    def metrics(key):
        accepted_safe = sum(r[key] == 'VERIFIED' for r in safe)
        unsafe_accepted = sum(r[key] == 'VERIFIED' for r in unsafe)
        return {'decision_correct': sum(r[key] == r['expected_status'] for r in rows), 'total': len(rows),
                'unsafe_accepted': unsafe_accepted, 'unsafe_total': len(unsafe),
                'supported_accepted': accepted_safe, 'supported_total': len(safe),
                'false_abstentions': len(safe)-accepted_safe}
    return {'dataset': benchmark['dataset'], 'provenance': benchmark['provenance'], 'as_of': DEFAULT_AS_OF,
            'python': platform.python_version(), 'corpus_sha256': digest(corpus_path.read_text()),
            'benchmark_sha256': digest(benchmark_path.read_text()), 'elapsed_ms': round(elapsed, 3),
            'baseline': metrics('baseline_status'), 'checked': metrics('checked_status'), 'cases': rows,
            'limitations': ['Small, author-controlled synthetic set; not real-world or model-quality evidence.',
                            'Pass-through ablation baseline, not a competing LLM system.',
                            'No live LLM, PDF/OCR pipeline, on-chain integration, deployment or users tested.',
                            'A forecast-qualified document still passes: exact arithmetic is not semantic entailment.',
                            'Supported paraphrased evidence is rejected: narrow grammar sacrifices recall.']}


def save_report(destination: Path) -> dict:
    destination.mkdir(parents=True, exist_ok=True)
    report = evaluate()
    (destination/'evaluation.json').write_text(json.dumps(report, indent=2)+'\n')
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'category', 'expected_status', 'baseline_status', 'checked_status', 'safe_to_accept', 'issues'])
    for row in report['cases']:
        writer.writerow([row[k] for k in ['id','category','expected_status','baseline_status','checked_status','safe_to_accept']] + [','.join(i['code'] for i in row['issues'])])
    (destination/'evaluation.csv').write_text(output.getvalue())
    lines = ['# Evaluation results', '', 'Command: `python -m evidence_desk evaluate --output artifacts`', '',
             f"Dataset: `{report['dataset']}` · {report['as_of']} · Python {report['python']}", '',
             'These are hand-authored synthetic candidate replays, not live model outputs or a held-out benchmark.', '',
             '| Metric | Pass-through baseline | Checked pipeline |', '|---|---:|---:|']
    for label, key, denominator in [('Decision agreement','decision_correct','total'),('Unsafe candidates accepted ↓','unsafe_accepted','unsafe_total'),('Supported candidates accepted ↑','supported_accepted','supported_total')]:
        lines.append(f"| {label} | {report['baseline'][key]}/{report['baseline'][denominator]} | {report['checked'][key]}/{report['checked'][denominator]} |")
    lines += ['', '## Failures retained in the benchmark', '']
    for row in report['cases']:
        if not row['checked_correct']:
            lines += [f"- **{row['name']}**: expected {row['expected_status']}; got {row['checked_status']}. {row['rationale']}"]
    lines += ['', '## Limits', ''] + ['- '+x for x in report['limitations']]
    lines += ['', '## Reproducibility', '', f"- Corpus SHA-256: `{report['corpus_sha256']}`", f"- Benchmark SHA-256: `{report['benchmark_sha256']}`", '- Wall time is diagnostic only; no latency or throughput claim is made.']
    (destination/'evaluation.md').write_text('\n'.join(lines)+'\n')
    return report
