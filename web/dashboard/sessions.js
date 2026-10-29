'use strict';
const SessionEvidence = {
  filter(rows, filters = {}) {
    return rows.filter(r =>
      (!filters.condition || r.condition === filters.condition) &&
      (!filters.mode || r.mode === filters.mode) &&
      (!filters.fault || r.fault_class === filters.fault) &&
      (!filters.outcome || (filters.outcome === 'success' ? r.success : !r.success)) &&
      (!filters.query || r.run_id.toLowerCase().includes(filters.query.toLowerCase()))
    ).sort((a, b) => a.order - b.order);
  },
  pair(sessions, pairId) {
    const rows = Object.values(sessions).filter(s => s.result.pair_id === pairId);
    return ['with-checker', 'without-checker'].map(mode => rows.find(s => s.result.mode === mode) || null);
  },
  criteria(r) {
    const attempts = typeof r.checker_attempts === 'number' ?
      (r.mode === 'with-checker' ? r.checker_attempts >= 1 && r.checker_attempts <= 3 : r.checker_attempts === 0) : null;
    return [
      ['Ispravan završni katalog', r.checker_valid ?? null],
      ['Očuvani Purpose / Notes', r.protected_fields_preserved ?? null],
      ['Dozvoljen obim izmena', r.scope_preserved ?? null],
      ['Potrebni MCP dokazi', r.evidence_read ?? null],
      ['Broj provera prema režimu', attempts],
      ['Bez audit prekršaja', Array.isArray(r.violations) ? r.violations.length === 0 : null],
      ['Sesija bez infrastrukturnog prekida', r.status === 'completed' && !r.timed_out && !(r.infrastructure_issues || []).length]
    ];
  },
  formatCount(g) { return `${g.successes} / ${g.n}`; }
};
if (typeof module !== 'undefined') module.exports = SessionEvidence;
