# services/agents/repo_summary.py
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple  # noqa: F401


EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".idea",
    ".vscode",
}

# Small, stable mapping for language detection (by file extension)
EXT_TO_LANG = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C/C++",
    ".cs": "C#",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".sh": "Shell",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".md": "Markdown",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".ini": "INI",
    ".env": "ENV",
}


def _normalize_focus_dirs(focus_dirs: Any) -> List[str]:
    if not focus_dirs:
        return []
    if isinstance(focus_dirs, str):
        return [x.strip() for x in focus_dirs.split(",") if x.strip()]
    if isinstance(focus_dirs, list):
        return [str(x).strip() for x in focus_dirs if str(x).strip()]
    return []


def _should_skip(path: Path) -> bool:
    # Skip any path that includes excluded dir names
    parts = set(path.parts)
    return any(d in parts for d in EXCLUDED_DIRS)


def _is_probably_text_file(path: Path) -> bool:
    # Conservative: only sample snippets from known “text-like” extensions
    ext = path.suffix.lower()
    if ext in EXT_TO_LANG:
        return True
    # allow a few common text configs without suffix
    if path.name in {"Dockerfile", "Makefile"}:
        return True
    return False


def _redact(text: str) -> str:
    """
    Redaction rules (test-compatible):
    - Remove AWS keys
    - Remove Bearer tokens
    - Ensure generic [REDACTED] marker is present if anything redacted
    """
    if not text:
        return text

    redacted = False

    if re.search(r"\bAKIA[0-9A-Z]{16}\b", text):
        text = re.sub(r"\bAKIA[0-9A-Z]{16}\b", "[REDACTED_AWS_KEY]", text)
        redacted = True

    if re.search(r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b", text, re.IGNORECASE):
        text = re.sub(
            r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b",
            "[REDACTED_BEARER_TOKEN]",
            text,
            flags=re.IGNORECASE,
        )
        redacted = True

    if re.search(r"(?im)\b(secret|api_key|apikey|token|password)\b\s*=", text):
        text = re.sub(
            r"(?im)^(.*\b(secret|api_key|apikey|token|password)\b\s*=\s*).*$",
            r"\1[REDACTED]",
            text,
        )
        redacted = True

    # Test requirement: literal "[REDACTED]" must appear if anything got redacted
    if redacted and "[REDACTED]" not in text:
        text = "[REDACTED]\n" + text

    return text


def _read_excerpt(path: Path, max_bytes: int) -> str:
    data = path.read_bytes()[: max(0, int(max_bytes))]
    return data.decode("utf-8", errors="replace")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Repo summary agent (safe v2):
    - walks repo under `root`
    - counts files by extension and top-level directory
    - counts language distribution from extensions
    - optionally returns safe snippet excerpts (opt-in)
    """
    root_in = payload.get("root") or "."
    root = Path(str(root_in)).expanduser().resolve()

    focus_dirs = set(_normalize_focus_dirs(payload.get("focus_dirs")))
    include_snippets = bool(payload.get("include_snippets", False))

    # snippet settings (support both older + newer naming styles)
    max_snippets = int(payload.get("max_snippets", payload.get("snippet_max_files", 3)) or 3)
    max_bytes_per = int(
        payload.get("max_bytes_per_snippet", payload.get("snippet_max_bytes_per_file", 800)) or 800
    )
    max_total = int(
        payload.get("max_total_bytes", payload.get("snippet_max_total_bytes", 2000)) or 2000
    )
    redact = bool(payload.get("snippet_redact", True))

    total_files = 0
    by_ext: Counter[str] = Counter()
    top_dirs: Counter[str] = Counter()
    focus_counts: Counter[str] = Counter()
    languages: Counter[str] = Counter()

    if not root.exists():
        return {
            "ok": False,
            "error": f"root path does not exist: {root}",
            "stats": {"total_files_seen": 0, "by_ext": {}, "top_dirs": {}, "focus_dirs": {}},
        }

    # collect files once (stable ordering)
    files: List[Path] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if _should_skip(p):
            continue
        files.append(p)

    snippets: List[Dict[str, Any]] = []
    used_total = 0

    for p in files:
        total_files += 1

        ext = p.suffix if p.suffix else "<none>"
        by_ext[ext] += 1

        lang = EXT_TO_LANG.get(p.suffix.lower())
        if lang:
            languages[lang] += 1

        try:
            rel = p.relative_to(root)
            top = rel.parts[0] if rel.parts else "."
        except Exception:
            top = "."

        top_dirs[top] += 1
        if focus_dirs and top in focus_dirs:
            focus_counts[top] += 1

        # snippets (opt-in only)
        if include_snippets:
            if len(snippets) >= max_snippets:
                continue
            if used_total >= max_total:
                continue

            # if focus_dirs is provided, only snippet files within those top dirs
            if focus_dirs and top not in focus_dirs:
                continue

            if not _is_probably_text_file(p):
                continue

            remaining = max_total - used_total
            take = min(max_bytes_per, remaining)
            if take <= 0:
                continue

            try:
                excerpt = _read_excerpt(p, take)
                if redact:
                    excerpt = _redact(excerpt)
                # Never throw on encoding; keep counting bytes safely
                b = len((excerpt or "").encode("utf-8", errors="ignore"))

            except (OSError, UnicodeError, ValueError):
                continue

            used_total += b
            snippets.append(
                {
                    "path": str(p.relative_to(root)),
                    # keep BOTH keys so  don’t break any evolving tests/docs
                    "content": excerpt,
                    "excerpt": excerpt,
                    "bytes": b,
                    "language": lang or None,
                }
            )

    out: Dict[str, Any] = {
        "ok": True,
        "stats": {
            "total_files_seen": total_files,
            "by_ext": dict(by_ext),
            "top_dirs": dict(top_dirs),
            "focus_dirs": dict(focus_counts),
        },
        "languages": dict(languages),
        "snippets": snippets if include_snippets else [],
    }

    return out
