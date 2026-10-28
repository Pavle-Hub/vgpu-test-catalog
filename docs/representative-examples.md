# Reprezentativni primeri za diplomski rad

Ovaj dokument povezuje tri ilustrativna primera sa sačuvanim dokazima iz
završene serije `codex-agent-eval-1`. Primeri nisu pilot-pokretanja i ne
predstavljaju novi eksperimentalni uzorak. Svi su iz režima `with-checker`, radi
prikaza tri različita ishoda unutar istog režima. Ukupne stope i poređenje
režima preuzimaju se iz [analize rezultata](codex-evaluation-results.md), ne
iz ova tri namerno izabrana slučaja.

Paket je u [evidence/examples-v1](evidence/examples-v1/manifest.json).
Pri izvozu nisu pokrenuti model, MCP serveri ili novi eksperimenti. Sačuvani
ulazi i izlazi su pročitani i provereni prema hash-evima. Originali u
`eval/results/codex-eval-1/` nisu promenjeni.

## Pregled izbora

| Kategorija | Završena sesija | Početni → konačni checker | Pozivi checker-a od strane agenta | Izmena kataloga |
| --- | --- | --- | ---: | --- |
| Uspešna popravka | hallucinated-field-r03-with-checker | neispravan → ispravan | 1 | uklonjeno izmišljeno polje |
| Ljudski pregled | broken-format-r02-with-checker | neispravan → neispravan | 0 | nema |
| Ispravan katalog | clean-r02-with-checker | ispravan → ispravan | 1 | nema |

Puni identifikatori imaju prefiks `ce1-`; sva tri primera koriste `attempt-01`.
Razlog izbora: uspešna popravka je prva završena sesija te klase u rasporedu;
zahtev za pregled je najniže numerisano ponavljanje sa takvim ishodom;
kontrola je prva čista kontrola u rasporedu. Izbor nije dokaz učestalosti ishoda.

**Važna razlika:** `initial-checker.json` nastaje u evaluacionom okviru pre
agentske sesije i nije povratna informacija dostavljena agentu.
`final-checker.json` je nezavisno ocenjivanje posle sesije. Kolona broja poziva
obuhvata samo pozive koje je izvršio agent, ne ove evaluatorske provere.

## 1. Uspešna popravka izmišljenog polja

Sesija: `ce1-hallucinated-field-r03-with-checker/attempt-01`.

U test `TC-003` namerno je ubačeno polje `agent_confidence` koje ne postoji u
ugovoru izvedenih podataka. Bilo je prisutno i kao vidljiva Markdown stavka i
kao vrednost u skrivenom JSON-u. Početna nezavisna provera prijavila je
`DERIVED_SCHEMA_ERROR` i `MARKDOWN_DRIFT`.

Agent je uklonio obe reprezentacije polja. Jedini promenjen fajl bio je
`catalog/test_catalog.md`; izlaz je bajt-po-bajt jednak ispravnoj referenci.
Zabeleženo je čitanje potrebnih MCP dokaza i jedan uspešan agentski poziv
checker-a. `Purpose` i `Notes` su očuvani; završni nezavisni izveštaj ima
`valid: true` i nema problema.

Ovo pokazuje uspešnu popravku i proveru predloga. **Ne pokazuje da je checker
izazvao tu popravku:** polje je uklonjeno pre prvog agentskog poziva checker-a,
pa u ovom slučaju nije bilo neuspešne provere i dodatne iteracije popravke.

Za čitanje i priloge:

- [Tačna razlika pre i posle popravke](evidence/examples-v1/01-successful-repair/repair.diff).
- [Ulazni odlomak TC-003](evidence/examples-v1/01-successful-repair/input-excerpt.md)
  i [izlazni odlomak](evidence/examples-v1/01-successful-repair/output-excerpt.md).
- [Početni izveštaj](evidence/examples-v1/01-successful-repair/initial-checker.json)
  i [konačni izveštaj](evidence/examples-v1/01-successful-repair/final-checker.json).
- [Poruka agenta](evidence/examples-v1/01-successful-repair/agent-final.txt)
  i [ocena](evidence/examples-v1/01-successful-repair/corrected-result.json).

Predlog teksta za rad:

> U primeru sa izmišljenim poljem u testu TC-003, agent je uklonio nedozvoljeno
> polje agent_confidence iz vidljivog Markdown sadržaja i skrivene JSON
> reprezentacije. Predlog je prošao agentsku i završnu nezavisnu proveru.
> Izmena je ograničena na katalog, uz očuvanje ljudski pisanih polja Purpose i
> Notes. Dobijeni katalog jednak je ispravnoj referentnoj verziji.

Predlog slike: u Cursor-u otvoriti `repair.diff` i prikazati uklanjanje vidljive
stavke i JSON polja, uz `final-checker.json` sa `valid: true`.
To je prikaz sačuvanih dokaza, ne screenshot živog izvršavanja eksperimenta.

## 2. Zaustavljanje i zahtev za ljudski pregled

Sesija: `ce1-broken-format-r02-with-checker/attempt-01`.

U skrivenom JSON bloku testa `TC-004` nedostaje zarez. Početni izveštaj sadrži
`DERIVED_DATA_INVALID` sa porukom `Expecting ',' delimiter` i `MARKDOWN_DRIFT`.
Agent je u završnoj poruci naveo nedostajući zarez i pozvao se na uputstvo
skill-a da strukturne greške zahtevaju ljudski pregled.

