# Human Context AI — Founder & Engineering Handbook

A five-volume foundational design document. Written chapter by chapter, each
chapter reviewed before the next is drafted. No filler, no repeated
paragraphs, no section that could be deleted without loss.

## Status

| Volume | Title | Scope (pages) | Status |
|---|---|---|---|
| 1 | Vision & Philosophy | 45–55 | Outline approved (7 ch.), writing Ch. 1 |
| 2 | Human Context Model | 50–70 | Not started |
| 3 | AI Architecture | 70+ | Not started |
| 4 | Product | — | Not started |
| 5 | Research Roadmap (5–10 yr) | — | Not started |

## The founding problem

Before anything else: [founding-problem.md](founding-problem.md) states the
real, personal problem this whole project answers to. Every volume should
be checked against it, not just Volume 1.

## Structure

Each volume is a directory. Each chapter is its own file, numbered, so it can
be reviewed and revised independently without touching the rest of the book.

```
handbook/
  volume-1-vision-and-philosophy/
    00-outline.md
    01-<chapter-slug>.md
    02-<chapter-slug>.md
    ...
  volume-2-human-context-model/
  volume-3-ai-architecture/
  volume-4-product/
  volume-5-research-roadmap/
```

## Working rules

- A chapter is not started until its place in the volume outline is approved.
- A chapter is not "done" until it's been reviewed and any revisions applied.
- Case studies, schemas, and diagrams live in the chapter they support — no
  separate appendix graveyard where content goes to be forgotten.
