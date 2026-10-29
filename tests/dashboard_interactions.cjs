// Dependency-free DOM contract tests; real browser checks supplement these.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const base = path.join(__dirname, '..', 'web', 'dashboard');
const rules = require(path.join(base, 'sessions.js'));
const rows = Object.values(payload.sessions).map(s => s.result);
assert.equal(rules.filter(rows).length, 60);
assert.equal(rules.filter(rows, {condition:'clean'}).length, 10);
assert.equal(rules.filter(rows, {outcome:'failure'}).length, 4);
assert.equal(rules.filter(rows, {query:'no-such-run'}).length, 0);
const [left,right] = rules.pair(payload.sessions, 'broken-format-r02');
assert.equal(left.result.success, false);
assert.equal(right.result.success, true);
assert.ok(rules.criteria(right.result).every(c=>c[1]===true));
assert.equal(rules.criteria(left.result).filter(c=>c[1]===false).length, 4);
assert.equal(rules.criteria({...right.result,evidence_read:undefined})[3][1],null);

class Element {
  constructor(tag='div',id=''){this.tag=tag;this.id=id;this.children=[];this.attrs={};this.events={};this.dataset={};this.value='';this._text='';this.hidden=false;this.classList={toggle(){}};}
  set textContent(value){this._text=String(value);this.children=[];}
  get textContent(){return this._text+this.children.map(c=>c.textContent||'').join('');}
  append(...nodes){this.children.push(...nodes);if(this.id==='pair-choice'&&!this.value&&nodes[0])this.value=nodes[0].value;}
  replaceChildren(...nodes){this.children=[];this._text='';this.append(...nodes);}
  setAttribute(k,v){this.attrs[k]=v;}
  removeAttribute(k){delete this.attrs[k];}
  addEventListener(k,fn){this.events[k]=fn;}
  focus(){this.focused=true;}
  querySelector(key){return this.queries[key];}
  fire(event){if(this.events[event])this.events[event]();}
}
const ids=new Map();
function get(id){if(!ids.has(id))ids.set(id,new Element('div',id));return ids.get(id);}
const views=['results','catalog','cases','architecture','sessions'].map(v=>get(`view-${v}`));
const nav=views.map(v=>{const n=new Element();n.dataset.view=v.id.slice(5);return n;});
const interpretation=new Element();interpretation.queries={};
for(const key of ['h2','p:not(.eyebrow)','.callout','.muted'])interpretation.queries[key]=new Element();
const twoCol=new Element();twoCol.children=[new Element(),interpretation];
const document={getElementById:get,createElement:tag=>new Element(tag),createTextNode:text=>{const e=new Element();e.textContent=text;return e;},querySelectorAll:key=>key==='.view'?views:nav,querySelector:()=>twoCol};
const context=vm.createContext({document,Intl,console,location:{hash:'#sessions'},window:{addEventListener(){}},fetch:async()=>({ok:true,json:async()=>payload})});
vm.runInContext(fs.readFileSync(path.join(base,'sessions.js'),'utf8'),context);
vm.runInContext(fs.readFileSync(path.join(base,'app.js'),'utf8'),context);
setImmediate(()=>{
  assert.equal(get('app').hidden,false);
  assert.match(get('session-count').textContent,/60 \/ 60/);
  get('filter-outcome').value='failure';get('filter-outcome').fire('change');
  assert.equal(get('session-rows').children.length,4);
  get('filter-query').value='no-such-run';get('filter-query').fire('input');
  assert.match(get('session-rows').textContent,/Nema sesija/);
  get('reset-filters').onclick();assert.equal(get('session-rows').children.length,60);
  get('pair-choice').value='broken-format-r02';get('pair-choice').fire('change');
  assert.equal(get('pair-panels').children.length,2);
  assert.match(get('pair-panels').children[0].textContent,/Uspeh sesije: NE/);
  assert.match(get('pair-panels').children[1].textContent,/Uspeh sesije: DA/);
  assert.match(get('pair-panels').textContent,/Potrebni MCP dokazi/);
  get('search').value='TC-010';get('search').fire('input');
  assert.equal(get('catalog-list').children.length,1);
  assert.match(get('catalog-detail').textContent,/insufficient-data/);
  get('search').value='non-existent';get('search').fire('input');
  assert.match(get('catalog-detail').textContent,/Nema odgovarajućeg testa/);
  console.log('Dashboard interaction contracts passed: filters, pair selection, criteria, search, empty states.');
});
