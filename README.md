# Code Ramsay

> *"What the hell is this. Don't be lazy."*

A code reviewer with the temperament of Gordon Ramsay. Walks into your kitchen, tells you what's wrong, walks out. Direct, opinionated, and right roughly 99% of the time. He's not here to make you feel better.

Code Ramsay is a [GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli) custom agent that reviews source code for genuinely-bad design and surfaces it for conversation. **Critique only**, no edits — another agent owns implementation.

His kitchen is brownfield. He deliberately ignores `AGENTS.md`, `CLAUDE.md`, `copilot-instructions.md`, READMEs, and ADRs, so he sees what other agents have absorbed and stopped questioning.

## What he actually does

- **Reviews the target you point at** across three lenses (architecture, logical coupling, per-file design) and decides himself which ones matter.
- **Refuses to nit-pick.** A finding ships only if the resolving change is **structural** — moves a seam, redraws a boundary, separates fused concepts. No two-line tidies, no style sermons.
- **Names the failure mode and the kind of move** (split, lift, inline, extract). Never the fix. Never new symbol names. Never library suggestions. Another agent owns implementation.
- **Brings his own kit.** Doesn't invoke skills, doesn't read in-repo docs, doesn't accept "last time you said" framing. Each engagement is paid in fresh attention.
- **Writes one ephemeral file per cycle** at `<repo-root>/RAMSAY.md` — the receiving agent reads it, debates with Ramsay, decides what to fix, deletes it before implementation begins. **No cross-cycle history.**
- **Won't recommend the next flip in a back-and-forth.** A no-oscillation guardrail (`git log --follow` / `git blame`) runs before any directional finding.
- **Skeptical consult mode.** When an agent reports a fix, runs an anchor + 1-hop scan for transitional shims, translator pairs, and partial-status docstrings before stamping `consult-addresses`. Half-finished migrations get downgraded to `consult-partial` even when the agent acknowledges they're partial.

## Heads-up: the prompt is too big for `copilot plugin install` right now

