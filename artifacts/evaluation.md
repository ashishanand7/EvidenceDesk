# Evaluation results

Command: `python -m evidence_desk evaluate --output artifacts`

Dataset: `synthetic-adversarial-v1` · 2026-10-01 · Python 3.12.14

These are hand-authored synthetic candidate replays, not live model outputs or a held-out benchmark.

| Metric | Pass-through baseline | Checked pipeline |
|---|---:|---:|
| Decision agreement | 5/19 | 17/19 |
| Unsafe candidates accepted ↓ | 14/14 | 1/14 |
| Supported candidates accepted ↑ | 5/5 | 4/5 |

## Failures retained in the benchmark

- **Forecast mistaken for balance**: expected ABSTAIN; got VERIFIED. KNOWN LIMITATION: numeric labels are forecast figures. The current grammar does not reason over qualifications.
- **Valid narrative, unsupported grammar**: expected VERIFIED; got ABSTAIN. KNOWN LIMITATION: human-readable numbers are correct, but the exact-label parser abstains. Useful false abstention.

## Limits

- Small, author-controlled synthetic set; not real-world or model-quality evidence.
- Pass-through ablation baseline, not a competing LLM system.
- No live LLM, PDF/OCR pipeline, on-chain integration, deployment or users tested.
- A forecast-qualified document still passes: exact arithmetic is not semantic entailment.
- Supported paraphrased evidence is rejected: narrow grammar sacrifices recall.

## Reproducibility

- Corpus SHA-256: `b31dd5d769f03e3a6160567f76048d14c293548ca826ed0687f5b09e447187c0`
- Benchmark SHA-256: `ddd888a0991e6517c347074838572566d0b5f01077369533db96e25fd17f4d12`
- Wall time is diagnostic only; no latency or throughput claim is made.
