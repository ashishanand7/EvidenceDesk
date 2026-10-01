# Verification record

Project created and checked on **2026-10-01**. Environment: Python **3.12.14**, Node **v24.19.0**. All data was synthetic. No keys, external model calls or financial transactions were used.

## Executed successfully

| Command | Observed outcome |
|---|---|
| `python -m unittest discover -s tests -v` | 57 test methods passed; includes 36 adversarial methods and 80 seeded arithmetic subcases |
| `python -m compileall -q evidence_desk tests scripts` | No Python compilation errors |
| `node --check evidence_desk/web/app.js` | No JavaScript syntax errors |
| `node tests/frontend_smoke.cjs` | DOM-stub frontend smoke checks passed |
| `python -m evidence_desk evaluate --output artifacts` | 19 replays; 17 authored-status matches; 1 unsafe acceptance and 1 false abstention |
| `python -m evidence_desk ask --output artifacts/sample-trace.json` | VERIFIED 1.2400× Atlas ratio with exact evidence and five trace stages |
| `python -m evidence_desk verify-trace artifacts/sample-trace.json` | Trace chain valid |
| `python scripts/make_offline_demo.py` | Self-contained captured replay HTML generated |

The Python suite actually starts a temporary local HTTP server and checks assets, headers, health, corpus, evaluations, query responses, malformed requests, content limits, Host/Origin rejection, traversal prevention, and repeated-request isolation. It also launches the CLI as a subprocess.

The JavaScript smoke check executes the actual app script with minimal DOM stubs and real pipeline-generated fixture responses. It checks initial rendering; conflicts; staleness; source-instruction text; the known semantic-gap warning; blocked and out-of-scope requests; the repeated-submit guard; tab switching; all 19 evaluation rows; JSON export content; and request-error recovery.

## Not executed / limits

- **Real-browser visual and interaction QA:** blocked in this environment because the cloud browser rejected the loopback URL with `ERR_BLOCKED_BY_CLIENT`. No tunnel or alternate route was used to bypass that restriction
- **Screenshots, mobile layouts, keyboard/accessibility tree and actual download UI:** not verified in a browser. DOM-stub tests do not replace these checks
- **Live model behavior:** no model adapter or model call exists in this build
- **Production load, deployment, authentication, private-document ingestion, OCR or blockchain integration:** outside this prototype
- **Coverage percentage:** not measured; the test count and scope above are not a line-coverage claim

Test evidence: [Python output](tests.txt), [frontend output](frontend-smoke.txt), [evaluation](evaluation.json), [sample trace](sample-trace.json). The source fingerprint and benchmark fingerprint are stored in the evaluation report. Re-run the commands from the source directory rather than treating these captured artifacts as independent proof.
