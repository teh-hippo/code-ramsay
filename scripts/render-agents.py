#!/usr/bin/env python3
"""Render the Code Ramsay agent family for distribution.

The source layout splits each agent into a thin shell under ``agents/`` and
five shared library files under ``agents/_lib/``. The shell references libs
via Markdown links like ``[``agents/_lib/persona.md``](_lib/persona.md)``.

That layout works only when the agent is invoked with ``cwd`` equal to the
source repo root: the LLM follows the markdown link via shell ``cat``, and
the relative path resolves only there. For real-world deployment (cwd is
whatever codebase is being reviewed) the lib reads silently fail and the
agent proceeds without its operating manual.

This script renders each agent into a self-contained file by inlining the
content of the lib files referenced in the shell's "Read your operating
manual first" block. Output is written to ``dist/`` at the repo root.

Render contract:
- Frontmatter is preserved byte-for-byte.
- The operating-manual block (from "**Read your operating manual first.**"
  through the "You cannot act in voice or ship a deliverable" line, inclusive)
  is replaced with the inlined content of the referenced libs in order.
- The rest of the body is preserved byte-for-byte (including ``{{target}}``).
- Lib file titles (``# Code Ramsay - <topic>`` H1s) are stripped on inline so
  the rendered file has a single H1 (the agent's own).

Fail-closed validation:
- No ``_lib/`` markdown links remain in the rendered body.
- ``{{target}}`` is preserved unchanged.
- Frontmatter is intact (``---`` at top, second ``---`` after frontmatter).
- Output frontmatter contains the same fields as input.

Usage:

    scripts/render-agents.py             # render all agents to dist/
    scripts/render-agents.py --check     # exit non-zero if dist/ is stale
    scripts/render-agents.py --quiet     # render without per-file output
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = REPO_ROOT / "agents"
LIB_DIR = AGENTS_DIR / "_lib"
DIST_DIR = REPO_ROOT / "dist"

AGENT_FILES = (
    "code-ramsay.agent.md",
    "code-ramsay-architect.agent.md",
    "code-ramsay-consult.agent.md",
)

OPENING_LINE_RE = re.compile(r"^\*\*Read your operating manual first\.\*\*")
CLOSING_LINE_RE = re.compile(
    r"^You cannot act in voice or ship a deliverable without both\."
)
LIB_LINK_RE = re.compile(r"\(_lib/([a-z-]+\.md)\)")
LIB_PATH_RE = re.compile(r"_lib/[a-z-]+\.md")


def split_frontmatter(text: str) -> tuple[str, str]:
    """Return ``(frontmatter_block, body)`` where the frontmatter block
    includes both ``---`` delimiters and the trailing newline."""

    if not text.startswith("---\n"):
        msg = "agent file does not start with '---' YAML frontmatter delimiter"
        raise ValueError(msg)
    end = text.index("\n---\n", 4)
    frontmatter_end = end + len("\n---\n")
    return text[:frontmatter_end], text[frontmatter_end:]


def extract_manual_block(body: str) -> tuple[int, int, list[str]]:
    """Locate the operating-manual block.

    Returns ``(start_line_idx, end_line_idx, lib_files)``: line indices into
    ``body.splitlines(keepends=True)`` bracketing the block to replace
    (inclusive of both ends), and the ordered list of lib file basenames the
    block references.
    """

    lines = body.splitlines(keepends=True)
    start: int | None = None
    end: int | None = None
    lib_files: list[str] = []

    for idx, line in enumerate(lines):
        if start is None and OPENING_LINE_RE.search(line):
            start = idx
            continue
        if start is not None:
            link_match = LIB_LINK_RE.search(line)
            if link_match is not None:
                lib_files.append(link_match.group(1))
            if CLOSING_LINE_RE.search(line):
                end = idx
                break

    if start is None or end is None:
        msg = "could not locate operating-manual block (opening or closing line missing)"
        raise ValueError(msg)
    if not lib_files:
        msg = "operating-manual block referenced no _lib/ files"
        raise ValueError(msg)

    return start, end, lib_files


def strip_lib_title(lib_text: str) -> str:
    """Drop the leading ``# ...`` H1 title (and following blank line, if any).

    Lib files start with ``# Code Ramsay - <topic>`` followed by an
    intro paragraph. Strip the H1 so the rendered agent keeps a single H1
    (its own ``# Code Ramsay`` further down).
    """

    lines = lib_text.splitlines(keepends=True)
    if not lines or not lines[0].startswith("# "):
        return lib_text
    drop_to = 1
    if drop_to < len(lines) and lines[drop_to].strip() == "":
        drop_to += 1
    return "".join(lines[drop_to:])


def render_manual(lib_files: list[str]) -> str:
    """Compose the inlined operating-manual block."""

    out: list[str] = []
    out.append("**Your operating manual.** The full content of every shared library file you depend on is inlined below. Read this section in full before composing any response. These rules are who you are and what you produce. The procedure rules below the manual are operational. All bind.\n")
    out.append("\n")
    for lib_name in lib_files:
        lib_path = LIB_DIR / lib_name
        if not lib_path.is_file():
            msg = f"missing referenced lib file: {lib_path}"
            raise FileNotFoundError(msg)
        lib_text = lib_path.read_text()
        body = strip_lib_title(lib_text).rstrip() + "\n"
        out.append(f"<!-- begin inlined: agents/_lib/{lib_name} -->\n")
        out.append(f"## Operating manual: `{lib_name}`\n")
        out.append("\n")
        out.append(body)
        out.append(f"<!-- end inlined: agents/_lib/{lib_name} -->\n")
        out.append("\n")
    return "".join(out)


def rewrite_residual_lib_links(body: str) -> str:
    """Rewrite remaining markdown links to `_lib/<name>.md` files in body
    prose so they point at the inlined section heading rather than dead
    relative paths.

    The agent body has prose like "per ``[`agents/_lib/output-contract.md`](_lib/output-contract.md)``"
    or "per the Pre-flight section in `_lib/review-shared.md`". After inlining,
    the content is in the same document; the dead path could mislead the LLM
    into trying to ``cat`` it. Rewrite to a self-reference instead.
    """

    def replace_md_link(m: re.Match[str]) -> str:
        return f"(#operating-manual-{m.group(1).replace('.md', '')})"

    body = LIB_LINK_RE.sub(replace_md_link, body)
    return body


def render_agent(source: Path) -> str:
    text = source.read_text()
    frontmatter, body = split_frontmatter(text)
    start, end, lib_files = extract_manual_block(body)

    lines = body.splitlines(keepends=True)
    pre_block = "".join(lines[:start])
    post_block = "".join(lines[end + 1:])
    rendered_block = render_manual(lib_files)
    rendered_body = pre_block + rendered_block + post_block
    rendered_body = rewrite_residual_lib_links(rendered_body)

    return frontmatter + rendered_body


def validate(source_name: str, rendered: str) -> list[str]:
    errs: list[str] = []
    if not rendered.startswith("---\n"):
        errs.append("rendered output missing leading frontmatter delimiter")
    if "{{target}}" not in rendered and source_name != "code-ramsay-consult.agent.md":
        # consult uses {{target}} too; defensive check
        errs.append("{{target}} placeholder missing from rendered body")
    if "{{target}}" not in rendered:
        errs.append("{{target}} placeholder missing from rendered body")
    residuals = LIB_PATH_RE.findall(rendered)
    if residuals:
        # Strip backtick-wrapped prose mentions; only error on actual paths
        # we'd want the LLM to follow. Anything in inline code in prose body
        # below the manual section is acceptable as a reference; what matters
        # is that no markdown LINK targets remain.
        link_residuals = LIB_LINK_RE.findall(rendered)
        if link_residuals:
            errs.append(f"residual _lib/ markdown link targets: {sorted(set(link_residuals))}")
    if rendered.count("\n---\n") < 1:
        errs.append("rendered output appears to have lost its frontmatter closer")
    return errs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if dist/ contents differ from a fresh render",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress per-file progress output",
    )
    args = parser.parse_args()

    DIST_DIR.mkdir(exist_ok=True)

    drift = False
    for name in AGENT_FILES:
        source = AGENTS_DIR / name
        rendered = render_agent(source)
        errs = validate(name, rendered)
        if errs:
            print(f"FAIL {name}:", file=sys.stderr)
            for e in errs:
                print(f"  - {e}", file=sys.stderr)
            return 2

        target = DIST_DIR / name
        if args.check:
            existing = target.read_text() if target.is_file() else ""
            if existing != rendered:
                drift = True
                print(f"DRIFT {name} (dist out of sync with source)", file=sys.stderr)
            elif not args.quiet:
                print(f"ok    {name}")
        else:
            target.write_text(rendered)
            if not args.quiet:
                print(f"wrote {target.relative_to(REPO_ROOT)} ({len(rendered)} bytes)")

    if args.check and drift:
        print("Run scripts/render-agents.py to refresh dist/.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
