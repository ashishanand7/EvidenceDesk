'use strict';
const $ = (id) => document.getElementById(id);
let currentResult = null;
let latestRequest = 0;
let busy = false;
function node(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}
async function jsonFetch(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
function renderResult(data) {
  currentResult = data;
  $('export').disabled = false;
  $('status').className = `status ${data.status}`;
  $('status').textContent = data.status;
  const claim = data.claims[0];
  $('answer-title').textContent = `${data.entity} · ${claim ? claim.period : 'Evidence check'}`;
  $('answer-value').className = 'answer-value';
  if (claim) {
    $('answer-value').textContent = claim.metric === 'coverage_ratio' ? `${Number(claim.value).toFixed(2)}×` : new Intl.NumberFormat('en-US', {style:'currency',currency:claim.unit,maximumFractionDigits:0}).format(Number(claim.value));
    $('answer-description').textContent = claim.metric === 'coverage_ratio' ? 'Reported reserves ÷ reported liabilities. Exact citations, dates, units and arithmetic passed the bounded checks. This is not a solvency assessment.' : 'The structured numeric claim matches the cited source lines and reporting date. Source authenticity and broader economic meaning have not been established.';
  } else {
    $('answer-value').classList.add('long');
    $('answer-value').textContent = {REVIEW:'Review required.',ABSTAIN:'Not enough support.',BLOCKED:'Outside the boundary.'}[data.status] || 'No result.';
    $('answer-description').textContent = 'No checked claim is released. Inspect the specific reason and the original source material below.';
  }
  if (data.entity === 'Iris Markets') {
    $('answer-description').className = 'known-gap';
    $('answer-description').textContent = 'KNOWN FAILURE: these numbers are forecasts, not observed balances. The arithmetic verifier accepts them because it does not interpret qualifications. This case is deliberately retained in the benchmark.';
  } else $('answer-description').className = '';
  $('issues').replaceChildren(...data.issues.map(item => {
    const el = node('div','issue'); el.append(node('b','',item.code),node('span','',item.message)); return el;
  }));
  $('source-count').textContent = `${data.documents.length} documents`;
  const citations = data.candidate ? data.candidate.claims.flatMap(c => c.citations || []) : [];
  $('sources').replaceChildren(...data.documents.map((doc,index) => {
    const card = node('article','source-card');
    const title = node('div','source-title'); title.append(node('span','source-number',String(index+1).padStart(2,'0')),node('span','',doc.title));
    const lines = node('div','source-lines');
    doc.text.split('\n').forEach((text,i) => {
      const cited = citations.some(c => c.document_id === doc.id && c.line === i+1);
      const line = node('div',`source-line${cited?' cited':''}`);
      line.append(node('span','line-number',String(i+1)),node('span','',text)); lines.append(line);
    });
    card.append(title,lines,node('div','source-foot',`SHA-256 ${doc.sha256.slice(0,20)}…\n${doc.provenance}`));
    return card;
  }));
  if (!data.documents.length) $('sources').append(node('p','empty','No source documents are available for this result.'));
  $('trace-count').textContent = `${data.trace.length} steps · hash-linked`;
  $('trace').replaceChildren(...data.trace.map(event => {
    const el = node('details'); const summary = node('summary');
    summary.append(node('span','',String(event.sequence+1).padStart(2,'0')),node('strong','',event.stage));
    el.append(summary,node('pre','',JSON.stringify(event,null,2))); return el;
  }));
}
async function runQuery() {
  if (busy) return;
  busy = true;
  const request = ++latestRequest;
  $('run').disabled = true;
  $('answer').setAttribute('aria-busy','true');
  $('error').hidden = true;
  try {
    const data = await jsonFetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({entity:$('entity').value,question:$('question').value,as_of:$('as-of').value})});
    if (request === latestRequest) renderResult(data);
  } catch (error) {
    $('error').textContent = error.message; $('error').hidden = false;
  } finally {
    if (request === latestRequest) { busy = false; $('run').disabled = false; $('answer').setAttribute('aria-busy','false'); }
  }
}
async function loadEvaluation() {
  $('rerun').disabled = true; $('eval-error').hidden = true;
  try {
    const data = await jsonFetch('/api/evaluation');
    const items = [
      ['UNSAFE ACCEPTANCES',`${data.baseline.unsafe_accepted} → ${data.checked.unsafe_accepted}`,`of ${data.checked.unsafe_total} unsafe synthetic candidates`],
      ['DECISION AGREEMENT',`${data.checked.decision_correct} / ${data.checked.total}`,'checked status vs authored label'],
      ['SUPPORTED ACCEPTED',`${data.checked.supported_accepted} / ${data.checked.supported_total}`,'one useful false abstention']
    ];
    $('metrics').replaceChildren(...items.map(([label,value,meta]) => {const el=node('div','metric-card');el.append(node('div','label',label),node('div','value',value),node('div','meta',meta));return el;}));
    $('case-list').replaceChildren(...data.cases.map((item,i) => {
      const details = node('details','case'), summary = node('summary');
      summary.append(node('span','source-number',String(i+1).padStart(2,'0')),node('strong','case-name',item.name),node('span','',item.checked_status),node('span',`case-result${item.checked_correct?'':' fail'}`,item.checked_correct?'MATCH':'KNOWN GAP'));
      const body = node('div','case-details');body.append(node('p','',item.rationale),node('p','',`Expected: ${item.expected_status} · Baseline: ${item.baseline_status} · Checked: ${item.checked_status}`),node('pre','',JSON.stringify({candidate:item.candidate,issues:item.issues},null,2)));
      details.append(summary,body);return details;
    }));
  } catch (error) { $('eval-error').textContent=error.message; $('eval-error').hidden=false; }
  finally { $('rerun').disabled=false; }
}
function switchTab(selected) {
  ['inquiry','evaluation'].forEach(id => {const active=id===selected;$(id).hidden=!active;$(id+'-tab').classList.toggle('active',active);$(id+'-tab').setAttribute('aria-selected',String(active));});
  if (selected==='evaluation') loadEvaluation();
}
$('query-form').addEventListener('submit',event=>{event.preventDefault();runQuery();});
$('inquiry-tab').addEventListener('click',()=>switchTab('inquiry'));
$('evaluation-tab').addEventListener('click',()=>switchTab('evaluation'));
$('rerun').addEventListener('click',loadEvaluation);
document.querySelectorAll('[data-example]').forEach(button=>button.addEventListener('click',()=>{if(busy)return;$('entity').value=button.dataset.example;$('question').value='What is the reserve coverage ratio?';runQuery();}));
$('export').addEventListener('click',()=>{
  if(!currentResult)return;
  const url=URL.createObjectURL(new Blob([JSON.stringify(currentResult,null,2)],{type:'application/json'}));
  const link=node('a');link.href=url;link.download='evidence-desk-trace.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
(async()=>{try{const data=await jsonFetch('/api/corpus');const entities=[...new Set(data.documents.map(d=>d.entity))].sort();$('entity').replaceChildren(...entities.map(name=>{const option=node('option','',name);option.value=name;return option;}));await runQuery();}catch(error){$('error').textContent=error.message;$('error').hidden=false;}})();
