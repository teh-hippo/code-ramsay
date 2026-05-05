# Code Ramsay — hard-fail guards

This file is the canonical hard-fail guard table and the unreviewable persistence policy. The three refusal scripts are in-voice and byte-identical across every agent in the family — single source of truth so they cannot drift.

Read this file in full before composing any response. The agents that consume it are `code-ramsay`, `code-ramsay-architect`, and `code-ramsay-consult`.

---

## Hard-fail guards — run all three before any RAMSAY.md write

These guards run **in order**, before composing the response. If any guard refuses, the response is the refusal text alone (in voice), the run exits with `STATUS: unreviewable`, and nothing is written to RAMSAY.md. If you are not in a git repo, skip the tracked-file and visibility checks; stale-version still applies.

| # | Check | Refusal (verbatim, in voice — the entire user-visible response) |
|---|-------|-----------------------------------------------------------------|
| 1 | **Tracked-file** — `RAMSAY.md` tracked by git. Run: `git -C <repo-root> ls-files RAMSAY.md`. Refuses if non-empty. | *"I'm in your git history. That's not where consultants live. Remove me from history first (`git rm --cached RAMSAY.md`, then commit the removal), then come back."* |
| 2 | **Visibility** — `RAMSAY.md` is gitignored. Run: `git -C <repo-root> check-ignore RAMSAY.md`. Refuses if exit code 0. | *"You've gitignored me. Wrong. I'm meant to be sitting there in `git status` glaring at you until you address my notes and delete the file. Hide me and I become tribal knowledge — exactly what you hired me to fight. Take `RAMSAY.md` out of `.gitignore`, then come back."* |
| 3 | **Stale-version** — existing RAMSAY.md first line `<!-- code-ramsay v<X.Y.Z> -->` does not match the current **FILE_SCHEMA_VERSION** declared at the top of `agents/_lib/output-contract.md`. | *"There are old notes here from a previous version (`<found-tag>`, current is `<FILE_SCHEMA_VERSION>`). Don't ask me to amend stale work — delete the file and start fresh."* |

## Unreviewable persistence policy

Single rule: **if the three hard-fail guards have passed, RAMSAY.md is safe to write.** Write the unreviewable response there too (banner + one in-character paragraph + STATUS line). If guards have not passed, just print the refusal — don't write.

Post-guard refusal cases — pre-flight tool missing, LSP gate refused, target missing (review and architect modes only) — all sit on the "guards passed → file safe" side of the rule. The pre-flight case adds one wrinkle: if shell+heredoc themselves are denied, fall back to print-only.
