# Human Context AI

An AI system that explains not just *who* someone was, but *why* they became
who they became — starting with public historical figures to prove the
reasoning works, built toward a much more personal goal: preserving a real
family's memory for descendants who never got to meet them.

## What's in this repo

- **[`handbook/`](handbook/)** — the founder & engineering handbook: vision,
  philosophy, and the actual problem this project answers to. Start with
  [`handbook/founding-problem.md`](handbook/founding-problem.md) if you want
  the real motivation, not the pitch.
- **[`mvp/`](mvp/)** — the working code. See [`mvp/README.md`](mvp/README.md)
  for what it does and how to run it.

## Status

**Phase 1 MVP is live and working.** Search any public historical figure and
get an evidence-linked breakdown of their timeline, environment, and
relationships — plus the actual point of the system: their real thinking
patterns. Every decision the person made is broken into *how* they decided
(decision-making style) and *how* they carried it out (execution style),
synthesized into named behavioral patterns, scored, and plotted on an
interactive trajectory graph showing how each pattern strengthened or faded
across their life.

Every claim — down to every individual chart data point — is tagged with an
Evidence Hierarchy level (Direct / Historical Record / Contemporary Account /
AI Inference) and links back to its source. No unsourced number is presented
as fact anywhere in the UI.

Validated across several rounds of tuning against multiple figures (Nikola
Tesla, Elon Musk, Adolf Hitler): plain-language output aimed at a global
audience, decision-level analysis instead of generic trait labels, and full
evidence traceability on every generated claim.

## Next step

Phase 1 exists to validate the reasoning engine somewhere safe — public
figures, abundant documentation, no consent issues. The actual motivation
(see [`handbook/founding-problem.md`](handbook/founding-problem.md)) is
preserving one real family's memory for its own descendants, not historical
trivia. That's next: the same engine, rebuilt for a single family, with user
accounts and strict per-family data isolation as a hard boundary from day
one — no cross-family access, ever.

## Tech stack

FastAPI + Python backend, OpenAI for reasoning, Wikipedia/Wikidata for public
source material, SQLite for caching, a dependency-free HTML/JS/SVG frontend.
No Neo4j/Qdrant/Kubernetes yet — those belong to the long-term technical
roadmap, not this stage.

## License

MIT — see [LICENSE](LICENSE).
