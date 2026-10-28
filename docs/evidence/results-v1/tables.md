# Tabele za diplomski rad — korigovano ocenjivanje audit-v2

## Tabela 1. Autonomne popravke po klasi greške

| Klasa | with-checker | 95% Wilson interval | without-checker | 95% Wilson interval |
| --- | ---: | --- | ---: | --- |
| Pogrešna vrednost (`wrong-value`) | 5/5 (100,0%) | 56,6%–100,0% | 5/5 (100,0%) | 56,6%–100,0% |
| Zastarela vrednost (`stale-value`) | 5/5 (100,0%) | 56,6%–100,0% | 5/5 (100,0%) | 56,6%–100,0% |
| Izmišljeno polje (`hallucinated-field`) | 5/5 (100,0%) | 56,6%–100,0% | 5/5 (100,0%) | 56,6%–100,0% |
| Narušen format (`broken-format`) | 1/5 (20,0%) | 3,6%–62,4% | 5/5 (100,0%) | 56,6%–100,0% |
| Netačno poreklo (`false-provenance`) | 5/5 (100,0%) | 56,6%–100,0% | 5/5 (100,0%) | 56,6%–100,0% |

Pet ponavljanja istog ciljnog kvara po klasi i režimu; ne pet različitih kvarova.

## Tabela 2. Zbirno za slučajeve sa greškom

| Režim | Uspešne popravke | 95% Wilson interval |
| --- | ---: | --- |
| with-checker | 21/25 (84,0%) | 65,3%–93,6% |
| without-checker | 25/25 (100,0%) | 86,7%–100,0% |

## Tabela 3. Kontrole bez ubačene greške (odvojeno od popravki)

| Režim | Uspešne kontrolne sesije | 95% Wilson interval |
| --- | ---: | --- |
| with-checker | 5/5 (100,0%) | 56,6%–100,0% |
| without-checker | 5/5 (100,0%) | 56,6%–100,0% |

## Tabela 4. Upareni ishodi i eksplorativni egzaktni test

| Grupa | Oba uspešna | Samo with | Samo without | Oba neuspešna | Razlika (pp) | p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Sa greškom | 21 | 0 | 4 | 0 | -16,0 | 0,125 |
| Kontrole | 5 | 0 | 0 | 0 | 0,0 | 1,000 |

Razlika je with-checker minus without-checker, u procentnim poenima.
Za kontrole nema nesaglasnih parova; p = 1 je konvencija, ne dokaz jednakosti.
Intervali su marginalni opisni intervali pojedinačnih stopa, ne interval razlike.
Jedan infrastrukturni prekid je neocenjen; pilot-sesije nisu uključene.
Četiri strukturna kvara sa zahtevom za ljudski pregled ostaju neuspešne popravke.
