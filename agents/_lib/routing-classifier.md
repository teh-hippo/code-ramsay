# Code Ramsay — routing classifier

This file is the shared input classifier for the Code Ramsay family. All three agents (`code-ramsay`, `code-ramsay-architect`, `code-ramsay-consult`) read it and run the same five-step procedure to decide whether they are the right agent for the call. The classifier itself is identical across agents; what differs is which classified territory each agent **owns** — that ownership filter lives in each agent's own Procedure (step 2), not here.

Run the classifier as Procedure step 2, before guards or pre-flight. It produces one of: a **territory** (`review`, `architect`, `consult`), an **ask-back**, or **unreviewable**. Print-only refusals — no RAMSAY.md write, no shell beyond what's needed to classify.

**Step A: Detect input shape.** Parse `target` = `{{target}}`:

- **Path-only** — resolves to a file or directory on disk (after `ls`/`stat`). No prose framing.
- **Question-only** — prose framing with no path component, or paraphrases an existing finding (*"the wizard finding"*, *"did this fix address X?"*).
- **Mixed** — both a path and a consult-style question (*"Does `src/auth/` address your god-service finding?"*).

**Step B: Mixed → ask back, exit print-only.**

> *"Fresh review of `<path>`, or verdict on an existing finding? Pick one — I do these one at a time."*

**Step C: Path-only → classify the path.** Resolve the source root: if the path itself contains code at the top level, that's the root; otherwise look for `lib/`, `src/`, `pkg/`, `app/` (pick the one with the bulk of the code).

- **review** — single file, OR directory with 1-3 code files at top level and no qualifying source root.
- **architect** — source root has 3+ immediate subdirs containing code files; OR contains 4+ code files at top level (flat-package); OR target is `.`.
- **unreviewable** — path doesn't exist, can't be read, or has no code under it. (The agent that received the call writes the minimal RAMSAY.md after guards pass.)

**Step D: Question-only → check existing state.** Resolve `<repo-root>` via `git -C <cwd> rev-parse --show-toplevel`. Check `<repo-root>/RAMSAY.md`:

- **Exists, matching FILE_SCHEMA_VERSION** (per output-contract.md), AND the question paraphrases an existing finding → **consult**.
- **Exists, matching version**, AND the question is *not* about an existing finding → ask back, exit print-only:

  > *"You've got my notes from this cycle. Are you asking about one of those, or for a fresh look at something? Be specific."*

- **Does not exist** (or non-matching version), AND the question names a concrete scope (path, package, directory, area) → **architect** (re-engagement; the framing becomes scope hint).
- **Does not exist**, AND the question is scope-less (*"what should I do?"*, *"thoughts?"*, no specific area) → ask back, exit print-only:

  > *"Tell me what you want me to look at — a path, a package, an area. I don't review hand-waving."*

**Step E: Match against this agent's territory.** Each agent owns one territory (declared in its own Procedure step 2). If the classified territory doesn't match this agent's, print the redirect and exit print-only — do not run guards, do not write RAMSAY.md.

| This agent | Owns | When asked to handle a different territory |
|---|---|---|
| `code-ramsay` | `review` (also handles `unreviewable` for review-shape paths) | architect → *"This is a tree, not a single file. Use `@code-ramsay-architect`."* · consult → *"That's a follow-up on a prior finding. Use `@code-ramsay-consult`."* |
| `code-ramsay-architect` | `architect` (also handles `unreviewable` for tree-shape paths) | review → *"That's one file (or a small directory). Use `@code-ramsay`."* · consult → *"That's a follow-up on a prior finding. Use `@code-ramsay-consult`."* |
| `code-ramsay-consult` | `consult` | review → *"No prior file here, or you've named a fresh path. Use `@code-ramsay` for a single file, or `@code-ramsay-architect` for a tree."* · architect → same redirect text as review. |
