# Catalog

`test_catalog.md` deliberately combines three ownership classes:

- `Purpose` and `Notes` are human-authored and must not be changed by automated
  synchronization.
- `Derived fields` are the only mechanically writable region. The visible list
  and hidden `catalog:derived-data` JSON are regenerated together.
- `Summary` is semantic agent output. The deterministic checker validates only
  its presence and declared length bounds, not whether its wording is true.

Run `catalog-check --check` for read-only verification. Use
`catalog-check --write` only as a local mechanical repair; CI must never invoke
write mode because doing so would replace the proposal it is meant to verify.

