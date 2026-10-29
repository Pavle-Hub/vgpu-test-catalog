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
  const view = ['results','catalog','cases','architecture','sessions'].includes(location.hash.slice(1)) ? location.hash.slice(1) : 'results';
  document.querySelectorAll('.view').forEach(n => {n.hidden=n.id!==`view-${view}`;});
  document.querySelectorAll('[data-view]').forEach(n => { n.classList.toggle('active',n.dataset.view===view); if(n.dataset.view===view)n.setAttribute('aria-current','page');else n.removeAttribute('aria-current'); });
}
function results() {
  const s=data.summary;
  const withGroup=s.groups['fault/with-checker'], withoutGroup=s.groups['fault/without-checker'];
  $('stats').replaceChildren(stat('Završene sesije',`${s.completed_runs} / ${s.expected_runs}`,'Pilot-sesije nisu uključene'),stat('Popravke · with-checker',percent(withGroup.rate),`${SessionEvidence.formatCount(withGroup)} · kriterijumi protokola`),stat('Popravke · without-checker',percent(withoutGroup.rate),`${SessionEvidence.formatCount(withoutGroup)} · kriterijumi protokola`),stat('Uspešne kontrole',SessionEvidence.formatCount(s.groups['clean/with-checker']),`with; without: ${SessionEvidence.formatCount(s.groups['clean/without-checker'])}`));
  const reviewRows=Object.values(data.sessions).map(s=>s.result).filter(r=>r.human_review_reported&&!r.success);
  const interpretation=document.querySelector('#view-results .two-col').children[1];
  interpretation.querySelector('h2').textContent=`Zahtevi za pregled: ${reviewRows.length}. Nisu pogrešne provere.`;
  interpretation.querySelector('p:not(.eyebrow)').textContent=`Broj neuspešnih sesija sa zahtevom za ljudski pregled: ${reviewRows.length}. Takav ishod ostaje neuspeh autonomne popravke; pregled pojedinačnih kriterijuma je dostupan u tabeli sesija.`;
  const paired=s.paired.fault;
  interpretation.querySelector('.callout').textContent=`Uparena razlika: ${new Intl.NumberFormat('sr-Latn').format(paired.paired_rate_difference*100)} pp · Egzaktni dvostrani test: p = ${new Intl.NumberFormat('sr-Latn').format(paired.exact_p_two_sided)}`;
  interpretation.querySelector('.muted').textContent=`Korigovane audit ocene: ${data.corrections}. Originalni dokazi nisu menjani.`;
  for(const [key,label] of Object.entries(labels)) {
    const tr=el('tr'), title=el('td',label); title.append(el('small',key));tr.append(title);
    for(const mode of ['with-checker','without-checker']) {const g=s.by_fault_class[`${key}/${mode}`]; const cell=el('td',`${g.successes}/${g.n} · ${percent(g.rate)}`); cell.append(el('small',`95% interval: ${g.wilson_95.map(percent).join(' – ')}`));tr.append(cell);}
    const count=reviewRows.filter(r=>r.fault_class===key).length;
    const a=s.by_fault_class[`${key}/with-checker`],b=s.by_fault_class[`${key}/without-checker`];
    tr.append(el('td',count?`${count} zahteva za pregled`:(a.rate===b.rate?'Isti opaženi ishod':'Različite opažene stope'))); $('classes').append(tr);
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
function criteriaPanel(result) {
  const box=el('div'); box.append(el('h3','Šta je provereno?'));
  const list=el('ul',undefined,'criteria');
  for(const [label,state] of SessionEvidence.criteria(result)) {
    const row=el('li');row.append(el('span',label),el('span',state===null?'NEPOZNATO':state?'DA':'NE',state?'criterion-pass':'criterion-fail'));list.append(row);
  }
  box.append(list,el('p','Ovo su sačuvane ocene protokola, ne nove provere. Validan katalog nije isto što i uspešna sesija.','muted'));
  return box;
}
function diff(text) { const pre=el('pre',undefined,'code-panel'); if(!text.trim()){pre.textContent='Nema tekstualnih izmena. Ulaz i izlaz su identični.';return pre;} for(const line of text.split('\n')) {let cls='diff-line';if(line.startsWith('@@')||line.startsWith('---')||line.startsWith('+++'))cls+=' meta';else if(line.startsWith('+'))cls+=' add';else if(line.startsWith('-'))cls+=' remove';pre.append(el('span',line,cls));}return pre; }
function cases() {
  $('case-choices').replaceChildren();
  for(const [id,title] of Object.entries(titles)){const b=el('button',title,'case-choice');b.type='button';b.classList.toggle('selected',id===selectedCase);b.setAttribute('aria-pressed',id===selectedCase);b.append(el('small',data.cases[id]['corrected-result.json'].run_id));b.onclick=()=>{selectedCase=id;cases();};$('case-choices').append(b);}
  const c=data.cases[selectedCase],r=c['corrected-result.json'],content=$('case-content');content.replaceChildren();
  const panel=el('article',undefined,'panel');panel.append(el('p',r.run_id,'eyebrow'),el('h2',titles[selectedCase]));const meta=el('div',undefined,'case-meta');meta.append(badge(`Sesija: ${r.status}`),badge(`Uspeh protokola: ${r.success?'DA':'NE'}`,!r.success),badge(`Završni katalog: ${r.checker_valid?'VALIDAN':'NEVALIDAN'}`,!r.checker_valid),badge(`Agentske provere: ${r.checker_attempts}`));panel.append(meta);
  const note=selectedCase==='02-human-review'?'Agent je tražio ljudski pregled, bez izmena i bez poziva checker-a. Ovo ostaje neuspeh autonomne popravke.':selectedCase==='03-clean-control'?'Referentni katalog, ulaz i izlaz imaju isti hash. Provera nije zahtevala izmenu.':'Polje agent_confidence uklonjeno je iz Markdown-a i skrivenog JSON-a pre prve uspešne agentske provere.';
  panel.append(el('p',note),criteriaPanel(r),el('h3','Agentska izmena · input → output'),diff(c['repair.diff'])); const inj=el('details');inj.append(el('summary','Koja je greška ubačena? · referenca → input'),diff(c['injection.diff']));panel.append(inj);content.append(panel);
  const comparisons=el('article',undefined,'panel');const toggle=el('label',undefined,'view-switch'),check=el('input');check.type='checkbox';toggle.append(check,document.createTextNode('Prikaži ceo katalog umesto odlomka'));comparisons.append(el('h2','Pre i posle'),toggle);const grid=el('div',undefined,'two-col');const before=el('pre',undefined,'code-panel'),after=el('pre',undefined,'code-panel');for(const [heading,p] of [['Ulazni katalog',before],['Izlazni katalog',after]]) {const div=el('div');div.append(el('h3',heading),p);grid.append(div);}comparisons.append(grid);function update(){before.textContent=c[check.checked?'input.md':'input-excerpt.md'];after.textContent=c[check.checked?'output.md':'output-excerpt.md'];}check.onchange=update;update();content.append(comparisons);
  const reports=el('article',undefined,'panel');reports.append(el('h2','Nezavisni izveštaji evaluatora'),el('p','Početna i završna evaluatorska provera nisu agentski pozivi i ne vraćaju se agentu kao povratna informacija.'));const rg=el('div',undefined,'report-grid');for(const [heading,key] of [['Pre sesije','initial-checker.json'],['Posle sesije','final-checker.json']]) {const d=el('div');d.append(el('h3',heading),el('pre',JSON.stringify(c[key],null,2),'code-panel'));rg.append(d);}reports.append(rg);content.append(reports);
  const message=el('article',undefined,'panel');message.append(el('h2','Završna poruka agenta'),el('pre',c['agent-final.txt'],'case-message'));content.append(message);
  const details=el('details',undefined,'panel');details.append(el('summary','Ocena, zaštićena polja i audit'),el('pre',JSON.stringify({ocena:r,audit:c['audit-summary.json']},null,2)));content.append(details);
}
function showPair() {
  const pairId=$('pair-choice').value;
  $('pair-panels').replaceChildren();
  for(const [index,s] of SessionEvidence.pair(data.sessions,pairId).entries()) {
    const col=el('section',undefined,'pair-column');
    col.append(el('h2',index===0?'with-checker':'without-checker'));
    if(!s){col.append(el('p','Nema sačuvane završene sesije.'));$('pair-panels').append(col);continue;}
    const r=s.result;
    col.append(el('p',r.run_id,'muted'),badge(`Uspeh sesije: ${r.success?'DA':'NE'}`,!r.success),el('p',`Agentske provere: ${r.checker_attempts} · Ljudski pregled prijavljen: ${r.human_review_reported?'DA':'NE'}`),criteriaPanel(r));
    col.append(el('h3',`Odlomak: ${s.excerpt_testcase}`),el('p',r.condition==='clean'?'Kontrola: prikazan TC-001. Hash-evi i diff odnose se na ceo katalog.':'Prikazan je ciljni test; diff i hash-evi odnose se na ceo katalog.','muted'));
    col.append(el('h3','Agentska izmena'),diff(s.repair_diff));
    const beforeAfter=el('details');beforeAfter.append(el('summary','Ulaz i izlaz'),el('h3','Pre'),el('pre',s.input_excerpt,'code-panel'),el('h3','Posle'),el('pre',s.output_excerpt,'code-panel'));col.append(beforeAfter);
    const reports=el('details');reports.append(el('summary','Nezavisni izveštaji evaluatora'),el('pre',JSON.stringify(s.reports,null,2),'code-panel'));col.append(reports);
    const score=el('details');score.append(el('summary','Ocena i hash-evi'),el('pre',JSON.stringify(r,null,2),'code-panel'));col.append(score);
    $('pair-panels').append(col);
  }
}
function sessionList() {
  const filters={};
  for(const key of ['condition','mode','fault','outcome','query'])filters[key]=$(`filter-${key}`).value;
  const all=Object.values(data.sessions).map(s=>s.result);
  const rows=SessionEvidence.filter(all,filters);
  $('session-count').textContent=`Prikazano ${rows.length} / ${all.length} završenih sesija`;
  $('session-rows').replaceChildren();
  for(const r of rows) {
    const tr=el('tr'),id=el('td',`${r.order}. ${r.run_id}`);
    tr.append(id,el('td',r.condition==='clean'?'Kontrola':(labels[r.fault_class]||r.fault_class)),el('td',r.mode),el('td',r.checker_valid?'DA':'NE'),el('td',r.success?'DA':'NE'));
    const cell=el('td'),open=el('button','Uporedi','row-open');open.type='button';
    open.onclick=()=>{$('pair-choice').value=r.pair_id;showPair();$('pair-choice').focus();};
    cell.append(open);tr.append(cell);$('session-rows').append(tr);
  }
  if(!rows.length){const tr=el('tr'),cell=el('td','Nema sesija za odabrane filtere.');cell.colSpan=6;tr.append(cell);$('session-rows').append(tr);}
}
function initSessions() {
  for(const [key,label] of Object.entries(labels)) {const option=el('option',label);option.value=key;$('filter-fault').append(option);}
  const pairs=[...new Set(SessionEvidence.filter(Object.values(data.sessions).map(s=>s.result)).map(r=>r.pair_id))];
  for(const id of pairs){const option=el('option',id);option.value=id;$('pair-choice').append(option);}
  $('session-notice').textContent=`Istorijski dokazi: ${data.summary.completed_runs} završenih sesija. Infrastrukturni prekidi: ${data.summary.interrupted_attempts} (neocenjeni, nisu u tabeli). Pilot-sesije su isključene. Nema novih izvršavanja.`;
  for(const key of ['condition','mode','fault','outcome'])$(`filter-${key}`).addEventListener('change',sessionList);
  $('filter-query').addEventListener('input',sessionList);
  $('pair-choice').addEventListener('change',showPair);
  $('reset-filters').onclick=()=>{for(const key of ['condition','mode','fault','outcome','query'])$(`filter-${key}`).value='';sessionList();};
  sessionList();showPair();
}
async function start(){try{const response=await fetch('/api/data');if(!response.ok)throw new Error('Podaci nisu dostupni.');data=await response.json();results();selectedTest=data.catalog[0].testcase_id;catalogList();catalogDetail(data.catalog[0]);cases();initSessions();$('search').addEventListener('input',catalogList);window.addEventListener('hashchange',navigate);navigate();$('loading').hidden=true;$('app').hidden=false;}catch(error){$('loading').textContent=`Prikaz nije učitan: ${error.message} Proveri terminal i sačuvane dokaze.`;}}
start();
