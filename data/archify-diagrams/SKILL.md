---
name: "archify-diagrams"
description: "Create verified interactive architecture/sequence/workflow HTML diagrams with local archify (~/Repositories/archify) from repo analysis or descriptions."
---

# Archify Diagrams

Produce typed-JSON diagrams compiled by archify into self-contained interactive HTML. Never invent topology: every node/edge comes from reading the target repo or the user's explicit description.

Archify lives at `~/Repositories/archify` (CLI package in the nested `archify/` folder). All commands below run from `~/Repositories/archify/archify`. Set `ARCHIFY_UPDATE_CHECK_DISABLED=1` to keep it fully offline.

## Steps

1. **Preflight.** Run `node bin/archify.mjs doctor`. Completion: output ends with "Archify is ready." If modules are missing, run `npm install --no-audit --no-fund` in the nested `archify/` dir first.

2. **Pick diagram type.** When unsure, ask the CLI: `node bin/archify.mjs guide "<scenario>" --json`. Types: architecture (components/topology), workflow (ordered steps/branches), sequence (calls over time), dataflow (sources→transforms→stores), lifecycle (states/retries/terminals). Completion: one type chosen with rationale.

3. **Analyze the target.** For a repo, read README + docs/how-it-works + entrypoints/source layout and list real components, boundaries (what runs where), and the primary data/control path. For a description, extract participants, order, branches, exceptions. Completion: 8–12 core components max, one primary path; supporting detail goes to cards, not extra edges.

3a. **Model edge semantics honestly.** Connections are strictly directed (no bidirectional option in the schema). For every orchestrator→helper call whose result flows back (pure callee/library module), draw TWO edges: solid forward "call" + dashed reverse return — otherwise readers infer the helper's output vanishes or sits on the main path. Inspect actual handlers/endpoints, not names: any interface surface (GUI, CLI, upload/save API) that persists files needs its own edge to the store node even when another component also writes there; a node that both supplies and receives artifacts gets edges in both directions.

4. **Write the JSON IR** at `/tmp/archify-e2e/<name>.<type>.json`. Copy structure from the closest file in `examples/` (schema_version 1, diagram_type, meta with title/views, components with pos/size, connections, cards). Geometry rules that repeatedly pass showcase validation:
   - Keep total canvas width ≲ 1300px; long node sublabels shrink below the 6px desktop readability floor.
   - Lay out on a roomy grid (~40px+ gaps); leave vertical corridors between rows for routed edges.
   - Label short edges only when there is clear space above/below; prefer omitting labels on obvious emphasis edges.
   - Call/return edge pairs: auto-routing runs them nearly parallel and `composition/label-route-clearance` (min 4px) then kills one label. Route the return through a separate channel via explicit `fromSide`/`toSide` + orthogonal `via` points, and leave reverse edges unlabeled — the dashed variant plus a view note decodes them.
   - Cards accept no `pos`/`size` properties (schema/additionalProperties); keep card content to title/body only.

5. **Deliver through the atomic gate:** `node bin/archify.mjs deliver <type> <in.json> <out.html> --json`. Type comes BEFORE the input file (wrong order just prints usage). On `ok:false`, read `diagnostics[]`: each error names its subject and usually suggests exact fix coordinates (`labelAt [...]` or labelDy) — apply them verbatim and re-run. Budget 2 repair rounds; if still failing, simplify geometry (shorter labels, wider gaps, fewer labeled edges) instead of more patches. Completion: `ok:true`, `validation.checksPassed == checkCount`.

6. **Verify the artifact:** `node bin/archify.mjs check <out.html>` and optionally `visual-check <out.html> --json` (headless Chrome containment pass). Completion: both exit clean.

7. **Show output to the user.** The browser tool blocks `file://`; render with exec instead:
   ```bash
   google-chrome --headless=new --disable-gpu --window-size=1800,1200 --hide-scrollbars --screenshot=<shot>.png file://<abs-out.html>
   ```
   Send the PNG screenshot plus the HTML file itself (MEDIA: lines) so interactive features remain available. Completion: user received image + HTML paths.

## Reference

- Design delta review: `node bin/archify.mjs compare architecture <base.json> <head.json> <delta.html> --json` returns added/removed/changed/moved facts with a proof receipt.
- Optional live preview (loopback-only, watches one JSON): `preview <type> <in.json> <out.html>`; use `--no-open` in tests.
- Failure receipts to trust: `composition/label-route-clearance` (min 4px — move labelAt away from the neighboring edge), `composition/short-interior-segment` (move via points into a wider corridor), `artifact/orthogonal-arrows` (drop explicit route "straight" when endpoints differ in y; use default routing or via points), `composition/desktop-readability` (shrink canvas width / shorten node copy), `clean-flow/endpoint-side-direction` (each `via` segment must leave fromSide and reach toSide along that side's axis — vertical exit for top/bottom, horizontal entry for left/right; keep one right-angle per declared pair or drop sides/via entirely).
- Connection properties (architecture schema): id/from/to/label/variant(fromSide,toSide)/route(auto|straight|orthogonal-h|orthogonal-v)/via[]/labelAt/labelDx/labelDy/labelSegment/width. No arrowhead/bidirectional fields — model returns as separate dashed edges.
- Full authoring contract: `~/Repositories/archify/archify/SKILL.md`; schemas in `schemas/*.schema.json`.