The agent prompt currently exceeds the 30,000-character soft limit for Copilot CLI agents (it's around 74k). Direct repo install via `copilot plugin install` may not work yet. Shrinking is on the roadmap.

For now, install by dropping the agent file into your personal agents directory:

```sh
git clone https://github.com/teh-hippo/code-ramsay.git
cp code-ramsay/agents/code-ramsay.agent.md ~/.copilot/agents/code-ramsay.agent.md
```

Restart your Copilot CLI session and the agent is loaded.

## Usage

### Interactive — the primary use case

```sh
copilot                                                # opens an interactive session
> /agent code-ramsay
> review .                                              # whole-repo architect-mode review
> review lib/screens/multi_terminal_screen.dart         # single-file review
> Did splitting AuthService into Login/Token handle the god-class concern?  # consult mode
```

The receiving agent reads the file at `<repo-root>/RAMSAY.md`, debates with Ramsay (pushing back on findings, asking for verdicts on proposed fixes), decides what to address, **deletes the file**, then begins implementation.

### Programmatic

```sh
copilot --agent code-ramsay -p "review lib/" --allow-all-tools
```

## State: one file per cycle

`<repo-root>/RAMSAY.md`. **Not gitignored.** Ramsay refuses to write if it is.

The file dirties the root deliberately and stays visible in `git status` so the team can't forget it's there. Hide it in `.gitignore` and it becomes tribal knowledge, which is exactly what Ramsay is hired to fight.

**The receiving agent's only allowed write is `rm`.** They don't edit it. They don't mark findings done. They don't append. The file is Ramsay's handwriting; only Ramsay writes there.

**No cross-cycle memory.** Once the file's deleted, the next engagement starts fresh — no `Returning complaints` section, no `Resolved since last visit`, no per-repo notes file. Each cycle is its own thing. If you want Ramsay's view again later, hire him again.

## Hard-fail guards

Ramsay refuses to write `RAMSAY.md` if any of these hold:

1. **Leftover `.bully/`** anywhere in the repo (state from v0.7 or earlier) — clean it up first.
2. **`RAMSAY.md` is tracked by git** — `git rm --cached`, commit removal, then come back.
3. **`RAMSAY.md` is gitignored** (and you're in a git repo) — remove it from `.gitignore` so it stays visible in `git status`.
4. **Existing `RAMSAY.md` has a different version tag** in the HTML comment — delete the file and start fresh.

Each refusal lands in voice and exits with `STATUS: unreviewable`.

## Output structure

```
<!-- code-ramsay v0.8.3 -->

> [banner explaining the consultant boundary]

# Code Ramsay: review of <target> — <date>

## Get Your Act in Gear
### [architecture · BLOCKER · <path>]
**The complaint.** ...
**Why it'll bite you.** ...
**Direction.** ...

*I can't help you any further here until you get your act in gear.*

### [architecture · <path>]
... (other foundational findings, in weight order) ...

## Sharpen Up
... (per-file / neighbour structural work) ...

## Saw it. Couldn't be Arsed.
- *<target or symbol>* — ...

STATUS: findings | clean | unreviewable | consult-addresses | consult-partial | consult-not-addressed
```

`Get Your Act in Gear` orders blockers first (with the heading tag and inline closing line), then non-blocker giants. `Sharpen Up` is per-file/neighbour structural work — for mature codebases, most of what Ramsay says lives here. `Saw it. Couldn't be Arsed.` is the considered-and-dropped pile, including comment-mismatch one-liners and recurring nits, plus oscillation areas Ramsay decided not to flip again.

A footer line is appended to the printed response only (not the file):

> *Reminder: Once you begin implementation, you're on your own. Me, and my notes, are not part of that process.*

## Consult mode

When `RAMSAY.md` exists with a matching version tag and the user message is a question about a finding, Ramsay enters consult mode. **Singular**: one consult resolves one finding. The skeptical leftover-evidence scan runs before any `consult-addresses` verdict. The file is amended via the targeted-edit model: banner preserved verbatim, everything not under discussion preserved byte-identical, the discussed finding edited (or removed entirely on `consult-addresses`).

The printed reply is the verdict + reasoning, not the full file. The file is updated separately.

## Exit codes

| Code | Meaning | In-band marker |
|------|---------|----------------|
| 0    | Reviewable run (clean, findings, or consult verdict) | `STATUS: clean` / `findings` / `consult-addresses` / `consult-partial` / `consult-not-addressed` |
| 2    | Unreviewable (hard-fail guard refused, target missing, LSP gate refused) | `STATUS: unreviewable` |
| 3    | Engine error, retryable | `STATUS: model_error` |

## Eval suite

Lives under `eval/`. Plain pytest, uv-managed. Routes through the deployed agent so we exercise the production invocation path, not a direct model call.

```sh
cd eval
uv sync
uv run pytest                  # offline tests only (free)
uv run pytest -m live          # invokes the live agent (costs real model requests)
```

See `eval/README.md` for layout, design, and the baseline-recording flow.

## Development

When iterating on the agent prompt locally, be aware that **plugin installs are cached**. Editing `agents/code-ramsay.agent.md` in your clone does not propagate to the installed plugin at `~/.copilot/installed-plugins/_direct/teh-hippo--code-ramsay/` — Copilot CLI keeps using the cached copy until you explicitly refresh.

Three workflows for active development:

1. **Re-install on every change.** `copilot plugin uninstall code-ramsay && copilot plugin install /path/to/local/clone` (works against your local checkout, not the remote).
2. **Override via personal agents.** Drop the work-in-progress file at `~/.copilot/agents/code-ramsay.agent.md`; Copilot CLI prefers user-scoped agents over plugin-scoped, so your edits win immediately. Remove it when you're done.
3. **Pull from remote.** `copilot plugin update code-ramsay` after pushing — for testing what others will see.

Run `./scripts/check-pii.sh` before any push. It greps for known leakage patterns (developer paths, prior-fixture names, etc.) and exits non-zero if it finds anything.

## License

MIT. See `LICENSE`.
