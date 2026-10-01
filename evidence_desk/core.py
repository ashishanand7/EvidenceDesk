"""Deterministic extraction and verification; no LLM and no network calls.

Source documents are untrusted data. Only the exact metric grammar is parsed.
The validator is intentionally narrow: numerical consistency is not due diligence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
import hashlib
import json
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AS_OF = "2026-10-01"
MAX_AGE_DAYS = 45
ALLOWED_TOOLS = frozenset({"search_documents", "read_evidence", "calculate_coverage"})
METRIC_RE = re.compile(r"^(Reserves|Liabilities):\s*([0-9]+(?:\.[0-9]+)?)\s+(USD|EUR)\s+(million|billion)\s*$", re.I)
PERIOD_RE = re.compile(r"^As of:\s*(\d{4}-\d{2}-\d{2})\s*$", re.I)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    entity: str
    text: str
    provenance: str = "Synthetic demonstration document, authored October 2026"

    @property
    def sha256(self) -> str:
        return digest(self.text)

    def public(self) -> dict:
        return {**asdict(self), "sha256": self.sha256}


@dataclass(frozen=True)
class Fact:
    document_id: str
    entity: str
    metric: str
    value: str  # Normalized base-currency units, decimal serialized without float drift
    currency: str
    period: str
    quote: str
    line: int
    sha256: str

    def citation(self) -> dict:
        return {"document_id": self.document_id, "quote": self.quote, "line": self.line, "sha256": self.sha256}


class Trace:
    """Hash-linked trace detects accidental edits, not malicious full-chain rewrites."""
    def __init__(self) -> None:
        self.events: list[dict] = []

    def add(self, stage: str, detail: dict) -> None:
        event = {"sequence": len(self.events), "stage": stage, "detail": detail,
                 "previous_hash": self.events[-1]["hash"] if self.events else "0" * 64}
        event["hash"] = digest(canonical(event))
        self.events.append(event)


def verify_trace(events: list[dict]) -> bool:
    if not isinstance(events, list):
        return False
    previous = "0" * 64
    try:
        for i, original in enumerate(events):
            if not isinstance(original, dict):
                return False
            event = dict(original)
            checksum = event.pop("hash", None)
            if event.get("sequence") != i or event.get("previous_hash") != previous or digest(canonical(event)) != checksum:
                return False
            previous = checksum
    except (ValueError, TypeError):
        return False
    return True


def load_corpus(path: Path | None = None) -> list[Document]:
    raw = json.loads((path or ROOT / "data" / "documents.json").read_text())
    docs = [Document(**item) for item in raw]
    if len({doc.id for doc in docs}) != len(docs):
        raise ValueError("Document identifiers must be unique")
    return docs


def document_period(document: Document) -> str | None:
    # A document must have one unambiguous, valid reporting date.
    periods = [m.group(1) for line in document.text.splitlines() if (m := PERIOD_RE.fullmatch(line.strip()))]
    if len(set(periods)) != 1:
        return None
    try:
        date.fromisoformat(periods[0])
    except ValueError:
        return None
    return periods[0]


def extract(document: Document) -> list[Fact]:
    period = document_period(document)
    if period is None:
        return []
    facts = []
    for line_number, line in enumerate(document.text.splitlines(), 1):
        match = METRIC_RE.fullmatch(line.strip())
        if match:
            metric, amount, currency, scale = match.groups()
            # Explicit numeric envelope prevents silent context rounding / resource abuse.
            if len(amount.replace(".", "")) > 32 or ("." in amount and len(amount.split(".")[1]) > 12):
                continue
            multiplier = Decimal(1_000_000 if scale.lower() == "million" else 1_000_000_000)
            with localcontext() as ctx:
                ctx.prec = 80
                normalized = str(Decimal(amount) * multiplier)
            facts.append(Fact(document.id, document.entity, metric.lower(), normalized,
                              currency.upper(), period, line, line_number, document.sha256))
    return facts


def retrieve(documents: list[Document], entity: str, query: str) -> list[Document]:
    """Entity filter + simple lexical ranking. All entity docs retained for conflict checks."""
    tokens = set(re.findall(r"[a-z]+", query.lower()))
    eligible = [d for d in documents if d.entity.casefold() == entity.casefold()]
    return sorted(eligible, key=lambda d: (-len(tokens & set(re.findall(r"[a-z]+", d.text.lower()))), d.id))


def policy(tool: str) -> dict:
    if tool in ALLOWED_TOOLS:
        return {"tool": tool, "allowed": True, "reason": "Read-only local evidence tool"}
    return {"tool": tool, "allowed": False, "reason": "Outside the read-only allowlist; no execution implementation exists"}


def issue(code: str, message: str) -> dict:
    return {"code": code, "message": message}


def validate_candidate(candidate: dict, documents: list[Document], as_of: str = DEFAULT_AS_OF,
                       max_age_days: int = MAX_AGE_DAYS) -> dict:
    """Check claims against exact evidence and consistent, recent source facts.

    Returns REVIEW for conflicting evidence, BLOCKED for a disallowed tool,
    ABSTAIN for other validation failures, VERIFIED only for the bounded schema.
    """
    issues: list[dict] = []
    doc_map = {d.id: d for d in documents}
    if len(doc_map) != len(documents):
        return {"status": "ABSTAIN", "issues": [issue("CORPUS_SCHEMA", "Duplicate document identifiers are not permitted")], "claims": []}
    all_facts = [fact for document in documents for fact in extract(document)]
    try:
        reference_date = date.fromisoformat(as_of)
    except (ValueError, TypeError):
        raise ValueError("as_of must be an ISO calendar date") from None
    if not isinstance(candidate, dict):
        return {"status": "ABSTAIN", "issues": [issue("SCHEMA", "Candidate must be an object")], "claims": []}
    tool = candidate.get("requested_tool")
    if tool is not None and (not isinstance(tool, str) or tool not in ALLOWED_TOOLS):
        return {"status": "BLOCKED", "issues": [issue("TOOL_DENIED", "Requested tool is outside the read-only allowlist")], "claims": []}
    if set(candidate) - {"entity", "claims", "requested_tool", "provider"}:
        issues.append(issue("SCHEMA", "Unexpected top-level fields"))
    entity = candidate.get("entity")
    claims = candidate.get("claims")
    if not isinstance(entity, str) or not entity or not isinstance(claims, list) or not claims or len(claims) > 10:
        return {"status": "ABSTAIN", "issues": issues + [issue("SCHEMA", "Entity and 1–10 structured claims required")], "claims": []}
    for index, claim in enumerate(claims):
        prefix = f"Claim {index + 1}: "
        if not isinstance(claim, dict) or set(claim) != {"metric", "value", "unit", "period", "citations"}:
            issues.append(issue("SCHEMA", prefix + "Invalid claim fields"))
            continue
        metric, unit, period = claim["metric"], claim["unit"], claim["period"]
        if not all(isinstance(v, str) for v in (metric, unit, period, claim["value"])) or metric not in {"reserves", "liabilities", "coverage_ratio"}:
            issues.append(issue("SCHEMA", prefix + "Unsupported metric or field types"))
            continue
        try:
            value = Decimal(claim["value"])
            if not value.is_finite() or value < 0:
                raise InvalidOperation
            age = (reference_date - date.fromisoformat(period)).days
        except (InvalidOperation, ValueError, TypeError):
            issues.append(issue("SCHEMA", prefix + "Invalid value or reporting date"))
            continue
        if age < 0 or age > max_age_days:
            issues.append(issue("STALE_EVIDENCE", prefix + f"Reporting date is outside 0–{max_age_days} days before the evaluation date"))
        citations = claim["citations"]
        if not isinstance(citations, list) or not 1 <= len(citations) <= 20:
            issues.append(issue("MISSING_CITATION", prefix + "1–20 exact citations required"))
            continue
        cited_facts: list[Fact] = []
        for citation in citations:
            if not isinstance(citation, dict) or set(citation) != {"document_id", "quote", "line", "sha256"}:
                issues.append(issue("CITATION_SCHEMA", prefix + "Malformed citation"))
                continue
            doc_id, quote, line, source_hash = (citation[k] for k in ("document_id", "quote", "line", "sha256"))
            if not isinstance(doc_id, str) or not isinstance(quote, str) or not isinstance(source_hash, str) or type(line) is not int:
                issues.append(issue("CITATION_SCHEMA", prefix + "Invalid citation types"))
                continue
            doc = doc_map.get(doc_id)
            if not doc:
                issues.append(issue("UNKNOWN_SOURCE", prefix + "Document does not exist"))
                continue
            if doc.entity.casefold() != entity.casefold():
                issues.append(issue("ENTITY_MISMATCH", prefix + "Citation is for another entity"))
                continue
            if doc.sha256 != source_hash:
                issues.append(issue("HASH_MISMATCH", prefix + "Document content changed since citation creation"))
                continue
            lines = doc.text.splitlines()
            if not quote or not (1 <= line <= len(lines)) or lines[line - 1] != quote:
                issues.append(issue("QUOTE_MISMATCH", prefix + "Quoted text does not match the exact source line"))
                continue
            matches = [f for f in all_facts if f.document_id == doc_id and f.line == line and f.sha256 == doc.sha256 and f.entity == doc.entity]
            if not matches:
                issues.append(issue("UNSUPPORTED_EVIDENCE", prefix + "Quote is not a supported numeric fact"))
            cited_facts.extend(matches)
        required = {"reserves", "liabilities"} if metric == "coverage_ratio" else {metric}
        eligible = [f for f in cited_facts if f.period == period and f.metric in required]
        if any(f.period != period for f in cited_facts):
            issues.append(issue("PERIOD_MISMATCH", prefix + "Citation and claim have different dates"))
        for required_metric in sorted(required):
            values = {(Decimal(f.value), f.currency) for f in all_facts if f.entity.casefold() == entity.casefold()
                      and f.period == period and f.metric == required_metric}
            if len(values) > 1:
                issues.append(issue("CONFLICT", prefix + f"Sources disagree on {required_metric}; human review needed"))
        if set(f.metric for f in eligible) != required:
            issues.append(issue("MISSING_EVIDENCE", prefix + "Required metric evidence is incomplete"))
            continue
        currencies = {f.currency for f in eligible}
        if len(currencies) != 1:
            issues.append(issue("CURRENCY_MISMATCH", prefix + "Cannot combine currencies without an explicit FX source"))
            continue
        if metric == "coverage_ratio":
            reserves = Decimal(next(f.value for f in eligible if f.metric == "reserves"))
            liabilities = Decimal(next(f.value for f in eligible if f.metric == "liabilities"))
            if liabilities == 0:
                issues.append(issue("ZERO_DENOMINATOR", prefix + "Coverage is undefined with zero liabilities"))
                continue
            with localcontext() as ctx:
                ctx.prec = 80
                expected = (reserves / liabilities).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            if unit != "x" or value != expected:
                issues.append(issue("CALCULATION_MISMATCH", prefix + f"Expected {expected}x from source values"))
        elif unit != next(iter(currencies)) or value != Decimal(eligible[0].value):
            issues.append(issue("VALUE_MISMATCH", prefix + "Amount or currency does not match the cited fact"))
    status = "REVIEW" if any(i["code"] == "CONFLICT" for i in issues) else "ABSTAIN" if issues else "VERIFIED"
    return {"status": status, "issues": issues, "claims": claims if status == "VERIFIED" else []}


def _candidate(entity: str, facts: list[Fact], metric: str, latest_period: str | None = None) -> dict:
    required = {"reserves", "liabilities"} if metric == "coverage_ratio" else {metric}
    periods = sorted({f.period for f in facts}, reverse=True)
    # Deliberately select the latest report, never backfill missing facts from an old date.
    period = latest_period if latest_period is not None else periods[0] if periods else ""
    selected = [f for f in facts if f.period == period and f.metric in required]
    value, unit = "0", "x" if metric == "coverage_ratio" else "USD"
    if metric == "coverage_ratio" and required <= {f.metric for f in selected}:
        reserves = Decimal(next(f.value for f in selected if f.metric == "reserves"))
        liabilities = Decimal(next(f.value for f in selected if f.metric == "liabilities"))
        if liabilities:
            with localcontext() as ctx:
                ctx.prec = 80
                value = str((reserves / liabilities).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
    elif selected:
        value, unit = selected[0].value, selected[0].currency
    return {"entity": entity, "provider": "deterministic-extractor-v1", "claims": [
        {"metric": metric, "value": value, "unit": unit, "period": period, "citations": [f.citation() for f in selected]}]}


def run_query(entity: str, question: str, documents: list[Document] | None = None,
              as_of: str = DEFAULT_AS_OF) -> dict:
    docs = load_corpus() if documents is None else documents
    if not isinstance(question, str) or not question.strip() or len(question) > 1000:
        raise ValueError("Question must contain 1–1,000 characters")
    if not isinstance(entity, str) or not 1 <= len(entity) <= 100:
        raise ValueError("Entity must contain 1–100 characters")
    date.fromisoformat(as_of)
    trace = Trace()
    trace.add("request", {"entity": entity, "question": question, "as_of": as_of, "provider": "deterministic-extractor-v1"})
    lower = question.lower()
    blocked_terms = re.search(r"\b(buy|sell|trade|transfer|withdraw|send|email|approve|invest)\b", lower)
    if blocked_terms:
        trace.add("policy", policy("external_action"))
        result = {"status": "BLOCKED", "issues": [issue("TOOL_DENIED", "This prototype only reads evidence and calculates; it cannot act on assets or send messages")], "claims": []}
        candidate = None
        selected = []
    elif any(term in lower for term in ("safe", "solvent", "solvency", "recommend", "fraud", "creditworthy")):
        result = {"status": "ABSTAIN", "issues": [issue("OUT_OF_SCOPE", "A reserve ratio cannot establish solvency, safety, fraud or investment suitability")], "claims": []}
        candidate = None
        selected = []
        trace.add("scope", {"decision": "decline consequential inference"})
    else:
        if any(term in lower for term in ("ratio", "coverage", "backed")):
            metric = "coverage_ratio"
        elif "liabilit" in lower:
            metric = "liabilities"
        elif "reserve" in lower:
            metric = "reserves"
        else:
            metric = None
        if not metric:
            selected, candidate = [], None
            result = {"status": "ABSTAIN", "issues": [issue("OUT_OF_SCOPE", "Ask about reserves, liabilities or reserve coverage; this parser does not understand arbitrary questions")], "claims": []}
        else:
            selected = retrieve(docs, entity, question)
            trace.add("retrieval", {"tool": policy("search_documents"), "document_ids": [d.id for d in selected], "strategy": "entity-filtered lexical ranking; retain all matches for conflict checks"})
            facts = [f for d in selected for f in extract(d)]
            trace.add("extraction", {"facts": [asdict(f) for f in facts], "grammar": "exact numeric labels; source prose is never executed"})
            reporting_dates = [period for doc in selected if (period := document_period(doc)) is not None]
            latest_period = max(reporting_dates) if reporting_dates else ""
            candidate = _candidate(entity, facts, metric, latest_period)
            trace.add("candidate", candidate)
            result = validate_candidate(candidate, selected, as_of)
    trace.add("validation", result)
    return {**result, "entity": entity, "question": question, "as_of": as_of,
            "provider": "deterministic-extractor-v1 (no LLM)", "candidate": candidate,
            "documents": [d.public() for d in selected], "trace": trace.events,
            "disclaimer": "Synthetic prototype. VERIFIED means the narrow numerical checks passed, not that an entity is safe or solvent."}
