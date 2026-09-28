"""The trainee's working copy: a private, patchable copy of the lab specimen.

Fixes are overlays (files to write, plus an optional ``DELETE`` manifest) and
are applied to the working copy only, so a wrong treatment can be measured
and then reverted to the chapter's original code.
"""
from __future__ import annotations

import difflib
import os
import shutil

from app.lab.chapters import BASE_DIR, Chapter, fix_dir


def _chapter_paths(root: str, chapter: Chapter) -> list[str]:
    """All files currently under the chapter's owned paths (relative)."""
    out: list[str] = []
    for rel in chapter.files:
        path = os.path.join(root, rel)
        if os.path.isdir(path):
            for dp, dn, fn in os.walk(path):
                dn[:] = sorted(d for d in dn if d != "__pycache__")
                out += [os.path.relpath(os.path.join(dp, f), root) for f in sorted(fn) if f.endswith(".py")]
        elif os.path.exists(path):
            out.append(rel)
    return sorted(out)


class Trainee:
    def __init__(self, root: str) -> None:
        self.root = root

    def reset(self) -> None:
        if os.path.isdir(self.root):
            shutil.rmtree(self.root)
        shutil.copytree(BASE_DIR, self.root, ignore=shutil.ignore_patterns("__pycache__"))

    def ensure(self) -> None:
        if not os.path.isdir(self.root):
            self.reset()

    def read(self, rel: str) -> str:
        with open(os.path.join(self.root, rel), encoding="utf-8") as fh:
            return fh.read()

    def overlay(self, chapter: Chapter, key: str) -> tuple[dict[str, str], list[str]]:
        """Files the fix writes (rel -> content) and files it deletes."""
        src = fix_dir(chapter, key)
        writes: dict[str, str] = {}
        deletes: list[str] = []
        for dp, _, fn in os.walk(src):
            for f in sorted(fn):
                full = os.path.join(dp, f)
                rel = os.path.relpath(full, src)
                if rel == "DELETE":
                    with open(full) as fh:
                        deletes = [line.strip() for line in fh if line.strip()]
                    continue
                with open(full, encoding="utf-8") as fh:
                    writes[rel] = fh.read()
        return writes, deletes

    def diff(self, chapter: Chapter, key: str) -> str:
        """Unified diff of the chapter's original code against the fix."""
        writes, deletes = self.overlay(chapter, key)
        chunks: list[str] = []
        for rel in sorted(set(writes) | set(deletes)):
            base_path = os.path.join(BASE_DIR, rel)
            old = open(base_path, encoding="utf-8").read() if os.path.exists(base_path) else ""
            new = "" if rel in deletes else writes.get(rel, old)
            chunks.extend(difflib.unified_diff(
                old.splitlines(keepends=True), new.splitlines(keepends=True),
                fromfile=f"a/{rel}" if old else "/dev/null", tofile=f"b/{rel}" if new else "/dev/null", n=2,
            ))
        return "".join(chunks)

    def revert(self, chapter: Chapter) -> None:
        """Restore the chapter's files to the specimen's original code."""
        for rel in _chapter_paths(self.root, chapter):
            if not os.path.exists(os.path.join(BASE_DIR, rel)):
                os.remove(os.path.join(self.root, rel))
        for rel in _chapter_paths(BASE_DIR, chapter):
            dst = os.path.join(self.root, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(BASE_DIR, rel), dst)

    def apply(self, chapter: Chapter, key: str) -> None:
        self.revert(chapter)
        writes, deletes = self.overlay(chapter, key)
        for rel, content in writes.items():
            dst = os.path.join(self.root, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "w", encoding="utf-8") as fh:
                fh.write(content)
        for rel in deletes:
            path = os.path.join(self.root, rel)
            if os.path.exists(path):
                os.remove(path)
