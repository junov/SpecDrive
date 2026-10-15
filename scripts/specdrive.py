#!/usr/bin/env python3
"""SpecDrive helper for spec-as-source development in a git repository.

Projects have three top-level folders: ``spec/`` (Markdown source of truth), ``src/`` and
``test/`` (derived from the spec by an AI agent).

The sync BASELINE is the most recent commit reachable from HEAD whose message carries a
``Spec-Sync:`` trailer (created by ``accept``). Everything else is derived from git:

* spec delta   - requirement-level comparison of spec/ at the baseline vs. the working tree
                 (includes uncommitted and untracked edits)
* code drift   - src/ and test/ files changed since the baseline (edits made outside a sync)
* sync history - ``git log --grep "^Spec-Sync:"``
* retired IDs  - every requirement ID that ever appeared in spec/ history is never reused

Standard library only; Python 3.8+.

Usage:
    python specdrive.py status
    python specdrive.py delta [--json]
    python specdrive.py trace [--id AUTH-001] [--json]
    python specdrive.py next-id AUTH
    python specdrive.py check [--json]
    python specdrive.py accept -m "Add password reset" [--force]
    python specdrive.py log
    python specdrive.py base
    python specdrive.py init
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

# ------------------------------------------------------------------ configuration
ID_PATTERN = r"[A-Z][A-Z0-9]*-\d{3,}"
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
REQ_HEADING_RE = re.compile(rf"^(?P<id>{ID_PATTERN})\s*[:.\-\u2013\u2014]\s*(?P<title>.+)$")
SPEC_REF_RE = re.compile(rf"@spec\s+(?P<ids>{ID_PATTERN}(?:\s*,\s*{ID_PATTERN})*)")
REQ_PARENT_RE = re.compile(r"^\s*(functional\s+|non-functional\s+)?requirements\s*$", re.I)
FENCE_RE = re.compile(r"^\s*(```|~~~)")
TRAILER = "Spec-Sync"
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
SPEC_DIR, SRC_DIR, TEST_DIR = "spec", "src", "test"
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz", ".exe", ".dll", ".so",
              ".dylib", ".class", ".jar", ".pyc", ".woff", ".woff2", ".ttf", ".mp4", ".mp3", ".lock"}
MAX_SCAN_BYTES = 2 * 1024 * 1024
OUT_FENCE = "````"


class SpecDriveError(Exception):
    pass


# ------------------------------------------------------------------ git
class Git:
    def __init__(self, cwd: Path):
        self.root = cwd
        top = self.run("rev-parse", "--show-toplevel", allow_fail=True)
        if top is None:
            raise SpecDriveError(f"Not inside a git repository: {cwd}")
        self.root = Path(top.strip())

    def run(self, *args: str, allow_fail: bool = False) -> Optional[str]:
        try:
            proc = subprocess.run(["git", "-c", "core.quotepath=off", *args], cwd=self.root,
                                  capture_output=True, text=True, encoding="utf-8", errors="replace")
        except FileNotFoundError:
            raise SpecDriveError("git is not installed or not on PATH.")
        if proc.returncode != 0:
            if allow_fail:
                return None
            raise SpecDriveError(f"git {' '.join(args)} failed:\n{proc.stderr.strip()}")
        return proc.stdout

    def lines(self, *args: str) -> List[str]:
        return [l for l in (self.run(*args) or "").splitlines() if l]

    def has_commits(self) -> bool:
        return self.run("rev-parse", "--verify", "--quiet", "HEAD", allow_fail=True) is not None

    def baseline(self) -> Optional[str]:
        """Most recent sync commit reachable from HEAD, or None."""
        if not self.has_commits():
            return None
        out = self.lines("log", "-1", "--format=%H", "--extended-regexp", f"--grep=^{TRAILER}:", "HEAD")
        return out[0].strip() if out else None

    def commit_info(self, sha: Optional[str]) -> Optional[dict]:
        if not sha:
            return None
        short, date, subject = (self.run("log", "-1", "--format=%h%x09%cI%x09%s", sha) or "").rstrip("\n").split("\t", 2)
        return {"sha": sha, "short": short, "date": date, "subject": subject}

    def working_files(self, *folders: str) -> List[str]:
        """Tracked + untracked files (honoring .gitignore) that exist in the working tree."""
        files = set(self.lines("ls-files", "--cached", "--others", "--exclude-standard", "--", *folders))
        return sorted(f for f in files if (self.root / f).is_file())


# ------------------------------------------------------------------ spec model
@dataclass
class Section:
    file: str
    line: int
    level: int
    heading: str
    path: str
    parent: str
    req_id: Optional[str] = None
    title: str = ""
    body: List[str] = field(default_factory=list)
    lines: List[str] = field(default_factory=list)
    digest: str = ""
    key: str = ""

    @property
    def is_req(self) -> bool:
        return self.req_id is not None

    @property
    def location(self) -> str:
        return f"{self.file}:{self.line}"


def normalize(lines: Sequence[str]) -> List[str]:
    """Trim trailing whitespace, collapse blank runs, drop leading/trailing blanks."""
    out: List[str] = []
    prev_blank = True
    for raw in lines:
        t = raw.rstrip()
        if not t:
            if not prev_blank:
                out.append("")
            prev_blank = True
        else:
            out.append(t)
            prev_blank = False
    while out and not out[-1]:
        out.pop()
    return out


def parse_spec(text: str, rel: str) -> List[Section]:
    """Split Markdown into sections.

    A requirement section (heading ``ID: title``) absorbs its deeper sub-headings; any other
    section ends at the next heading of any level. Headings inside code fences are ignored.
    """
    sections: List[Section] = []
    stack: Dict[int, str] = {}
    in_fence = False
    cur = Section(rel, 1, 0, "", "(preamble)", "", title="(preamble)")
    for i, line in enumerate(text.splitlines()):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            cur.body.append(line)
            continue
        m = None if in_fence else HEADING_RE.match(line)
        if not m:
            cur.body.append(line)
            continue
        level, text_ = len(m.group(1)), m.group(2).strip()
        if cur.is_req and level > cur.level:
            cur.body.append(line)
            continue
        sections.append(cur)
        for k in [k for k in stack if k >= level]:
            del stack[k]
        parent = next((stack[p] for p in range(level - 1, 0, -1) if p in stack), "")
        stack[level] = text_
        path = " > ".join(stack[k] for k in sorted(stack))
        rm = REQ_HEADING_RE.match(text_)
        cur = Section(rel, i + 1, level, line, path, parent,
                      req_id=rm.group("id") if rm else None,
                      title=rm.group("title").strip() if rm else text_)
    sections.append(cur)

    result = []
    for s in sections:
        s.lines = normalize(([s.heading] if s.heading else []) + s.body)
        if not s.lines:
            continue
        s.digest = hashlib.sha256("\n".join(s.lines).encode("utf-8")).hexdigest()
        result.append(s)
    return result


@dataclass
class SpecModel:
    sections: "OrderedDict[str, Section]" = field(default_factory=OrderedDict)
    duplicates: List[dict] = field(default_factory=list)
    unidentified: List[dict] = field(default_factory=list)

    @property
    def requirements(self) -> List[Section]:
        return [s for s in self.sections.values() if s.is_req]


def build_model(sources: Dict[str, str]) -> SpecModel:
    model = SpecModel()
    for rel in sorted(sources):
        for s in parse_spec(sources[rel], rel):
            key = s.req_id if s.is_req else f"{rel}::{s.path}"
            if key in model.sections:
                if s.is_req:
                    model.duplicates.append({"id": s.req_id, "first": model.sections[key].location, "second": s.location})
                    continue
                n = 2
                while f"{key}#{n}" in model.sections:
                    n += 1
                key = f"{key}#{n}"
            s.key = key
            model.sections[key] = s
            if not s.is_req and s.level >= 2 and REQ_PARENT_RE.match(s.parent):
                model.unidentified.append({"heading": s.title, "location": s.location})
    return model


def working_spec(git: Git) -> Dict[str, str]:
    return {f: (git.root / f).read_text(encoding="utf-8", errors="replace")
            for f in git.working_files(SPEC_DIR) if f.endswith(".md")}


def commit_spec(git: Git, sha: Optional[str]) -> Dict[str, str]:
    if not sha:
        return {}
    files = [f for f in git.lines("ls-tree", "-r", "--name-only", sha, "--", SPEC_DIR) if f.endswith(".md")]
    return {f: git.run("show", f"{sha}:{f}") or "" for f in files}


# ------------------------------------------------------------------ delta / drift / trace
KIND_ORDER = {"ADDED": 0, "MODIFIED": 1, "REMOVED": 2, "MOVED": 3}


@dataclass
class Change:
    kind: str
    section: Section
    before: List[str]
    after: List[str]
    old_file: Optional[str] = None

    def to_dict(self) -> dict:
        s = self.section
        return {"kind": self.kind, "requirement": s.is_req, "id": s.req_id, "key": s.key, "title": s.title,
                "file": s.file, "line": s.line, "oldFile": self.old_file,
                "before": "\n".join(self.before), "after": "\n".join(self.after)}


@dataclass
class Delta:
    baseline: Optional[str]
    changes: List[Change]
    current: SpecModel


def compute_delta(git: Git) -> Delta:
    base = git.baseline()
    cur = build_model(working_spec(git))
    old = build_model(commit_spec(git, base))
    changes: List[Change] = []
    for k, c in cur.sections.items():
        b = old.sections.get(k)
        if b is None:
            changes.append(Change("ADDED", c, [], c.lines))
        elif b.digest != c.digest:
            changes.append(Change("MODIFIED", c, b.lines, c.lines, b.file))
        elif c.is_req and b.file != c.file:
            changes.append(Change("MOVED", c, b.lines, c.lines, b.file))
    for k, b in old.sections.items():
        if k not in cur.sections:
            changes.append(Change("REMOVED", b, b.lines, [], b.file))
    changes.sort(key=lambda ch: (not ch.section.is_req, KIND_ORDER[ch.kind], ch.section.file, ch.section.line))
    return Delta(base, changes, cur)


def code_drift(git: Git, base: Optional[str]) -> List[dict]:
    if not base:
        return []
    drift = []
    for l in git.lines("diff", "--name-status", base, "--", SRC_DIR, TEST_DIR):
        parts = l.split("\t")
        drift.append({"change": parts[0], "file": parts[-1]})
    for f in git.lines("ls-files", "--others", "--exclude-standard", "--", SRC_DIR, TEST_DIR):
        drift.append({"change": "??", "file": f})
    return drift


@dataclass
class Trace:
    requirements: "OrderedDict[str, dict]"
    orphans: List[dict]


def compute_trace(git: Git, model: Optional[SpecModel] = None) -> Trace:
    model = model or build_model(working_spec(git))
    reqs: "OrderedDict[str, dict]" = OrderedDict(
        (s.req_id, {"id": s.req_id, "title": s.title, "location": s.location, "tests": [], "src": []})
        for s in model.requirements)
    orphans = []
    for rel in git.working_files(SRC_DIR, TEST_DIR):
        path = git.root / rel
        if path.suffix.lower() in BINARY_EXT or path.stat().st_size > MAX_SCAN_BYTES:
            continue
        area = "tests" if rel.split("/", 1)[0] == TEST_DIR else "src"
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for m in SPEC_REF_RE.finditer(line):
                for rid in re.split(r"\s*,\s*", m.group("ids")):
                    loc = f"{rel}:{n}"
                    if rid in reqs:
                        reqs[rid][area].append(loc)
                    else:
                        orphans.append({"id": rid, "location": loc})
    return Trace(reqs, orphans)


def check_problems(delta: Delta, trace: Trace) -> List[str]:
    p = [f"duplicate ID {d['id']}: {d['first']}, {d['second']}" for d in delta.current.duplicates]
    p += [f"requirement without ID: '{u['heading']}' at {u['location']}" for u in delta.current.unidentified]
    p += [f"orphan @spec {o['id']} at {o['location']}" for o in trace.orphans]
    p += [f"untested requirement {r['id']} ({r['location']})" for r in trace.requirements.values() if not r["tests"]]
    return p


# ------------------------------------------------------------------ output helpers
def emit_json(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def baseline_line(info: Optional[dict]) -> str:
    if info:
        return f"Baseline: {info['short']} ({info['date']}) {info['subject']}"
    return "Baseline: none (no sync commit yet) - the whole spec counts as ADDED (initial generation)"


def full_context_diff(before: List[str], after: List[str]) -> List[str]:
    n = max(len(before), len(after))
    return [l for l in difflib.unified_diff(before, after, lineterm="", n=n)][2:]  # drop ---/+++ headers


def label(c: Change) -> str:
    s = c.section
    return f"{s.req_id}: {s.title}" if s.is_req else f"[context] {s.key}"


def counts(changes: List[Change], kind: str) -> int:
    return sum(1 for c in changes if c.kind == kind)


# ------------------------------------------------------------------ commands
def cmd_init(git: Git, args) -> int:
    for d in (SPEC_DIR, SRC_DIR, TEST_DIR):
        p = git.root / d
        print(("exists   " if p.exists() else "created  ") + d + "/")
        p.mkdir(exist_ok=True)
    print(baseline_line(git.commit_info(git.baseline())))
    return 0


def cmd_base(git: Git, args) -> int:
    info = git.commit_info(git.baseline())
    if args.json:
        emit_json(info)
    else:
        print(info["sha"] if info else EMPTY_TREE)
    return 0


def cmd_delta(git: Git, args) -> int:
    d = compute_delta(git)
    m = d.current
    if args.json:
        emit_json({"baseline": d.baseline, "duplicates": m.duplicates, "unidentified": m.unidentified,
                   "changes": [c.to_dict() for c in d.changes]})
        return 0
    req = [c for c in d.changes if c.section.is_req]
    ctx = [c for c in d.changes if not c.section.is_req]
    out = ["# Spec delta", "", baseline_line(git.commit_info(d.baseline)),
           f"Requirements: {counts(req, 'ADDED')} added, {counts(req, 'MODIFIED')} modified, "
           f"{counts(req, 'REMOVED')} removed, {counts(req, 'MOVED')} moved",
           f"Context sections: {counts(ctx, 'ADDED')} added, {counts(ctx, 'MODIFIED')} modified, "
           f"{counts(ctx, 'REMOVED')} removed", ""]
    if m.duplicates:
        out += ["## ERRORS - duplicate requirement IDs (fix before syncing)"]
        out += [f"- {x['id']}: {x['first']} and {x['second']}" for x in m.duplicates] + [""]
    if m.unidentified:
        out += ["## WARNINGS - requirement headings without IDs (assign with next-id)"]
        out += [f"- '{x['heading']}' at {x['location']}" for x in m.unidentified] + [""]
    if not d.changes:
        out.append("No spec changes since the last sync.")
    for c in d.changes:
        s = c.section
        where = {"MOVED": f"{c.old_file} -> {s.location}", "REMOVED": f"was {s.location}"}.get(c.kind, s.location)
        out += [f"## {c.kind} {label(c)}", f"_{where}_", ""]
        if c.kind == "ADDED":
            out += [OUT_FENCE + "markdown", *c.after, OUT_FENCE]
        elif c.kind == "REMOVED":
            out += [OUT_FENCE + "markdown", *c.before, OUT_FENCE]
        elif c.kind == "MODIFIED":
            out += [OUT_FENCE + "diff", *full_context_diff(c.before, c.after), OUT_FENCE]
        else:
            out.append("(content unchanged)")
        out.append("")
    print("\n".join(out))
    return 0


def cmd_status(git: Git, args) -> int:
    d = compute_delta(git)
    info = git.commit_info(d.baseline)
    drift = code_drift(git, d.baseline)
    req = [c for c in d.changes if c.section.is_req]
    ctx = [c for c in d.changes if not c.section.is_req]
    if args.json:
        emit_json({"baseline": info, "requirements": len(d.current.requirements),
                   "pendingRequirementChanges": [f"{c.kind} {c.section.req_id}" for c in req],
                   "pendingContextChanges": [f"{c.kind} {c.section.key}" for c in ctx],
                   "duplicates": len(d.current.duplicates), "unidentified": len(d.current.unidentified),
                   "codeDrift": drift})
        return 0
    out = ["# SpecDrive status", "", baseline_line(info), f"Requirements in spec: {len(d.current.requirements)}", ""]
    if not d.changes:
        out.append("Spec: in sync with baseline.")
    else:
        out.append(f"Spec: {len(d.changes)} pending change(s) - run 'delta' for details")
        out += [f"  {c.kind:<8} {c.section.req_id}  {c.section.title}" for c in req]
        out += [f"  {c.kind:<8} [context] {c.section.key}" for c in ctx]
    if d.current.duplicates:
        out.append(f"ERROR: {len(d.current.duplicates)} duplicate requirement ID(s)")
    if d.current.unidentified:
        out.append(f"WARNING: {len(d.current.unidentified)} requirement heading(s) without an ID")
    out.append("")
    if not info:
        out.append("Code drift: n/a (no baseline)")
    elif not drift:
        out.append("Code drift: none (src/ and test/ unchanged since baseline)")
    else:
        out.append(f"Code changed since baseline: {len(drift)} file(s) in src/ or test/")
        out.append("(expected while a sync is in progress; otherwise these are edits made outside a sync)")
        out += [f"  {x['change']:<4} {x['file']}" for x in drift]
    print("\n".join(out))
    return 0


def cmd_trace(git: Git, args) -> int:
    t = compute_trace(git)
    if args.id:
        r = t.requirements.get(args.id)
        if r is None:
            refs = [o["location"] for o in t.orphans if o["id"] == args.id]
            if args.json:
                emit_json({"id": args.id, "inSpec": False, "references": refs})
            else:
                print(f"{args.id} is not in the current spec (removed or never existed).")
                print(f"References still in code: {len(refs)}")
                print("\n".join(f"  {x}" for x in refs))
            return 0
        if args.json:
            emit_json(r)
            return 0
        out = [f"{r['id']}: {r['title']}", f"  spec:  {r['location']}"]
        out += [f"  test:  {x}" for x in r["tests"]] or ["  (no tests)"]
        out += [f"  src:   {x}" for x in r["src"]] or ["  (no tagged src)"]
        print("\n".join(out))
        return 0
    reqs = list(t.requirements.values())
    if args.json:
        emit_json({"requirements": reqs, "orphans": t.orphans})
        return 0
    out = ["# Traceability", "", "| ID | Title | Tests | Src |", "|----|-------|------:|----:|"]
    out += [f"| {r['id']} | {r['title']} | {len(r['tests'])} | {len(r['src'])} |" for r in reqs]
    untested = [r for r in reqs if not r["tests"]]
    unimpl = [r for r in reqs if not r["src"]]
    out += ["", f"Untested requirements: {len(untested)}"] + [f"  {r['id']}  ({r['location']})" for r in untested]
    out += [f"Requirements with no tagged src: {len(unimpl)}"] + [f"  {r['id']}" for r in unimpl]
    out += [f"Orphan @spec references (ID not in spec): {len(t.orphans)}"]
    out += [f"  {o['id']}  at {o['location']}" for o in t.orphans]
    print("\n".join(out))
    return 0


def cmd_check(git: Git, args) -> int:
    d = compute_delta(git)
    problems = check_problems(d, compute_trace(git, d.current))
    if args.json:
        emit_json({"ok": not problems, "pendingSpecChanges": len(d.changes), "problems": problems})
    else:
        if problems:
            print(f"CHECK FAILED - {len(problems)} problem(s):")
            print("\n".join(f"  - {p}" for p in problems))
        else:
            print("CHECK OK - every requirement is tested, no orphan references, IDs are valid.")
        if d.changes:
            print(f"Note: {len(d.changes)} spec change(s) since baseline not yet accepted.")
    return 1 if problems else 0


def cmd_accept(git: Git, args) -> int:
    """Commit spec/ src/ test/ (plus anything already staged) as a sync commit with trailers."""
    d = compute_delta(git)
    if d.current.duplicates:
        raise SpecDriveError("Refusing to accept: duplicate requirement IDs. Run 'delta'.")
    problems = check_problems(d, compute_trace(git, d.current))
    if problems and not args.force:
        raise SpecDriveError("Refusing to accept - traceability check failed (use --force to override):\n  - "
                             + "\n  - ".join(problems))
    git.run("add", "-A", "--", SPEC_DIR, SRC_DIR, TEST_DIR)
    staged = git.lines("diff", "--cached", "--name-only")
    if not staged and not d.changes and d.baseline:
        print("Nothing to accept: spec and code are already at the baseline.")
        return 0

    def ids(kind: str) -> str:
        return ", ".join(c.section.req_id for c in d.changes if c.section.is_req and c.kind == kind)

    msg = [f"spec-sync: {args.message}" if args.message else "spec-sync", ""]
    ctx = [f"- context {c.kind.lower()}: {c.section.key}" for c in d.changes if not c.section.is_req]
    if ctx:
        msg += ctx + [""]
    msg.append(f"{TRAILER}: v1")
    for kind in ("ADDED", "MODIFIED", "REMOVED", "MOVED"):
        if ids(kind):
            msg.append(f"Spec-{kind.capitalize()}: {ids(kind)}")
    fd, tmp = tempfile.mkstemp(prefix="specdrive-", suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(msg) + "\n")
        git.run("commit", "--allow-empty", "-F", tmp)
    finally:
        os.unlink(tmp)
    info = git.commit_info(git.baseline())
    print(f"Accepted. New baseline: {info['short']} {info['subject']} "
          f"({len(d.changes)} spec change(s), {len(staged)} file(s) committed).")
    return 0


def cmd_next_id(git: Git, args) -> int:
    prefix = args.prefix
    if not re.fullmatch(r"[A-Z][A-Z0-9]*", prefix):
        raise SpecDriveError("Prefix must be uppercase letters/digits, e.g. AUTH")
    rx = re.compile(rf"^[+\- ]?#{{1,6}}\s+{prefix}-(\d+)\b")
    lines: List[str] = []
    for text in working_spec(git).values():
        lines += text.splitlines()
    if git.has_commits():  # any ID that ever appeared in spec/ history (any branch) is retired
        lines += (git.run("log", "--all", "--format=", "-p", "--", SPEC_DIR) or "").splitlines()
    nums = [int(m.group(1)) for m in map(rx.match, lines) if m]
    print(f"{prefix}-{(max(nums) if nums else 0) + 1:03d}")
    return 0


def cmd_log(git: Git, args) -> int:
    if not git.has_commits():
        print("No commits yet.")
        return 0
    fmt = "--format=%h %cs %s%n%(trailers:key=Spec-Added,key=Spec-Modified,key=Spec-Removed,key=Spec-Moved)"
    out = git.lines("log", "--extended-regexp", f"--grep=^{TRAILER}:", fmt, "HEAD")
    print("\n".join(out) if out else "No sync commits yet.")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="specdrive", description=__doc__.split("\n\n")[0])
    ap.add_argument("-C", "--root", default=".", help="path inside the git repository (default: cwd)")
    sub = ap.add_subparsers(dest="command")
    for name, help_ in [("init", "create spec/ src/ test/ folders"),
                        ("status", "pending spec changes and code drift"),
                        ("base", "print the baseline commit SHA (empty tree if none)"),
                        ("delta", "requirement-level spec delta since the baseline"),
                        ("trace", "traceability matrix from @spec tags"),
                        ("check", "fail (exit 1) on untested/orphan/duplicate/unidentified requirements"),
                        ("accept", "commit the sync and advance the baseline"),
                        ("next-id", "allocate the next unused requirement ID for a prefix"),
                        ("log", "list sync commits")]:
        p = sub.add_parser(name, help=help_)
        p.add_argument("--json", action="store_true", help="machine-readable output")
        if name == "trace":
            p.add_argument("--id", help="show locations for a single requirement ID")
        if name == "accept":
            p.add_argument("-m", "--message", default="", help="short summary for the commit subject")
            p.add_argument("--force", action="store_true", help="accept even if 'check' fails")
        if name == "next-id":
            p.add_argument("prefix", help="uppercase ID prefix, e.g. AUTH")
    args = ap.parse_args(argv)
    if not args.command:
        args.command, args.json = "status", False
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    handlers = {"init": cmd_init, "status": cmd_status, "base": cmd_base, "delta": cmd_delta,
                "trace": cmd_trace, "check": cmd_check, "accept": cmd_accept, "next-id": cmd_next_id,
                "log": cmd_log}
    try:
        return handlers[args.command](Git(Path(args.root).resolve()), args)
    except SpecDriveError as e:
        print(f"specdrive: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
