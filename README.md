# Evidence Desk

### An answer is only as strong as its evidence.

An independent personal prototype, created **October 2026**, for inspecting evidence-backed financial claims. It pairs a deliberately bounded Python verification pipeline with a small browser workbench, a CLI, and a reproducible adversarial evaluation.

**No API keys. No runtime dependencies. No live LLM. No real issuer data. No financial actions.**

The project is AI-assisted. Its implemented contribution is the evidence/verification/evaluation boundary that could surround an AI candidate generator. The bundled generator is deterministic; it is not described as a trained model, an autonomous financial agent, or a production deployment.

## Try it in two minutes

Requires Python 3.11+; verified here on Python 3.12.14. Download and unzip the source, then run from the project directory:

```sh
python -m evidence_desk serve
```

Open **http://127.0.0.1:8765**. The server binds only to loopback. No installation or network access is required.

For a zero-server preview, open [`artifacts/offline-demo.html`](artifacts/offline-demo.html). It is explicitly labeled as a **captured replay** and supports only its bundled entities, questions and date; it does not execute Python verification in the browser.

```sh
# Supported answer, with exact citations and full trace
python -m evidence_desk ask --entity "Atlas Reserve" --output artifacts/sample-trace.json

# Conflicting evidence is routed to human review
python -m evidence_desk ask --entity "Bramble Custody"

# Source freshness, currency and missing-evidence checks
python -m evidence_desk ask --entity "Cinder Protocol"
python -m evidence_desk ask --entity "Gale Custody"
python -m evidence_desk ask --entity "Delta Vault"

# No financial action tool is implemented
python -m evidence_desk ask --question "Transfer funds now"

# Reproduce the evaluation and test suite
python -m evidence_desk evaluate --output artifacts
python -m unittest discover -s tests -v
node --check evidence_desk/web/app.js
node tests/frontend_smoke.cjs

# Detect accidental edits to an exported trace
python -m evidence_desk verify-trace artifacts/sample-trace.json
```

The Node checks are optional development checks; Node is not needed to run the app. `verify-trace` validates only the event list's hash links: it does not authenticate sources, the top-level exported answer, or trace completeness.

## What is actually implemented

- A corpus of **12 synthetic documents for 10 fictional entities**, including historical reports, conflicting numbers, incomplete balances, mixed currency and scale, malicious source prose, forecasts, and narrative phrasing
- Entity-filtered lexical retrieval that retains every matching document for contradiction checks; no embedding index or vector database
- Exact-label extraction of dated reserves and liabilities; decimal arithmetic normalizes millions/billions and rounds ratios half-up to four decimal places
- Structured candidate checking: exact source line and quote, document SHA-256, entity, date, freshness, currencies, numerical values, calculations and cross-source contradictions
- Four explicit results: `VERIFIED`, `REVIEW`, `ABSTAIN`, `BLOCKED`; rejected candidates never appear in the released claims list
- A read-only tool allowlist, with no transfer, trading, email, network-tool or approval-execution implementation
- A hash-linked inspection trail with source text, candidate, checks and outcome; JSON export and CLI verification
- A Python loopback HTTP API and responsive, dependency-free HTML/CSS/JavaScript workbench with source highlighting, expandable traces and an evaluation view
- A **19-case synthetic candidate-replay ablation**, machine-readable JSON/CSV, and an honest failure report

**`VERIFIED` means only that this narrow verifier accepted the structured numeric claim.** It does not mean the issuer is safe, solvent, investable, authentic, legally compliant or independently audited. The forecast example demonstrates why this distinction matters.

## Architecture

```text
Synthetic documents ─► Entity filter + lexical ranking
                                  │
                        Exact dated-fact extractor
                                  │
                       Deterministic candidate generator
                                  │
                  Citation / numeric / policy verification
                                  │
          VERIFIED       REVIEW       ABSTAIN       BLOCKED
                                  │
                    Hash-linked trace + UI / CLI

Hand-authored candidates ─► same verifier ─► evaluation JSON/CSV
```

The verifier is callable independently of the bundled generator. A future model adapter could produce the same structured candidate contract, but no live adapter, paid model, MCP server or blockchain connector is implemented or tested. Keeping those out makes the actual failure boundary inspectable.

### Deliberate design choices

1. **Keep all relevant documents.** Retrieval rankings must not hide a lower-ranked contradiction. This trades efficiency for conservative checking on a tiny corpus.
2. **Use exact lines and source fingerprints.** A plausible-looking citation is insufficient. A quote must exist at the stated line in the exact document version.
3. **Use decimals, not floating-point money.** Supported source numbers have at most 32 digits and 12 fractional digits. Computation uses an 80-digit decimal context; out-of-envelope numbers are not silently rounded.
4. **Choose the latest dated report first.** Missing or unparseable figures in the newest report do not silently fall back to an older report. Evidence age is measured against an explicit `--as-of` date.
5. **Keep policy decisions outside source prose.** Embedded instructions are never executed. The text parser and tool allowlist are intentionally much less capable than an LLM agent.
6. **Make rejection visible.** The UI shows the failed check and original source text, rather than converting uncertainty into a confident answer.

The 45-day freshness window is an arbitrary demonstration policy, **not a financial standard or regulatory requirement**. UI dates default to 2026-10-01 so the bundled demonstration stays reproducible.

## Measured results

Run: `python -m evidence_desk evaluate --output artifacts`

| Metric | Unchecked pass-through | Checked pipeline |
|---|---:|---:|
| Status agreement with authored labels | 5 / 19 | 17 / 19 |
| Unsafe-to-accept candidates accepted ↓ | 14 / 14 | 1 / 14 |
| Supported candidates accepted ↑ | 5 / 5 | 4 / 5 |

