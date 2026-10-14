# Router result review: saved response, candidate taxonomy

## What is saved

Below the external run root, `skillopt-verusage/card-organization-20261012-v2/`:

- `proposals/router.json`: unmodified parsed model output,183826bytes.
- `calls/router/b58a341fa74f01de7da22a665f199a4dae9c74ac73f45c57206fa712bf184d21/response.raw`:
  saved returned response,379044bytes.
- `provider_capture/57e096eb78104c05a0493cc98b811faf/response.txt`:
  redacted provider envelope,379124bytes; status completed, model deepseek-v4-pro,
  reasoning/message output blocks and usage are present.
- Request, context admission, validated response, budget and provider ledger.

The earlier incomplete65536-token response body was not saved by the old client.
The successful131072-cap retry is saved; do not conflate these two attempts.

## Format-only normalization

`scripts/adopt_card_router.py` converts keyed objects to arrays after checking
each key equals card_id, and canonicalizes source-field capitalization. It copies
all excerpts and semantic text unchanged. The original response remains immutable.
The reduction-stage directory contains normalized `proposals/router.json` and
`router_normalization.json` with both hashes and the complete conversion list.
No API call or cost was incurred by normalization or adoption.

Checks:78/78cards,86cases,37reachable families, all source anchors match in the
specified original field, all primary/cross-linked cases covered. These are
structural checks, not proof that each inferred scope is semantically faithful.

## Taxonomy review and limits

Family sizes:16singletons,8pairs,9triples,2groups of4,1group of5,1group of6.
All37entry/exclusion descriptions and21inter-card relations were inspected.
The taxonomy is relatively fine-grained; no target family count was forced.
Full directory wording totals roughly27KJSON characters before rendering, so
fewer index entries does not establish a shorter index than the flat control.
Measure the rendered file and review its actual entry conditions before freezing.

Critical source-boundary checks:

- Cards018/057 separately preserve trigger inference and missing antecedent cases
  using conditional links between two families, rather than requiring both repairs.
- Card052 remains post-verification cleanup, excluded from failed-proof repair.
- Card058 is concrete instantiation of available universal/entailment facts,
  not trigger inference or missing antecedent repair.
- Card018 has Action/Validate wording tension noted in the earlier prompt review.
  Router returned empty review_items and did not flag it. The independent review
  receipt explicitly retains this unresolved issue; no source correction approved.
- Loop cards035/036/041 are described as successive layers in a relation. This
  does not establish a mandatory sequence; the unchanged reducer prompt forbids
  inventing workflow dependencies between complementary advice.

Decision: permit draft reductions under the existing construction authorization,
not approve taxonomy, merged content, or deployment. Review any merged018rule
against both original diagnoses; preserve original wording if safe merging is
unsupported. Review the loop group for invented prerequisites. Recheck all merged
clauses against their actual cited sources, not only card-ID coverage.

No validation/test results were used to choose the groups. No actor evaluation
has run. Card quality, relevance, retrieval rate and downstream benefit remain
unmeasured for this candidate. Raw/sealed data and source card bodies are unchanged.
