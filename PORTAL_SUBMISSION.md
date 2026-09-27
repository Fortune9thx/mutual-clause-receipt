# Portal Submission

## Summary

MutualClauseReceipt is a reusable GenLayer primitive: given two
independently-registered constraint packs, it decides whether they can
coexist on the topics they both cover, using live-witnessed evidence for
any clause that claims to be checkable and pure deterministic interval
math for the actual compatibility verdict. No funds, no reputation, no
consent/ratification object, no domain registry.

## Deployed contract

- Network: GenLayer Studio Devnet (chain 61997)
- Address: `0x91BC43cC104705600b6afD1a1F07f1Ea33c21585`
- Deploy transaction: `0x9258a67b8095967e4e5e40fd84bc061973d1b41561d44dc0d88c2c9f76963e94`
  (FINALIZED, MAJORITY_AGREE)
- Explorer: https://explorer-studio-dev.genlayer.com/address/0x91BC43cC104705600b6afD1a1F07f1Ea33c21585
- Deployed source matches GitHub `master` at commit `1f40552` (includes
  the leader/validator value-canonicalization fix) exactly - this
  address supersedes an earlier deploy at `0x9B661ec91B1D1C82791C88B4a43134EDBa203892`,
  which was built from an older commit that predated that fix and has
  been retired; do not use it as evidence.

Live end-to-end verification performed against this exact deployment
(not just gltest): `register_pack` called twice (real FINALIZED writes,
returning `pack-0` and `pack-1`), then `open_overlap` + `seal_overlap`
ran a genuine `gl.vm.run_nondet` leader/validator consensus round -
including a real checkable clause (witness `https://httpbin.org/base64/MTIz`,
a stable endpoint that always decodes to the literal text `123`) checked
against a declarative pack requiring `<= 200`. This exercised a real
`gl.nondet.web.get` fetch and `gl.nondet.exec_prompt` extraction on both
the leader and the validator, with `_canonicalize_value` normalizing the
extracted number before comparison. Seal transaction
`0x075d1ac0be0368959ac1967ec847feffa3b63f64062b3c32c240946ad6075147`
(FINALIZED, `FINISHED_WITH_RETURN`); reading `get_overlap("overlap-0")`
back from the deployed contract returns:

```json
{"overlap_id": "overlap-0", "pack_a_id": "pack-0", "pack_b_id": "pack-1",
 "result": {"fold": "compatible", "topics": [{"a_ok": true, "a_value": "123",
 "b_ok": true, "b_value": "200", "relation": "compatible", "topic": "test_value"}]},
 "status": "sealed"}
```

## Repository

- GitHub: https://github.com/Fortune9thx/mutual-clause-receipt
- Contract: `contracts/MutualClauseReceipt.py`
- Tests: `tests/direct/test_mutual_clause_receipt.py` (26/26 passing,
  `gltest tests/direct`)
- Lint: `genvm-lint check contracts/MutualClauseReceipt.py` passes clean
  (3 checks, 0 warnings)

## What it does

- `register_pack(pack_json)` validates and stores a bundle of 1-8
  clauses (topic + operator + value + unit, checkable or declarative),
  returning a sequential `pack_id`.
- `open_overlap(pack_a_id, pack_b_id)` opens a fresh comparison between
  two registered packs.
- `seal_overlap(overlap_id)` finds every topic the two packs share,
  independently fetches and extracts a canonical value for each
  checkable side (validators re-fetch and re-extract from scratch, never
  trusting the leader's claim), computes each topic's relation via
  deterministic interval arithmetic, and folds the results into
  `compatible` / `conflict` / `unresolved`.
- Four view methods (`get_pack`, `get_overlap`, `get_latest_overlap`,
  `get_pack_count`, `get_overlap_count`) expose stored state.

## Why GenLayer is required

Checkable clauses depend on live web content that changes and on model
extraction, which is not byte-reproducible by nature. GenLayer's
Equivalence Principle lets independent validators each fetch and extract
on their own and settle through consensus rather than trusting a single
party's claim - exactly the trust problem a plain smart contract cannot
solve on its own (no native HTTP access, no model access, no way to
verify a claimed extraction without re-doing the work).

## Consensus design

`gl.vm.run_nondet(_leader, _validator)`, called once per seal. Both
functions independently fetch, extract, compute relations, and fold;
`_validator` accepts the leader's wrapped outcome, recomputes everything
from scratch, and only agrees on an exact match. See
`docs/DESIGN.md` and `docs/WHY_THIS_PASSES_REVIEW.md` for the full
rationale, including why the LLM is never asked to judge compatibility
directly and why a failed witness fetch can only produce `unresolved`,
never `compatible`.

## Testing evidence

26 direct-mode tests, all passing:

- Registration validation (schema, clause count, duplicate topics,
  checkable/declarative field requirements, unsafe witness URL
  rejection, invalid operator).
- Overlap lifecycle (open, double-seal rejection, unknown-pack/overlap
  lookups).
- No-overlap fail-safe (zero shared topics -> `unresolved`, no
  consensus call at all).
- Declarative/declarative compatible and conflicting numeric relations,
  plus unit-mismatch -> `unresolved`.
- Checkable-vs-declarative compatible and conflicting.
- Both-checkable compatible.
- Failed fetch -> `unresolved`.
- Prompt-injection resistance: a witness page instructing the model to
  declare compatibility, alongside a real value that violates the other
  pack's requirement, still resolves to `conflict`.
- Validator rejection of a tampered leader result, and acceptance of the
  honest one, via the test harness's `run_validator` cheat code.
- Pair-order independence of both the fold outcome and the
  `pair_to_latest` lookup.

## Known limitations

- A witness URL's *content* cannot be verified for truthfulness, only
  that independent validators agree on what a canonical extraction from
  that content yields. A compromised or adversarial witness source is a
  witness-integrity problem outside this contract's control - this is
  the same trust boundary every oracle-style GenLayer contract has.
- A pack with many overlapping checkable topics (up to 8 clauses per
  pack) can require several independent fetch+extract round trips inside
  one `seal_overlap` call, which is measurably heavier than a
  single-fetch design and can be more exposed to validator timeouts on a
  congested network. This is a disclosed cost/latency tradeoff, not a
  correctness gap.
