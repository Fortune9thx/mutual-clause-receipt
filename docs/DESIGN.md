# Design

## Storage

`MutualClauseReceipt` stores everything as flat `TreeMap[str, str]` JSON
records plus two `u256` counters:

- `packs: TreeMap[str, str]` - `pack_id -> pack record JSON`
- `overlaps: TreeMap[str, str]` - `overlap_id -> overlap record JSON`
- `pair_to_latest: TreeMap[str, str]` - canonical pair key -> latest `overlap_id`
- `pack_counter`, `overlap_counter: u256` - also used to mint sequential ids

`__init__` is empty. The storage generator for this SDK generation
auto-allocates every declared field (including `TreeMap`) to a real
storage slot at class-definition time; assigning `self.field = TreeMap()`
by hand inside `__init__` is rejected outright on this runner. Ids are
plain sequential counters (`pack-0`, `overlap-0`, ...), not content
hashes - simple, proven, and avoids depending on hashing behavior inside
the sandboxed runtime that isn't otherwise exercised anywhere in this
contract.

## Validation (`register_pack`)

A pack must be `schema: "mcr.pack.v1"`, a non-empty `title` (<=200 chars),
and 1-8 clauses. Each clause needs a non-empty, pack-unique `topic`
(<=100 chars), `mode` in `{checkable, declarative}`, `op` in
`{eq, lte, gte, neq}`, a non-empty `value` (<=100 chars), and a `unit`
(<=50 chars). A checkable clause additionally requires a safe HTTPS
`witness_url` (<=500 chars) and a non-empty `extract_instruction`
(<=1000 chars); a declarative clause must have neither field set. `owner`
is always `str(gl.message.sender_address)` captured at registration -
never a caller-supplied parameter.

### Witness URL safety

`_is_safe_https_url` requires an `https://` scheme, a dotted hostname,
and rejects: `localhost`/`*.localhost`, a pure-digit hostname (covers
both a bare integer and decimal-encoded IP shorthand), a dotted IPv4
literal, anything containing `[` (IPv6 literal), an explicit port, and
embedded credentials (`user@host`). Every validator's own infrastructure
will independently try to reach whatever URL a pack author supplies, so
this check runs once, at registration, rather than being re-litigated on
every seal.

## The relation algorithm

Every clause's `(op, value)` maps onto a set of real numbers:

| op | set |
|---|---|
| `eq(v)` | `{v}` |
| `lte(v)` | `(-inf, v]` |
| `gte(v)` | `[v, inf)` |
| `neq(v)` | `R \ {v}` |

For two **declarative** clauses on the same topic, compatibility is
literally "do these two sets intersect?" - computed via
`_clause_interval` + a min/max intersection check
(`_interval_relation`), including the edge case where the intersection
collapses to a single excluded point (e.g. `eq(10)` vs `neq(10)`).

A **checkable** clause never uses its own declared `value` as ground
truth. Instead, the live-fetched, model-extracted value becomes a single
concrete point, which is tested against the *other* side's `(op, value)`
constraint (`_point_satisfies`) - "does the real, currently-witnessed
number satisfy what the other pack requires?" When **both** sides are
checkable, each extracted point is cross-checked against the *other*
clause's own constraint in both directions; compatible only if neither
witnessed fact contradicts the other pack's requirement.

If a required fetch/extraction fails (`a_ok`/`b_ok` false) or the two
clauses' units don't match after normalization, the topic resolves to
`unresolved` before any of the above math runs.

Per-topic relations fold via `_fold`: any `conflict` wins, else any
`unresolved` wins, else `compatible`. A pack pair with zero shared topics
never invokes consensus at all - it's stored as `{"topics": [], "fold":
"unresolved"}` directly, since there is nothing to check and nothing for
a model to look at.

## Consensus (`seal_overlap`)

`gl.vm.run_nondet(_leader, _validator)` is called **once**, only when at
least one shared topic exists. `_leader` and `_validator` each contain
their own complete, independent copy of the fetch-extract-relate-fold
loop - the actual `gl.nondet.web.get` / `gl.nondet.exec_prompt` calls are
written inline in both, not routed through a shared helper. This is
deliberate: `genvm-lint`'s static nested-nondeterminism check only
follows calls made directly from the function passed to `run_nondet` -
routing the loop through one shared helper breaks that check even though
the resulting behavior is identical. Purely deterministic pieces (the
relation math, the fold, the extraction prompt template) are still
shared, since they never touch a non-deterministic primitive.

`_validator` receives the leader's wrapped outcome (a `gl.vm.Return`,
exposing `.calldata`, or a `gl.vm.UserError` on leader failure) rather
than a plain value - it unwraps `.calldata`, recomputes everything from
scratch, and returns `True` only on an exact string match against the
re-serialized JSON. Any exception during that recomputation (a failed
`.calldata` access, a fetch error, a malformed extraction) is caught and
treated as disagreement, never re-raised.

## What `seal_overlap` does *not* do

- It never retries automatically. A sealed overlap (whatever its fold)
  is permanent; a caller who wants to check the same pair again later
  (e.g. a checkable witness may have changed) calls `open_overlap` again
  to create a fresh `overlap_id`. `pair_to_latest` always points at
  whichever sealed overlap for that pair happened most recently,
  regardless of which order the two pack ids were passed in.
- It never checks who is calling. Packs and overlaps are public,
  read-mostly facts about already-registered data - there is no owner
  gate on `open_overlap`/`seal_overlap`, since nothing here can be
  griefed beyond the caller's own gas.
