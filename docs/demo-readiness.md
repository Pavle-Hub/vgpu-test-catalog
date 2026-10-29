# Spremnost za demonstraciju i pokretanje na drugom računaru

Ovo je tehničko uputstvo, ne dodatni eksperiment ili tekst poglavlja rada.
Priprema ne prepisuje istorijske rezultate i ne zahteva nove agentske pozive.

## 1. Brza lokalna provera

U korenu projekta:

```powershell
.venv\Scripts\python.exe tools\check_demo.py
```

Provera je read-only: proverava podržanu Python verziju, verzije tri osnovna
paketa prema lock fajlu, validnost dataset-a, trenutni katalog, hash-eve
prenosivih dokaza i prisustvo svih web resursa. Nema mrežnih poziva, pokretanja
agenta ili MCP servera, pisanja izveštaja ili automatske popravke.

- PASS: lokalna provera je prošla.
- WARN: odstupanje okruženja ili nedostupan opcioni Node; pročitaj poruku.
- FAIL: demonstracija nije spremna; exit code je 1.

Python 3.13.16 je referentna verzija. Druga podržana verzija ili odstupanje
paketa dobija upozorenje, ne tvrdnju da je novo okruženje identično referentnom.
Ne menjaj zaključani eksperimentalni protokol da bi uklonio upozorenje.

Za mašinski čitljiv ispis dodati `--json`. Poruka READY ne znači da je
izvršen kompletan pytest, browser test, živi MCP/agentski pilot ili udaljeni CI.
Preflight ne rezerviše port niti dokazuje da ga drugi proces neće zauzeti.
Njegova trenutna provera kataloga nije nova ocena neke stare agentske sesije.

## 2. Jednostavno Windows pokretanje

Posle instalacije okruženja možeš dvaput kliknuti `Start-Dashboard.cmd`.
Pokretač koristi sopstveni direktorijum i tačno njegov `.venv`, prvo izvršava
preflight i zaustavlja se pri grešci. Ne instalira pakete, ne menja pravila,
ne otvara PR i ne pokreće eksperimente. Otvori adresu koju ispiše:

```text
http://127.0.0.1:8765
```

Terminal ostaje otvoren dok traje prikaz; Ctrl+C zaustavlja server. Pokretač
ne otvara browser automatski. Ako je port zauzet, pokreni ručno:

```powershell
.venv\Scripts\python.exe tools\run_dashboard.py --port 8766
```

Za lokalni web prikaz ne trebaju internet, Codex nalog, Cursor ili agentski
tokeni. To je pregled istorijskih dokaza, ne živa samoispravka.

## 3. Priprema drugog Windows računara

Prenesi čistu kopiju projekta sa svim tracked fajlovima, uključujući
`docs/evidence/`, `web/`, `src/`, `schemas/`, `dataset/` i konfiguracione ulaze.
Najjednostavnije je klonirati Git repozitorijum. Ne kopiraj postojeći `.venv`
sa drugog računara: napravi ga lokalno sa instaliranim Python-om.

U korenu nove kopije, tokom pripreme sa pristupom internetu:

```powershell
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock
.venv\Scripts\python.exe -m pip install --no-deps -e .
.venv\Scripts\python.exe tools\check_demo.py
```

Prva komanda bira instalirani Python 3.13, ne instalira automatski tačno
3.13.16. Proveri ispis preflight-a. Testiraj pripremljeno okruženje pre odbrane;
ne oslanjaj se na preuzimanje paketa na licu mesta. Posle uspešne pripreme
dashboard se može prikazivati bez interneta.

Prenosivi paketi sa 60 sesija, primerima i slikama su u Gitu, pa dashboard
ne zahteva originalnu Git-ignored raw arhivu. Ta arhiva je ipak potrebna za
potpunu reproduktivnu evidenciju i mora ostati sačuvana posebno. U javnu kopiju
ne uključivati pristupne podatke, `.env`, korisničke konfiguracije ili ceo `.venv`.

## 4. Kratak pregled pred odbranu

1. Preflight bez FAIL stavki; razumeti svako WARN upozorenje.
2. Otvori dashboard i proveri: rezultati, katalog, tri primera, sve sesije i parove.
3. Izaberi broken-format-r02: različiti ishodi, sačuvani kriterijumi, bez novih poziva.
4. Otvori TC-010: insufficient-data je očekivani prikaz, ne problem weba.
5. Proveri dijagrame i dostupnost JSON/diff detalja.
6. Sačuvaj zasebno dokaze GitHub gate-a i blokiranog demonstracionog PR-a.
7. Zadrži rezervnu kopiju raw zbirke i dokumentuj commit korišćen za odbranu.

Ne praviti release tag automatski dok autor ne odabere konačnu verziju.
Ne ponavljati neuspešne eksperimente radi lepšeg rezultata i ne regenerisati
izvorni snapshot samo radi pokretanja web prikaza.
