# Changelog

All notable changes to this project are documented in this file.

## [1.0.0] - 2026-09-26

### Added

- `MutualClauseReceipt` contract: register content-typed constraint packs
  (1-8 clauses each, checkable or declarative) and seal a compatibility
  overlap between any two registered packs.
- Deterministic interval-based relation engine covering
  declarative/declarative, checkable/declarative, and
  checkable/checkable topic comparisons.
- Hand-rolled `gl.vm.run_nondet` leader/validator consensus for checkable
  clauses, with full independent re-fetch and re-extraction on the
  validator side.
- SSRF-safe HTTPS witness URL validation and length-bounded free-text
  fields on every clause.
- 26 direct-mode tests (`gltest tests/direct`), clean `genvm-lint check`.
- README, design docs, review-readiness notes, and Portal submission
  notes.
