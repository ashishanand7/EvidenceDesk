"""Produce an explicitly labeled, self-contained HTML replay, not a Python runtime."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from evidence_desk.core import ROOT, load_corpus, run_query
from evidence_desk.evaluation import evaluate

questions = ['What is the reserve coverage ratio?', 'What are the reserves?', 'What are the liabilities?', 'Is this safe?', 'Transfer funds now']
corpus = load_corpus()
payload = {'corpus':{'documents':[d.public() for d in corpus]}, 'evaluation':evaluate(), 'answers':{entity:{q:run_query(entity,q) for q in questions} for entity in sorted({d.entity for d in corpus})}}
html = (ROOT/'evidence_desk/web/index.html').read_text()
css = (ROOT/'evidence_desk/web/style.css').read_text()
js = (ROOT/'evidence_desk/web/app.js').read_text()
start = js.index('async function jsonFetch(')
end = js.index('\nfunction renderResult',start)
replacement = '''async function jsonFetch(url, options) {
  if(url === '/api/corpus') return REPLAY.corpus;
  if(url === '/api/evaluation') return REPLAY.evaluation;
  const request = JSON.parse(options.body);
  if(request.as_of !== '2026-10-01') throw new Error('This replay is captured for 2026-10-01. Run the Python server to evaluate another date.');
  const answer = REPLAY.answers[request.entity]?.[request.question];
  if(!answer) throw new Error('Captured replay only. Use the default coverage question or: What are the reserves? / What are the liabilities? / Is this safe? / Transfer funds now. Run the Python server for other requests.');
  return answer;
}
'''
js = js[:start] + replacement + js[end:]
serialized = json.dumps(payload,ensure_ascii=False).replace('</','<\\/')
js = 'const REPLAY = '+serialized+';\n'+js
html = html.replace('<link rel="stylesheet" href="/style.css">','<style>'+css+'</style>').replace('<script src="/app.js" defer></script>','')
html = html.replace('href="/"','href="#"').replace('LOCAL / OFFLINE','CAPTURED REPLAY').replace('PROTOTYPE 0.1','NO PYTHON EXECUTION')
html = html.replace('<strong>Synthetic by design.</strong>','<strong>Offline replay.</strong>').replace('No live model, real issuer data,<br>or financial actions.','Captured synthetic outputs.<br>Run Python for live verification.')
html = html.replace('<div class="eyebrow">ASK A BOUNDED QUESTION</div>','<div class="eyebrow">EXPLORE CAPTURED ANSWERS</div>')
html = html.replace('</body>','<script>'+js+'</script></body>')
(ROOT/'artifacts/offline-demo.html').write_text(html)
print('Wrote artifacts/offline-demo.html; captured results only, no network calls')
