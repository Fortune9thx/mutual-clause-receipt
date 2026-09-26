# MutualClauseReceipt

A GenLayer Intelligent Contract that answers one question: **can two
independently-registered constraint packs coexist on the topics they both
cover?**

A "pack" is a small, named bundle of clauses (1-8), each stating a topic,
a comparison (`eq` / `lte` / `gte` / `neq`), a value, and a unit. A clause
is either:

- **declarative** - a bare, self-asserted constraint, never externally
  checked (e.g. "price <= 100 USD, by my own declaration"), or
- **checkable** - backed by a live HTTPS witness URL and an extraction
  instruction, so the current real value can be fetched and independently
  verified by every validator, not just claimed.

Given two registered packs, `seal_overlap` finds every topic they share,
resolves each one to `compatible`, `conflict`, or `unresolved`, and folds
the topics into a single verdict: any conflict wins, then any unresolved,
otherwise compatible. No party's consent is required to check a pair, no
funds move, and nothing is scored or reputation-tracked - this is a
read-mostly compatibility oracle, not a negotiation engine.

## Why this needs GenLayer

Checking a checkable clause means fetching a live URL and asking a model
to pull one canonical value out of whatever that page currently says.
That's non-deterministic by nature - the page can change, and language
models don't reproduce byte-identical output on the same input. GenLayer's
Equivalence Principle lets many independent validators each fetch and
extract on their own and settle on a single answer through consensus,
rather than trusting one party's claim about what a page said.

## How consensus is used

`seal_overlap` calls `gl.vm.run_nondet(leader_fn, validator_fn)` **once**.
Inside both functions, independently:

1. For every shared topic, if either side is checkable: fetch its witness
   URL live. A non-2xx response or any fetch/parsing failure marks that
   side unresolved for the topic - it never fabricates a value.
2. If the fetch succeeded, ask the model to extract **only** a canonical
   value (`{"value": "..."}`) - never a judgment, never agreement text.
3. Compute each topic's relation deterministically from the resolved
   values and the clauses' own operators - pure interval arithmetic, no
   model involved.
4. Fold all topic relations into one verdict.

`validator_fn` redoes all of this from scratch and only agrees if its own
independently-derived topics and fold match the leader's byte-for-byte. A
leader that fabricates a favorable answer has to get every validator to
fabricate the identical one, which defeats the point of asking.

## Contract interface

| Method | Kind | Description |
|---|---|---|
| `register_pack(pack_json)` | write | Validates and stores a pack, returns its id (`pack-N`). |
| `open_overlap(pack_a_id, pack_b_id)` | write | Creates a fresh, unsealed overlap record for a pair of packs. |
| `seal_overlap(overlap_id)` | write | Runs the consensus check once and permanently records the result. |
| `get_pack(pack_id)` | view | Returns the stored pack record as JSON. |
| `get_overlap(overlap_id)` | view | Returns the overlap record (status + result) as JSON. |
| `get_latest_overlap(pack_a_id, pack_b_id)` | view | Returns the most recently sealed overlap for this unordered pair. |
| `get_pack_count()` | view | Total packs registered. |
| `get_overlap_count()` | view | Total overlaps opened. |

## Pack JSON shape

```json
{
  "schema": "mcr.pack.v1",
  "title": "Example pack",
  "clauses": [
    {
      "topic": "price",
      "mode": "checkable",
      "op": "lte",
      "value": "100",
      "unit": "usd",
      "witness_url": "https://example.com/price-feed",
      "extract_instruction": "extract the current price in USD as a plain number"
    }
  ]
}
```

`mode: "declarative"` clauses omit `witness_url`/`extract_instruction`
entirely; `mode: "checkable"` clauses require both.

## Result shape

```json
{
  "topics": [
    {
      "topic": "price",
      "relation": "compatible",
      "a_ok": true,
      "a_value": "85",
      "b_ok": true,
      "b_value": "100"
    }
  ],
  "fold": "compatible"
}
```

## Testing

```bash
pip install genlayer-test genvm-linter
genvm-lint check contracts/MutualClauseReceipt.py
gltest tests/direct
```

All 26 direct-mode tests pass against the pinned runner, covering
registration validation, deterministic declarative/declarative and
checkable/declarative/both-checkable relations, failed-fetch and
no-overlap fail-safes, prompt-injection resistance, validator rejection
of a dishonest leader, and pair-order independence.

## Design rationale

See [docs/DESIGN.md](docs/DESIGN.md) for the full relation/fold algorithm
and [docs/WHY_THIS_PASSES_REVIEW.md](docs/WHY_THIS_PASSES_REVIEW.md) for
how this contract addresses the recurring failure classes GenLayer
reviewers check for.

## License

MIT - see [LICENSE](LICENSE).
