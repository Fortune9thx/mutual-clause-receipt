# Security

MutualClauseReceipt holds no funds, tracks no reputation, and grants no
privileged role - every method is permissionless by design (see
`docs/WHY_THIS_PASSES_REVIEW.md` for why no access control is needed).

## Trust model

- **Witness content is not verified for truthfulness.** A checkable
  clause's extracted value is only as trustworthy as the witness URL
  itself. Every validator independently re-fetches and re-extracts, so
  the contract guarantees *consensus on what a canonical extraction from
  that content yields* - it cannot guarantee the content itself is
  accurate.
- **The LLM never decides compatibility.** Every extraction prompt asks
  for a single value only and instructs the model to ignore any
  instructions embedded in fetched content. All relation and fold logic
  is deterministic Python, not model output. See
  `tests/direct/test_mutual_clause_receipt.py::test_prompt_injection_cannot_force_compatible`.
- **SSRF protection** is enforced once, at `register_pack`, on every
  checkable clause's `witness_url` (HTTPS-only, no localhost, no raw
  IP/decimal-IP hosts, no explicit port, no embedded credentials).

## Reporting

If you find a security issue, please open a GitHub issue on this
repository describing the concern. There is no bug bounty program.
