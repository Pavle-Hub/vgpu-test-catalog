# Obim praktičnog dela

## Tema rada

Automatizacija održavanja softverskih artefakata primenom AI agenata.

## Cilj demonstracije

Implementirati i eksperimentalno proveriti obrazac u kome AI agent predlaže
izmene dokumentacionog artefakta na osnovu podataka dostupnih preko MCP-a, dok
nezavisni deterministički alat proverava izvedene vrednosti i njihovo poreklo pre
nego što CI dozvoli spajanje izmene.

## Hipoteza

Nedeterministički rezultat AI agenta može bezbedno da učestvuje u obaveznom
razvojnom toku kada deterministički verifikator nezavisno potvrdi ugovorom
definisane vrednosti i provenijenciju.

## Minimalni obim

1. Seedovan generator sintetičkog skupa merenja.
2. Pinovani snapshot sa kanonskim content hash-om.
3. `metrics-mcp` server sa alatima za statistiku.
4. `env-mcp` server sa resursima o podržanim GPU konfiguracijama.
5. `rules.yaml` kao jedini deklarativni ugovor.
6. Markdown katalog sa ljudskim i izvedenim poljima.
7. Deterministički `catalog-check` CLI i strukturisani JSON izveštaj.
8. Cursor Skill `sync-catalog` sa najviše tri pokušaja samoispravke.
9. GitHub Actions provera i zaštita grane.
10. Framework za kontrolisanu injekciju grešaka i izračunavanje metrika.

## Van osnovnog obima

- stvarni ili interni podaci i nazivi sistema;
- web dashboard;
- baza podataka;
- treći MCP izvor;
- LLM-as-judge kao obavezni gejt;
- bezbednosna analiza MCP kanala;
- automatsko spajanje pull request-a;
- tvrdnja da je semantički sažetak egzaktno proverljiv.

## Referentni scenario

1. Novi snapshot merenja promeni content hash.
2. Postojeći katalog postane zastareo.
3. `catalog-check --check` prijavi neusaglašenost.
4. Skill pročita ugovor i podatke iz oba MCP izvora.
5. Agent izmeni samo dozvoljena izvedena polja i provenijenciju.
6. Checker vrati strukturisan izveštaj o eventualnim razlikama.
7. Agent pokušava popravku najviše tri puta, zatim eskalira čoveku.
8. GitHub Actions dozvoljava spajanje tek kada checker prođe.

## Kriterijumi završetka

- isti seed proizvodi isti skup podataka;
- isti sadržaj proizvodi isti snapshot hash;
- checker daje isti rezultat pri ponovljenim pokretanjima;
- svih pet definisanih klasa grešaka ima merljiv ishod;
- ispravan katalog prolazi bez lažnog pada;
- agent ne menja ljudska polja;
- lažna provenijencija pada i kada je izvedena vrednost slučajno tačna;
- premalo uzoraka proizvodi `insufficient-data`, a ne izmišljenu vrednost;
- neusaglašen pull request ostaje blokiran obaveznim statusom.

