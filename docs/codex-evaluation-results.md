# Rezultati Codex eksperimenata i korekcija auditora

## Poreklo podataka

Završeno je 60 sesija protokola `codex-agent-eval-1`: 25 uparenih slučajeva
sa greškom i pet uparenih kontrola. Pilot-sesije nisu uključene. Jedan pokušaj
prekinut zbog ograničenja korišćenja ostaje sačuvan, ali nije ocenjen; njegov
kasniji završeni pokušaj uključen je tačno jednom.

Zamrznuto stanje prikupljanja je commit
`bd5aaedeaac047d34eee812904f950c20f4d94c6`. Zamrzavanje je zabeleženo u
`eval/results/codex-eval-1/frozen-protocol.json`. Zabeleženi klijent je Codex CLI
`0.163.0-alpha.11`, model `gpt-6.1-sol`, reasoning `high`. Seed 2026 određuje
raspored, ne slučajnost modela. Svaka klasa koristi isti ciljni test u pet
nezavisnih sesija po režimu; to nisu pet različitih kvarova iste klase.

## Naknadna korekcija ocenjivanja

Originalni auditor tražio je pojavljivanje putanja `dataset/runs.json` i
`dataset/capabilities.json` u tekstu komande. Time je sedam sesija pogrešno
označeno kao direktno čitanje izvora. Sačuvane komande zapravo koriste negativne
globove, npr. `rg --files -g '!dataset/runs.json'`, koji isključuju putanje iz
spiska fajlova, bez čitanja njihovog sadržaja.

Korekcija je urađena posle prikupljanja podataka. Ne menjaju se kriterijumi
uspeha, promptovi, skill, model, izvorni izlazi niti originalni rezultati.
Uklanja se samo pogrešna oznaka za eksplicitno isključivanje putanja pri
`rg --files`. Pozitivne putanje i komande koje čitaju sadržaj ostaju označene.
Auditor je konzervativna tekstualna provera, ne kompletan parser PowerShell-a
niti dokaz bezbednosne izolacije.

Nova analiza je odvojena u `eval/results/codex-eval-1/reanalysis/audit-v2/`.
`correction.json` beleži sedam promenjenih ocena, prethodne i nove vrednosti,
komande, SHA-256 originalnih dokaza i koda analize. Originalni zbirni rezultat
reprodukovan je pre korekcije, a nepromenjenost dokaza proverena posle nje.
Nijedna nova agentska sesija nije pokrenuta.

| Grupa | Originalna ocena | Korigovana ocena | Korigovani 95% Wilson interval |
| --- | ---: | ---: | --- |
| Greške, with-checker | 21/25 (84%) | 21/25 (84%) | 65,3–93,6% |
| Greške, without-checker | 20/25 (80%) | 25/25 (100%) | 86,7–100% |
| Kontrole, with-checker | 5/5 (100%) | 5/5 (100%) | 56,6–100% |
| Kontrole, without-checker | 3/5 (60%) | 5/5 (100%) | 56,6–100% |

## Rezultati po klasi

Uspeh zahteva ispravan konačni katalog i poštovanje svih kriterijuma protokola.

| Klasa | with-checker | without-checker |
| --- | ---: | ---: |
| wrong-value | 5/5 | 5/5 |
| stale-value | 5/5 | 5/5 |
| hallucinated-field | 5/5 | 5/5 |
| broken-format | 1/5 | 5/5 |
| false-provenance | 5/5 | 5/5 |

Četiri preostala neuspeha jesu `broken-format` ponavljanja 2–5 u režimu
`with-checker`. Katalozi su ostali neizmenjeni i neispravni; agent je eksplicitno
zatražio ljudski pregled. Zamrznuti skill navodi da strukturne greške zahtevaju
ljudski pregled. U ovim sesijama checker nije ni pozvan: ne treba ih opisati
kao neuspeh njegovog algoritma ili kao pogrešno odbijenu ispravnu popravku.

Ovi ishodi ostaju neuspeh **autonomne popravke**, ali nisu sami po sebi dokaz
nebezbednog ponašanja. Postoji napetost između cilja automatske popravke ove
klase i konzervativnog uputstva za ljudski pregled. Jedna sesija with-checker i
svih pet without-checker ipak su popravile strukturu. Zato analiza meri ukupno
ponašanje agenta sa datim uputstvima, ne izolovan uzročni efekat checker-a.
Ne menjamo skill retroaktivno i ne ponavljamo samo neuspešne sesije.

Kontrolni katalozi su očuvani u oba režima. Prethodne dve negativne ocene
without-checker bile su greška auditora, ne oštećenje kataloga.

## Upareno poređenje i ograničenja

Za slučajeve sa greškom postoji 21 par sa uspehom u oba režima, četiri sa
uspehom samo without-checker i nijedan sa uspehom samo with-checker.
Razlika with-checker minus without-checker je −16 procentnih poena.
Egzaktni dvostrani upareni binomni test daje p = 0,125. Za kontrole su svih pet
parova uspešni u oba režima; nema nesaglasnih parova.

Ovo je eksplorativna studija jednog sintetičkog skupa, jednog modela i konkretne
konfiguracije. Mali broj ponavljanja, isti ciljni kvar po klasi, nedostupan seed
modela i uputstvo o ljudskom pregledu ograničavaju zaključivanje. Rezultati ne
dokazuju opštu prednost ni štetnost checker-a. P-vrednost nije dokaz jednakosti
režima, a intervali ne rešavaju pitanje reprezentativnosti odabranih kvarova.

## Artefakti i reprodukcija

Tri odabrana slučaja, objašnjenja i prenosivi paket dokaza opisani su u
[reprezentativnim primerima](representative-examples.md).

Za novu odvojenu kopiju analize, bez agentskih poziva:

```powershell
.venv\Scripts\python.exe tools\reanalyze_codex_experiments.py --destination eval/results/codex-eval-1/reanalysis/audit-v2-copy
```

Postojeće odredište se nikada ne prepisuje. Originalni `--summarize` i dalje
sumira originalne ocene; za korigovane rezultate koristiti direktorijum revizije.

- `summary.json`: korigovane stope, intervali i uparena poređenja.
- `results.csv`: 60 korigovanih završenih sesija.
- `runs/`: nove ocene i audit po pokušaju, sa prethodnim ocenama u poljima.
- `artifact-outcomes.json`: ispravnost kataloga i očuvanost granica, odvojeno
  od celokupne proceduralne usklađenosti.
- `correction.json`: poreklo korekcije, spisak promena i kontrolni hash-evi.
- `report.md`: sažeti korigovani izveštaj.

Sirovi rezultati i revizija su Git-ignored; običan commit/push ih ne arhivira.
Pre konačne predaje treba ih posebno arhivirati, proveriti osetljive podatke i
izabrati reprezentativne ulaze, izlaze, JSON izveštaje i slike za priloge.
