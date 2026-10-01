# Independent adversarial review

Reviewed on 2026-10-01 in a separate AI-assisted review pass. This is a review of the deterministic local prototype,
especially `evidence_desk/core.py`, using synthetic evidence. It is not a financial
audit, production penetration test, or assessment of any real issuer.

## Verification snapshot

Run from the project root:

```sh
python -m unittest discover -s tests -p 'test_adversarial.py' -v
```

The independent suite contains 36 test methods, including 80 reproducible
mixed-scale arithmetic cases with an independent integer rounding oracle, plus
parameterized citation, schema, date, numeric-envelope, and policy mutations.
The final review rerun had **36 passing methods, zero failures, and zero errors**.
All six reproduced implementation findings below were fixed by the implementation
owner and independently retested. This snapshot covers the independent suite,
not other project tests or UI checks.

## Findings and regression results

1. **Cross-entity value substitution through duplicate document IDs. Fixed and
   retested.** The direct verifier previously accepted a 999-million claim for a
   target entity while its exact citation quoted the target's 1-million value.
   A different entity's document reused the same ID and line number; lookup
   matched that fact even though the source map pointed at the target document.
   The verifier now rejects duplicate IDs and binds facts to the cited source's
   hash and entity. The file loader already rejected duplicate IDs, but that was
   insufficient for direct verifier callers.

2. **Equivalent decimals falsely triggered conflicts. Fixed and retested.**
   `105`, `105.000` million, and `0.105` billion represented the same amount but
   normalized to differently formatted strings. Comparing Decimal values and
   currency now avoids this false conflict while retaining real disagreement.

3. **Long numbers silently lost source digits. Fixed and retested within the
   explicit envelope.** Default Decimal precision previously rounded a 30-digit
   source amount during scale conversion, then verified the rounded value. The
   parser now permits at most 32 source digits and 12 fractional places and uses
   precision 80 for arithmetic. Tests require either an exact verified amount or
   an explicit abstention; they do not require unlimited precision. Boundary
   cases at 32/33 digits and 12/13 fractional places are included.

4. **Large coverage ratios raised an unhandled Decimal exception. Fixed and
   retested.** Quantization previously failed for large otherwise parseable
   ratios. The bounded source envelope and higher local arithmetic precision
   now handle the large-ratio regression and the extreme accepted numerator /
   denominator combination. Half-up rounding ties also have explicit tests.

5. **Malformed traces crashed or passed accidentally. Fixed and retested for
   tested JSON-shaped cases.** `None`, `[None]`, and non-finite values could raise;
   `{}` passed as an empty iterable. The verifier now returns false for malformed
   input in these cases. This does not make a hash chain an authenticity proof.

6. **A latest report with no parseable facts silently fell back to an older
   report. Fixed and retested.** A complete 2026-09-29 report followed by a
   dated 2026-09-30 narrative statement returned a VERIFIED 2026-09-29 ratio when
   asked for the latest coverage ratio. The date was selected from extracted
   facts, so a newer report disappeared if none of its fact lines matched the
   grammar. This differed from the stated policy of selecting the latest report
   without backfilling. The implementation now selects the latest unambiguous
   report date independently of metric extraction, then abstains if that report
   cannot support the requested metrics. The regression first failed, then passed
   after this fix; it was not weakened to accept the old behavior.

## What the tests establish

- Exact document ID, whole-text SHA-256, raw quote, and one-based line matching
- Rejection of invented amounts, currencies, dates, metrics, narrative answer
  fields, missing citations, and cross-entity citations in tested schema paths
- Inclusive age boundary of 45 days, rejection of future/older dates, no mixing
  metrics across dates, rejection of incompatible currencies and zero liabilities
- Decimal scale normalization and four-place half-up ratio rounding, including
  independently computed mixed-million/billion cases
- Real source disagreement triggers REVIEW regardless of source ordering
- Only named read-only tools can be requested; tested action requests are blocked
- Embedded instruction-like prose does not alter parsed amounts or generate an
  external-action trace in this implementation
- Tested malformed candidate/claim/citation/trace shapes fail closed

All source data in the tests is synthetic. The tests are deterministic and use
only the Python standard library. They do not contact external services.

## Deliberately visible scope limitations

### Legitimate information can be missed

The valid question “How much collateral supports customer balances?” abstains
because it lacks the small keyword set used for routing. Likewise, a dated source
saying “The reserve balance amounts to USD 120 million” and “Customer obligations
total USD 100 million” yields no facts. The Juniper narrative corpus fixture is
another instance of this limitation. These are recall failures relative to a
human understanding of the request, even though abstention is the safe outcome
under the narrow implementation contract.

### A qualified forecast can still be VERIFIED

A document with exact numeric labels followed by “figures above are forecasts,
not observed balances” returns VERIFIED for the computed ratio. The Iris Markets
fixture illustrates the same issue. A characterization test deliberately keeps
this behavior visible; it does **not** claim the source establishes real balances.
The parser does not understand qualifications, negation, restricted assets,
ownership, encumbrances, audited status, or whether numerator and denominator
cover the same economic scope. A source may be incorrect or fabricated while
remaining perfectly self-consistent.

Consequently, a passing test suite and a VERIFIED result are not semantic accuracy
metrics. The correct user-facing interpretation is “the specified numeric checks
passed against these exact source lines.” Any future semantic evaluator should
count qualified forecasts and narrative paraphrases separately rather than
relabeling them away to advertise a perfect score.

### Hashes establish consistency, not trust or completeness

Source hashes bind text bytes, not issuer identity or metadata authenticity.
Trace hashes detect an un-rehashed edit or reordering, but anyone able to replace
the chain can recompute it. A valid prefix also passes: there is no signed final
event or external anchor proving the trace is complete. The suite explicitly
characterizes prefix acceptance. Do not call these traces tamper-proof or audited.

### Read-only architecture is narrower than a security guarantee

The implementation has no external action executor. That is the meaningful
boundary here; its small natural-language blocklist is not a comprehensive intent
classifier. The embedded-instruction test demonstrates one grammar-isolation
case, not general LLM prompt-injection resistance. Adding an LLM, network tools,
document uploads, a remote service, or execution capabilities would require a new
threat model and new tests.

This review does not prove resistance to arbitrary resource-exhaustion inputs,
malformed Python object graphs, compromised local code, or hostile file ingestion.
It does not test deployment authentication, transport security, concurrency, or
browser behavior. The evaluation date is explicit and defaults to a fixed demo
date, so a live adaptation must provide a current policy date intentionally.

## Recommended presentation

Keep the numeric-only disclaimer next to the result, retain the full source text
and qualifications, and distinguish functional regression results from broader
semantic evaluation results. Preserve abstentions and known-limit cases in the
demo. Do not describe this prototype as a production agent, a financial safety
oracle, or an independently audited system.