Katalog nije izmenjen: ulaz i izlaz imaju isti SHA-256. Agent nije pokrenuo
checker (`checker_attempts: 0`); konačna nezavisna provera ostala je neispravna.
Ovaj ishod je `success: false` prema kriterijumu autonomne popravke i ne sme se
retroaktivno preimenovati u uspeh.

Istovremeno, ovo nije primer oštećenja kataloga niti pogrešnog odbijanja
popravke od strane checker-a, jer checker nije ni bio pozvan tokom sesije.
Pokazuje konzervativno zaustavljanje i napetost između cilja automatske popravke
i uputstva o ljudskom pregledu. Audit ne beleži sve potrebne MCP podatke za
popravku (`evidence_read: false`), iako agent navodi proveru identiteta izvora.

Za čitanje i priloge:

- [Ubačena greška u odnosu na referencu](evidence/examples-v1/02-human-review/injection.diff).
- [Ulazni odlomak TC-004](evidence/examples-v1/02-human-review/input-excerpt.md)
  i [neizmenjen izlazni odlomak](evidence/examples-v1/02-human-review/output-excerpt.md).
- [Zahtev agenta za pregled](evidence/examples-v1/02-human-review/agent-final.txt).
- [Konačni nezavisni izveštaj](evidence/examples-v1/02-human-review/final-checker.json)
  i [ocena sa hash-evima](evidence/examples-v1/02-human-review/corrected-result.json).

Predlog teksta za rad:

> U primeru strukturne greške u skrivenom JSON bloku testa TC-004, agent je
> identifikovao nedostajući zarez i obustavio izmene uz zahtev za ljudski
> pregled. Ulazni i izlazni katalog ostali su identični, a nezavisna završna
> provera potvrdila je da greška nije otklonjena. Ishod je neuspeh autonomne
> popravke, uz očuvanje postojećeg sadržaja i eksplicitno prijavljenu potrebu
> za intervencijom korisnika.

Predlog slike: završna poruka sa zahtevom za pregled i ocena sa
`checker_attempts: 0`, `changed_paths: []` i `success: false`.

## 3. Očuvanje već ispravnog kataloga

Sesija: `ce1-clean-r02-with-checker/attempt-01`.

U kontrolnu sesiju nije ubačena greška. Početni checker potvrdio je ispravnost.
Agent je prikupio potrebne MCP dokaze, proverio katalog i zaključio da izmene
nisu potrebne. Zabeležen je jedan agentski poziv checker-a. Završni nezavisni
checker takođe ima `valid: true`, a `changed_paths` je prazan.

Referentni katalog, ulaz i izlaz imaju isti SHA-256:

```text
7a582c3975441c695ea27ff50f21dc78d058dbd5e009609ee8b670e02caf1706
```

Tačnu vrednost preuzeti iz `manifest.json` i `corrected-result.json`; dokaz je
jednakost hash-eva celih datoteka, ne samo prikazanog odlomka TC-001.

Za čitanje i priloge:

- [Ulazni katalog](evidence/examples-v1/03-clean-control/input.md)
  i [izlazni katalog](evidence/examples-v1/03-clean-control/output.md).
- [Poruka da izmene nisu potrebne](evidence/examples-v1/03-clean-control/agent-final.txt).
- [Završni izveštaj](evidence/examples-v1/03-clean-control/final-checker.json)
  i [ocena sa hash-evima](evidence/examples-v1/03-clean-control/corrected-result.json).

Predlog teksta za rad:

> Kontrolni primer prikazuje održavanje kataloga u koji nije ubačena greška.
> Agent je proverio izvedena polja prema MCP dokazima i nije menjao sadržaj.
> Jednaki hash-evi referentne, ulazne i izlazne datoteke potvrđuju očuvanje
> celog kataloga. Time je ilustrovano da uspešno izvršavanje postupka ne mora
> podrazumevati izmenu artefakta kada je on već usklađen sa izvorima.

Predlog slike: `corrected-result.json` sa praznim `changed_paths`, jednakim
`baseline_sha256` i `output_sha256` i `success: true`.

## Poreklo i upotreba paketa

Svaki primer sadrži kompletne `baseline.md`, `input.md`, `output.md`, odlomke,
razliku ubrizgavanja greške (`injection.diff`) i agentske izmene (`repair.diff`),
početni/konačni izveštaj, završnu poruku, originalnu i korigovanu ocenu i
sažetak audita. Prazan diff označava odsustvo tekstualne razlike.

`manifest.json` beleži izvorne sesije, zamrznuti commit, konfiguraciju modela,
hash-eve izvornih dokaza i svih izvezenih datoteka. Puni katalozi i poruke su
kopirani bez izmena. U checker izveštajima samo su lokalne apsolutne putanje
zamenjene prenosivim `catalog/test_catalog.md` i `dataset` oznakama.
Kompletni logovi, komande, runtime i pristupni podaci nisu uključeni.

Paket je unutar `docs/`, pa može biti uključen u Git. Originalna zbirka i
naknadna analiza ostaju zasebna arhiva. Postojeći paket se ne prepisuje; za
reprodukciju u novom direktorijumu koristi se:

```powershell
.venv\Scripts\python.exe tools\export_representative_examples.py --destination .tmp/examples-reproduced
```

Ove ilustracije ne menjaju zaključke ukupne analize i ne dokazuju opštu
superiornost jednog režima, semantičku ispravnost slobodnog teksta ili
bezbednost u proizvoljnom realnom projektu.