“Unsafe-to-accept” is a manually assigned dataset label, not an empirical risk estimate. The baseline **deliberately accepts every candidate**; it is an ablation of the verifier, not a competitive model or a retrieval system. No tools are executed in either evaluation condition.

This small, author-controlled set is not held out. It demonstrates specific failure modes and trade-offs; it does not establish a real-world hallucination rate, model accuracy, production quality or statistical generalization. See [full evaluation](artifacts/evaluation.md), [row-level CSV](artifacts/evaluation.csv), and [machine-readable results](artifacts/evaluation.json), which include corpus/benchmark checksums.

### The two retained failures

- **Forecast mistaken for balance:** Iris Markets has correct labeled numbers followed by a qualification that they are projections. The arithmetic verifier accepts the ratio. It does not understand that semantic qualification. The UI explicitly calls out this failure.
- **Valid narrative rejected:** Juniper Fund reports supported numbers in ordinary prose rather than exact metric labels. The parser abstains. This illustrates the recall cost of a rigid grammar.

Neither failure is hidden by changing the benchmark label to match the implementation.

## Verification and security scope

- **57 Python unittest methods passed**, including HTTP integration, CLI commands, schema/citation mutations, temporal/currency edge cases, and independent adversarial review
- The adversarial suite includes **80 seeded mixed-scale arithmetic subcases** checked against an independent integer-rounding oracle
- JavaScript syntax and DOM-stub frontend smoke checks are included separately; see [verification record](artifacts/verification.md) for actual run status
- Full visual/browser QA was **not completed in this environment**: its cloud browser rejected the loopback URL. No screenshot or mobile-browser test is claimed
- Tests uncovered and fixed six bugs: numerically equivalent strings treated as conflicts; decimal rounding; extreme-ratio errors; malformed traces; duplicate source-ID substitution; and fallback to older evidence when the latest report was unparseable

See [independent review](docs/independent-review.md) and [test output](artifacts/tests.txt).

The server has an exact static-file allowlist, local Host/Origin checks, a 4 KiB JSON request bound, no CORS and no uploads. Source strings enter the UI with `textContent`, not HTML. These are useful prototype precautions, **not a security audit**. Python's [`http.server` is not recommended for production](https://docs.python.org/3.12/library/http.server.html). Do not expose this server publicly, tunnel it, or load private/regulated data into this prototype.

Hash links detect accidental changes if a trusted final hash is retained elsewhere. A person who can rewrite the entire chain can recompute it; a valid prefix can omit later events. No trusted signature, timestamp, append-only storage or source authenticity guarantee exists.

## Data provenance

Every entity and balance is fictional. The source files were authored for this project on 2026-10-01, not scraped from companies, financial filings, on-chain ledgers, employers or customer accounts. Malicious prose is intentionally inert test content. See [data provenance](data/PROVENANCE.md).

The synthetic dataset and replay cases can be regenerated:

```sh
python scripts/make_data.py
python scripts/make_benchmark.py
python -m evidence_desk evaluate --output artifacts
python scripts/make_offline_demo.py
```

Regeneration is transparent and deterministic except for evaluation wall time and environment metadata. Wall time is diagnostic only; no throughput or latency claim is made.

## Five-minute interview walkthrough

1. **Start with Atlas.** Show the 1.24× answer, its exact source lines, the prior-month document, and the calculation trace. Explain what `VERIFIED` does and does not mean.
2. **Switch to Bramble.** Two same-date reports disagree. Explain why retaining all entity documents matters and why the system releases no numeric claim.
3. **Try an action and a malicious source.** `Transfer funds now` is blocked; Echo's embedded instruction remains plain text. Explain that these are deterministic boundaries, not proven defenses for a general LLM agent.
4. **Open the evaluation suite.** Explain the intentionally weak pass-through baseline, the 19 hand-authored labels and the two surviving failures. Avoid claiming “93% fewer hallucinations.”
5. **Discuss engineering trade-offs.** Exact evidence vs semantic entailment, precision vs numerical bounds, freshness vs fallback, safe abstention vs recall, and hash consistency vs authenticity.
6. **Describe the next credible experiment.** Add independently labeled, licensed public documents; a schema-constrained model adapter; qualification-aware claim extraction; and held-out validation. Only then assess model behavior and deployment needs.

## Why this project fits accountable financial AI

The scope was chosen against [Eunice's Senior Software / AI Engineer role](https://eunice.ai/careers/software-ai-engineer), reviewed 2026-10-01: evidence-backed financial infrastructure, Python/full-stack delivery, system-design trade-offs and evaluation pipelines. This project is independent and unaffiliated with Eunice. No employment, endorsement or use of proprietary systems is implied.

It is an artifact to discuss and extend, not a substitute for production experience. Suggested factual project language is in [portfolio notes](docs/portfolio-notes.md); only use claims you can personally explain and demonstrate.

## Repository guide

```text
evidence_desk/core.py         extraction, verification, policy, trace
 evidence_desk/evaluation.py  authored-replay ablation and reports
 evidence_desk/server.py      loopback-only HTTP API
 evidence_desk/__main__.py    CLI
 evidence_desk/web/           browser workbench
 data/                       synthetic sources and labeled candidates
 tests/                      adversarial, pipeline, HTTP, frontend checks
 artifacts/                  actual results, trace, offline demo, run record
 docs/                       independent review and portfolio/interview notes
 scripts/                    deterministic data/demo generation
```

No public deployment, paid API, secret, real financial transaction or production user is part of this build. No reuse license is granted by this repository unless its owner adds one explicitly.
