'use strict';
let data, selectedTest, selectedCase = '01-successful-repair';
const $ = id => document.getElementById(id);
const el = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
const percent = n => new Intl.NumberFormat('sr-Latn', {style:'percent', maximumFractionDigits:1}).format(n);
const labels = {'wrong-value':'Pogrešna vrednost','stale-value':'Zastarela vrednost','hallucinated-field':'Izmišljeno polje','broken-format':'Narušen format','false-provenance':'Netačno poreklo'};
const titles = {'01-successful-repair':'Uspešna popravka','02-human-review':'Zahtev za ljudski pregled','03-clean-control':'Očuvan ispravan katalog'};
function badge(text, warn=false) { return el('span',text,warn?'tag warn':'tag'); }
function stat(label,value,note) { const n=el('article',undefined,'stat'); n.append(el('div',label,'stat-label'),el('div',value,'stat-value'),el('div',note,'stat-note')); return n; }
function navigate() {
  const view = ['results','catalog','cases','architecture'].includes(location.hash.slice(1)) ? location.hash.slice(1) : 'results';
  document.querySelectorAll('.view').forEach(n => {n.hidden=n.id!==`view-${view}`;});
  document.querySelectorAll('[data-view]').forEach(n => { n.classList.toggle('active',n.dataset.view===view); if(n.dataset.view===view)n.setAttribute('aria-current','page');else n.removeAttribute('aria-current'); });
}
function results() {
  const s=data.summary;
  $('stats').replaceChildren(stat('Završene sesije',`${s.completed_runs} / ${s.expected_runs}`,'Pilot-sesije nisu uključene'),stat('Popravke · with-checker',percent(s.groups['fault/with-checker'].rate),'21 od 25 · kriterijumi protokola'),stat('Popravke · without-checker',percent(s.groups['fault/without-checker'].rate),'25 od 25 · kriterijumi protokola'),stat('Očuvane kontrole','5 / 5','U svakom režimu · odvojeno od popravki'));
  for(const [key,label] of Object.entries(labels)) {
    const tr=el('tr'), title=el('td',label); title.append(el('small',key));tr.append(title);
    for(const mode of ['with-checker','without-checker']) {const g=s.by_fault_class[`${key}/${mode}`]; const cell=el('td',`${g.successes}/${g.n} · ${percent(g.rate)}`); cell.append(el('small',`95% interval: ${g.wilson_95.map(percent).join(' – ')}`));tr.append(cell);}
    tr.append(el('td',key==='broken-format'?'4 zahteva za pregled (with)':'Isti opaženi ishod')); $('classes').append(tr);
  }
  $('provenance').textContent=JSON.stringify({protokol:data.protocol,revizija:data.revision,model:data.agent.model,reasoning:data.agent.reasoning_effort,CLI:data.agent.version,zamrznuti_commit:data.collection_head,izvor:data.source.dataset_id,hash_izvora:data.source.snapshot_hash,hash_trenutnog_kataloga:data.catalog_sha256,neocenjeni_prekidi:s.interrupted_attempts,korigovane_ocene:data.corrections},null,2);
}
function catalogList() {
  const query=$('search').value.toLowerCase(); const matches=data.catalog.filter(r=>JSON.stringify(r).toLowerCase().includes(query));
  $('catalog-list').replaceChildren();
  if(matches.length && !matches.some(r=>r.testcase_id===selectedTest)) {selectedTest=matches[0].testcase_id;catalogDetail(matches[0]);}
  if(!matches.length)$('catalog-detail').replaceChildren(el('h2','Nema odgovarajućeg testa'),el('p','Promeni ili obriši pretragu.'));
  for(const r of matches) { const b=el('button',r.testcase_id,'catalog-card'); b.type='button';b.classList.toggle('selected',selectedTest===r.testcase_id);b.setAttribute('aria-pressed',selectedTest===r.testcase_id);b.append(el('span',r.fields.supported_gpus.value.join(' · '))); b.onclick=()=>{selectedTest=r.testcase_id;catalogList();catalogDetail(r);};$('catalog-list').append(b); }
  if(!matches.length)$('catalog-list').append(el('p','Nema rezultata za ovu pretragu.','muted'));
}
function catalogDetail(r) {
  const box=$('catalog-detail');box.replaceChildren(el('p','DETALJI TEST-SLUČAJA','eyebrow'),el('h2',r.testcase_id)); const grid=el('div',undefined,'field-grid');
  const f=r.fields;
  for(const [name,value] of [['Podržani GPU modeli',f.supported_gpus.value.join(', ')],['Timeout',f.timeout_seconds.value===null?'insufficient-data':`${f.timeout_seconds.value} s`],['Prolaznost',f.pass_rate_badge.pass_rate_percent===null?'insufficient-data':`${f.pass_rate_badge.pass_rate_percent}% · ${f.pass_rate_badge.value}`],['Poslednje merenje',`${f.last_measurement.value} · ${f.last_measurement.status}`]]) {const n=el('div',undefined,'field');n.append(el('span',name),el('strong',value));grid.append(n);}box.append(grid);
  for(const name of ['Purpose','Notes','Summary'])box.append(el('h3',name),el('p',r.prose[name]||'—'));
  const details=el('details');details.append(el('summary','Izvedeni JSON i provenijencija'),el('pre',JSON.stringify(f,null,2)));box.append(details);
}
function diff(text) { const pre=el('pre',undefined,'code-panel'); if(!text.trim()){pre.textContent='Nema tekstualnih izmena. Ulaz i izlaz su identični.';return pre;} for(const line of text.split('\n')) {let cls='diff-line';if(line.startsWith('@@')||line.startsWith('---')||line.startsWith('+++'))cls+=' meta';else if(line.startsWith('+'))cls+=' add';else if(line.startsWith('-'))cls+=' remove';pre.append(el('span',line,cls));}return pre; }
function cases() {
  $('case-choices').replaceChildren();
  for(const [id,title] of Object.entries(titles)){const b=el('button',title,'case-choice');b.type='button';b.classList.toggle('selected',id===selectedCase);b.setAttribute('aria-pressed',id===selectedCase);b.append(el('small',data.cases[id]['corrected-result.json'].run_id));b.onclick=()=>{selectedCase=id;cases();};$('case-choices').append(b);}
  const c=data.cases[selectedCase],r=c['corrected-result.json'],content=$('case-content');content.replaceChildren();
  const panel=el('article',undefined,'panel');panel.append(el('p',r.run_id,'eyebrow'),el('h2',titles[selectedCase]));const meta=el('div',undefined,'case-meta');meta.append(badge(`Sesija: ${r.status}`),badge(`Uspeh protokola: ${r.success?'DA':'NE'}`,!r.success),badge(`Završni katalog: ${r.checker_valid?'VALIDAN':'NEVALIDAN'}`,!r.checker_valid),badge(`Agentske provere: ${r.checker_attempts}`));panel.append(meta);
  const note=selectedCase==='02-human-review'?'Agent je tražio ljudski pregled, bez izmena i bez poziva checker-a. Ovo ostaje neuspeh autonomne popravke.':selectedCase==='03-clean-control'?'Referentni katalog, ulaz i izlaz imaju isti hash. Provera nije zahtevala izmenu.':'Polje agent_confidence uklonjeno je iz Markdown-a i skrivenog JSON-a pre prve uspešne agentske provere.';
  panel.append(el('p',note),el('h3','Agentska izmena · input → output'),diff(c['repair.diff'])); const inj=el('details');inj.append(el('summary','Koja je greška ubačena? · referenca → input'),diff(c['injection.diff']));panel.append(inj);content.append(panel);
  const comparisons=el('article',undefined,'panel');const toggle=el('label',undefined,'view-switch'),check=el('input');check.type='checkbox';toggle.append(check,document.createTextNode('Prikaži ceo katalog umesto odlomka'));comparisons.append(el('h2','Pre i posle'),toggle);const grid=el('div',undefined,'two-col');const before=el('pre',undefined,'code-panel'),after=el('pre',undefined,'code-panel');for(const [heading,p] of [['Ulazni katalog',before],['Izlazni katalog',after]]) {const div=el('div');div.append(el('h3',heading),p);grid.append(div);}comparisons.append(grid);function update(){before.textContent=c[check.checked?'input.md':'input-excerpt.md'];after.textContent=c[check.checked?'output.md':'output-excerpt.md'];}check.onchange=update;update();content.append(comparisons);
  const reports=el('article',undefined,'panel');reports.append(el('h2','Nezavisni izveštaji evaluatora'),el('p','Početna i završna evaluatorska provera nisu agentski pozivi i ne vraćaju se agentu kao povratna informacija.'));const rg=el('div',undefined,'report-grid');for(const [heading,key] of [['Pre sesije','initial-checker.json'],['Posle sesije','final-checker.json']]) {const d=el('div');d.append(el('h3',heading),el('pre',JSON.stringify(c[key],null,2),'code-panel'));rg.append(d);}reports.append(rg);content.append(reports);
  const message=el('article',undefined,'panel');message.append(el('h2','Završna poruka agenta'),el('pre',c['agent-final.txt'],'case-message'));content.append(message);
  const details=el('details',undefined,'panel');details.append(el('summary','Ocena, zaštićena polja i audit'),el('pre',JSON.stringify({ocena:r,audit:c['audit-summary.json']},null,2)));content.append(details);
}
async function start(){try{const response=await fetch('/api/data');if(!response.ok)throw new Error('Podaci nisu dostupni.');data=await response.json();results();selectedTest=data.catalog[0].testcase_id;catalogList();catalogDetail(data.catalog[0]);cases();$('search').addEventListener('input',catalogList);window.addEventListener('hashchange',navigate);navigate();$('loading').hidden=true;$('app').hidden=false;}catch(error){$('loading').textContent=`Prikaz nije učitan: ${error.message} Proveri terminal i sačuvane dokaze.`;}}
start();
