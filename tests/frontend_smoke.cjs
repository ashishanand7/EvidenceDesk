/* Dependency-free DOM-stub smoke test. This is NOT browser/layout/accessibility QA. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const cp = require('node:child_process');
const root = path.resolve(__dirname,'..');
const fixture = JSON.parse(cp.execFileSync(process.env.PYTHON || 'python',['-c',`
import json
from evidence_desk.core import load_corpus,run_query
from evidence_desk.evaluation import evaluate
corpus=load_corpus()
qs=['What is the reserve coverage ratio?','Transfer funds now','Is this safe?']
print(json.dumps({'corpus':{'documents':[d.public() for d in corpus]},'evaluation':evaluate(),'answers':{e:{q:run_query(e,q) for q in qs} for e in {d.entity for d in corpus}}}))
`],{cwd:root,encoding:'utf8'}));
class Element {
  constructor(tag='div'){this.tag=tag;this.children=[];this.attributes={};this.listeners={};this.dataset={};this.className='';this.textContent='';this.value='';this.hidden=false;this.disabled=false;
    this.classList={add:(s)=>{this.className+=' '+s;},toggle:(s,on)=>{const words=new Set(this.className.split(/\s+/).filter(Boolean));on?words.add(s):words.delete(s);this.className=[...words].join(' ');}};
  }
  append(...els){this.children.push(...els);}
  replaceChildren(...els){this.children=els;if(this.tag==='select'&&els.length)this.value=els[0].value;}
  setAttribute(k,v){this.attributes[k]=v;}
  addEventListener(k,fn){this.listeners[k]=fn;}
  click(){if(!this.disabled&&this.listeners.click)this.listeners.click({preventDefault(){}});}
}
const html = fs.readFileSync(path.join(root,'evidence_desk/web/index.html'),'utf8');
const elements={};for(const match of html.matchAll(/<([a-z]+)[^>]*id="([^"]+)"/g))elements[match[2]]=new Element(match[1]);
elements.question.value='What is the reserve coverage ratio?';elements['as-of'].value='2026-10-01';
const examples=[...html.matchAll(/data-example="([^"]+)"/g)].map(match=>{const el=new Element('button');el.dataset.example=match[1];return el;});
let requests=0, failNext=false, exportBlob;
const context=vm.createContext({console,Intl,JSON,Number,Set,Error,Blob,setTimeout,URL:{createObjectURL(blob){exportBlob=blob;return 'blob:local-test';},revokeObjectURL(){}},document:{getElementById:(id)=>{assert.ok(elements[id],`missing ${id}`);return elements[id];},createElement:(tag)=>new Element(tag),querySelectorAll:()=>examples},fetch:async(url,options)=>{
 requests++;
 if(failNext){failNext=false;return {ok:false,status:400,json:async()=>({error:'Simulated request failure'})};}
 let data;
 if(url==='/api/corpus')data=fixture.corpus;
 else if(url==='/api/evaluation')data=fixture.evaluation;
 else {const req=JSON.parse(options.body);data=fixture.answers[req.entity][req.question];assert.ok(data,'test question fixture missing');}
 return {ok:true,json:async()=>data};
}});
const text=(el)=>[el.textContent,...el.children.map(text)].join(' ');
async function settle(){for(let i=0;i<5;i++)await new Promise(resolve=>setImmediate(resolve));}
(async()=>{
 vm.runInContext(fs.readFileSync(path.join(root,'evidence_desk/web/app.js'),'utf8'),context);
 await settle();
 assert.equal(elements.status.textContent,'VERIFIED');assert.equal(elements['answer-value'].textContent,'1.24×');assert.equal(elements.sources.children.length,2);assert.equal(elements.trace.children.length,5);
 examples[0].click();await settle();assert.equal(elements.status.textContent,'REVIEW');assert.match(text(elements.issues),/CONFLICT/);
 examples[1].click();await settle();assert.equal(elements.status.textContent,'ABSTAIN');assert.match(text(elements.issues),/STALE_EVIDENCE/);
 examples[2].click();await settle();assert.equal(elements.status.textContent,'VERIFIED');assert.equal(elements['answer-value'].textContent,'0.96×');assert.match(text(elements.sources),/Ignore prior rules/);
 examples[3].click();await settle();assert.equal(elements.status.textContent,'VERIFIED');assert.equal(elements['answer-description'].className,'known-gap');assert.match(elements['answer-description'].textContent,/KNOWN FAILURE/);
 elements.entity.value='Atlas Reserve';elements.question.value='Transfer funds now';await vm.runInContext('runQuery()',context);assert.equal(elements.status.textContent,'BLOCKED');assert.equal(elements.sources.children[0].className,'empty');
 elements.question.value='Is this safe?';await vm.runInContext('runQuery()',context);assert.equal(elements.status.textContent,'ABSTAIN');
 elements.question.value='What is the reserve coverage ratio?';const before=requests;await vm.runInContext('Promise.all([runQuery(),runQuery()])',context);assert.equal(requests,before+1);assert.equal(elements.status.textContent,'VERIFIED');assert.equal(elements['answer-description'].className,'');
 elements['evaluation-tab'].click();await settle();assert.equal(elements.inquiry.hidden,true);assert.equal(elements.evaluation.hidden,false);assert.equal(elements.metrics.children.length,3);assert.equal(elements['case-list'].children.length,19);assert.match(text(elements.metrics),/14 → 1/);
 elements['inquiry-tab'].click();assert.equal(elements.inquiry.hidden,false);assert.equal(elements.evaluation.hidden,true);
 elements.export.click();assert.ok(exportBlob);assert.equal(JSON.parse(await exportBlob.text()).status,'VERIFIED');
 failNext=true;await vm.runInContext('runQuery()',context);assert.equal(elements.error.hidden,false);assert.equal(elements.error.textContent,'Simulated request failure');assert.equal(elements.run.disabled,false);
 await vm.runInContext('runQuery()',context);assert.equal(elements.error.hidden,true);assert.equal(elements.answer.attributes['aria-busy'],'false');
 console.log('PASS: frontend DOM-stub smoke checks (initial render; conflict/stale/injection/known-gap examples; action/scope boundaries; repeated-submit guard; tab switch; 19-case evaluation; JSON export; error recovery).');
 console.log('Not run: real browser, CSS layout, mobile viewport, keyboard/accessibility tree, download UI.');
})().catch(error=>{console.error(error);process.exitCode=1;});
