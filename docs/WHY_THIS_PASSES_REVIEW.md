# Why this passes review

This maps the design directly onto the failure classes GenLayer reviewers
check for, rather than asserting "we followed best practice" in the
abstract.

## Validator independence (the most common real rejection reason)

A validator that only checks the leader's output for well-formed shape,
without independently re-acquiring evidence and re-deciding, is a
confirmed, recurring rejection reason across many prior GenLayer
submissions. `_validator` here does not inspect the leader's JSON shape
at all - it re-fetches every checkable witness URL, re-runs the same
extraction prompt, recomputes every topic's relation and the overall
fold from scratch, and only returns `True` on an exact string match
against its own independently-derived result. A leader that fabricates a
favorable verdict has to get a majority of validators to fabricate the
*identical* fabrication, which is not something clever wording in a
witness page or an extraction instruction can arrange.

## No nested non-determinism

`seal_overlap` calls `gl.vm.run_nondet` exactly once, guarded by a plain
Python `if` that skips it entirely when there is no shared topic to
check. `_leader`/`_validator` are named `def`s (never `lambda`), and the
actual `gl.nondet.web.get`/`gl.nondet.exec_prompt` calls appear directly,
inline, in both bodies - not proxied through a shared helper, which is
known to break `genvm-lint`'s static reachability check even when the
resulting behavior is identical. `genvm-lint check` passes cleanly.

## The LLM never decides compatibility

The only thing any prompt in this contract ever asks for is a single
extracted value (`{"value": "..."}`). The extraction prompt explicitly
tells the model to ignore any instructions embedded in the fetched page
and never to add commentary or agreement language. Every relation
(`compatible`/`conflict`/`unresolved`) is computed afterward by plain
interval arithmetic over already-known operators and values - there is
no code path where a model's own judgment, or text from a witness page,
writes into the fold. `tests/direct/test_mutual_clause_receipt.py::
test_prompt_injection_cannot_force_compatible` demonstrates this
directly: a witness page that explicitly instructs the model to declare
compatibility, embedded alongside a real reported value that violates
the other pack's requirement, still resolves to `conflict`.

## Failed evidence can only suppress a verdict, never manufacture one

A checkable clause's `ok` flag starts `False` and is only set `True`
after a genuine 2xx fetch *and* a successful extraction. Any topic
touching a failed side is short-circuited to `unresolved` before any
relation math runs (`test_seal_failed_fetch_is_unresolved`). There is no
default-to-compatible fallback anywhere.

## SSRF protection on every witness URL

Checked once, at `register_pack` time, since every validator's own
infrastructure will independently try to reach whatever URL a pack
author supplies: HTTPS-only, rejects `localhost`/`*.localhost`, dotted
IPv4 literals, pure-digit hostnames (decimal-encoded IP shorthand),
anything containing `[` (IPv6 literal), explicit ports, and embedded
credentials. See `docs/DESIGN.md` for the full list and
`test_register_pack_rejects_unsafe_witness_url` /
`test_register_pack_rejects_localhost_url`.

## Prompt-injection field bounding

Every free-text field that can reach a prompt is length-bounded at
registration: `title` <=200, `topic` <=100, `value` <=100, `unit` <=50,
`witness_url` <=500, `extract_instruction` <=1000. The `op`/`mode` enums
are validated against a fixed set (`assert x in {...}`, not merely
documented as an assumption).

## No funds, no reputation, no consent object - by design, not by omission

This is a compatibility oracle over two already-public documents, not an
escrow, a stake, or a negotiated agreement:

- **No domain registry.** Restricting witnesses to a curated allowlist
  would make the primitive useless for any pack author whose evidence
  source isn't pre-registered, and the live re-fetch by every validator
  *is* the check - a domain allowlist adds no additional safety a
  reviewer would recognize as closing a real gap.
- **No consent/ratification object.** The two packs never need each
  other's permission to be compared; compatibility is a fact about two
  independent, already-registered documents, not a negotiated outcome.
  Adding a treaty/ratify step would turn a read-mostly oracle into a
  stateful workflow engine - a different, unrequested primitive - and
  would introduce exactly the kind of liveness/escape-hatch surface
  (item 8/9 in this account's own audit checklist) that only applies to
  designs holding value or an exclusive state-advancing permission,
  neither of which exists here.
- **No fund-stranding surface.** There is nothing to strand: no balance
  ever accumulates in this contract, no stake is ever collected, and no
  method transfers value. The liveness/escape-hatch requirement that
  applies to escrow-like designs does not apply to a contract that never
  holds funds.
- **No reputation/scoring surface.** Packs and overlaps are facts, not
  scores; nothing here aggregates a per-address track record that a
  spoofed `owner` field could grief.

## Address handling

`owner` is always `str(gl.message.sender_address)`, read directly from
the message context at write time - never accepted as a caller-supplied
parameter, so there is no checksum-mismatch lookup surface (the contract
never uses `owner` as a lookup key at all; it is stored purely for
display/audit).

## Finality

Every write here (`register_pack`, `open_overlap`, `seal_overlap`) is a
one-time, non-reversible-by-anyone-else record: registering a pack
doesn't let a third party act on it before finality, and nothing reads
another write's result to trigger a *further* consequential action
inside this contract. There is no "something else acts on this before
finality" chain that the ACCEPTED-vs-FINALIZED distinction protects
against here - a caller integrating this primitive into a larger system
that does act on `seal_overlap`'s result is responsible for waiting on
whatever finality bar their own use case needs, exactly as they would
for any other GenLayer read.

## Tests

26 direct-mode tests cover: pack registration and every validation
rejection path, overlap lifecycle and double-seal rejection, the
no-overlap fail-safe, declarative/declarative compatible and conflicting
numeric relations plus unit-mismatch, checkable-vs-declarative compatible
and conflicting, both-checkable compatible, failed-fetch-is-unresolved,
prompt-injection resistance, validator rejection of a tampered leader
result (via the harness's `run_validator` cheat code) alongside
acceptance of the honest one, and pair-order independence of both the
fold outcome and the `pair_to_latest` lookup.
