# services/agents/security_scan.py
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Mapping


MAX_STDIO_CHARS = int(os.getenv("VELU_SECURITY_MAX_STDIO_CHARS", "12000") or "12000")


def _workspace_from_payload(payload: Mapping[str, Any]) -> Path:
    velu = payload.get("_velu")
    if isinstance(velu, dict):
        ws = velu.get("workspace")
        if isinstance(ws, str) and ws.strip():
            return Path(ws.strip())
    # fallback: worker isolates cwd to workspace in your worker_entry
    return Path.cwd()


def _trim(s: str, limit: int = MAX_STDIO_CHARS) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    if len(s) <= limit:
        return s
    return s[:limit] + "\n…(truncated)…"


def _run(cmd: list[str], cwd: Path, timeout_sec: int = 120) -> dict[str, Any]:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        return {
            "ok": True,
            "rc": int(p.returncode),
            "stdout": _trim(p.stdout or ""),
            "stderr": _trim(p.stderr or ""),
        }
    except FileNotFoundError:
        return {"ok": False, "rc": None, "error": "not_found"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "rc": None, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "rc": None, "error": f"{type(e).__name__}: {e}"}


def _json_load_maybe(text: str) -> Any:
    s = (text or "").strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def _summarize_pip_audit(run_res: Dict[str, Any]) -> Dict[str, Any]:
    """
    pip-audit -f json usually returns a JSON list.
    rc may be non-zero when vulnerabilities exist.
    """
    out = {"tool": "pip-audit", "applicable": True, "findings": 0, "notes": []}
    if run_res.get("status") == "skip":
        out["applicable"] = False
        return out
    if not run_res.get("ok"):
        out["notes"].append(run_res.get("error") or "run_failed")
        return out

    data = _json_load_maybe(run_res.get("stdout") or "")
    if isinstance(data, list):
        out["findings"] = len(data)
    else:
        # fallback: unknown format
        out["notes"].append("non_json_output")
    return out


def _summarize_npm_audit(run_res: Dict[str, Any]) -> Dict[str, Any]:
    """
    npm audit --json output format varies by npm version.
    We try multiple shapes.
    """
    out = {"tool": "npm-audit", "applicable": True, "findings": 0, "notes": []}
    if run_res.get("status") == "skip":
        out["applicable"] = False
        return out
    if not run_res.get("ok"):
        out["notes"].append(run_res.get("error") or "run_failed")
        return out

    data = _json_load_maybe(run_res.get("stdout") or "")
    if isinstance(data, dict):
        # npm v8+ often: {"metadata": {"vulnerabilities": {...}}}
        meta = data.get("metadata")
        if isinstance(meta, dict):
            vul = meta.get("vulnerabilities")
            if isinstance(vul, dict):
                # counts by severity: info/low/moderate/high/critical
                out["findings"] = int(sum(int(v) for v in vul.values() if isinstance(v, (int, float))))
                return out

        # older: {"advisories": {...}}
        adv = data.get("advisories")
        if isinstance(adv, dict):
            out["findings"] = len(adv)
            return out

    out["notes"].append("non_json_or_unknown_shape")
    return out


def _summarize_semgrep(run_res: Dict[str, Any]) -> Dict[str, Any]:
    """
    semgrep --json typically includes {"results": [...]}
    rc semantics depend on config; use results count.
    """
    out = {"tool": "semgrep", "applicable": True, "findings": 0, "notes": []}
    if run_res.get("status") == "skip":
        out["applicable"] = False
        return out
    if not run_res.get("ok"):
        out["notes"].append(run_res.get("error") or "run_failed")
        return out

    data = _json_load_maybe(run_res.get("stdout") or "")
    if isinstance(data, dict):
        results = data.get("results")
        if isinstance(results, list):
            out["findings"] = len(results)
            return out
    out["notes"].append("non_json_or_unknown_shape")
    return out


def _summarize_gitleaks(run_res: Dict[str, Any]) -> Dict[str, Any]:
    """
    gitleaks detect --report-format json sometimes writes to stdout, sometimes to report file.
    We run it without a report file, so stdout is best-effort.
    """
    out = {"tool": "gitleaks", "applicable": True, "findings": 0, "notes": []}
    if run_res.get("status") == "skip":
        out["applicable"] = False
        return out
    if not run_res.get("ok"):
        out["notes"].append(run_res.get("error") or "run_failed")
        return out

    data = _json_load_maybe(run_res.get("stdout") or "")
    if isinstance(data, list):
        out["findings"] = len(data)
        return out

    # Sometimes gitleaks writes human output; if rc != 0 treat as suspicious
    if isinstance(run_res.get("rc"), int) and run_res["rc"] != 0:
        out["notes"].append("non_json_output_nonzero_rc")
    else:
        out["notes"].append("non_json_output")
    return out


def _is_true(env_name: str) -> bool:
    v = (os.getenv(env_name) or "").strip().lower()
    return v in {"1", "true", "yes", "on"}


def _detect_stack(ws: Path) -> Dict[str, bool]:
    has_py = (ws / "pyproject.toml").exists() or (ws / "requirements.txt").exists()
    # also look for generated backend deps inside workspace
    if not has_py:
        has_py = (ws / "generated" / "services" / "api").exists()
    has_node = (ws / "package.json").exists() or (ws / "generated" / "web" / "package.json").exists()
    return {"has_py": has_py, "has_node": has_node}


def _render_report_md(
    ws: Path,
    summaries: Dict[str, Any],
    raw_tools: Dict[str, Any],
    needs_review: bool,
) -> str:
    lines: list[str] = []
    lines.append("# Security Report")
    lines.append("")
    lines.append(f"- Workspace: `{ws}`")
    lines.append(f"- Needs review: `{needs_review}`")
    lines.append(f"- Generated at: `{int(time.time())}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")

    total_findings = 0
    for name, s in summaries.items():
        if isinstance(s, dict) and isinstance(s.get("findings"), int):
            total_findings += int(s["findings"])

    lines.append(f"- Total findings (best-effort): **{total_findings}**")
    lines.append("")
    lines.append("| Tool | Applicable | Findings | Notes |")
    lines.append("|---|---:|---:|---|")

    def _row(tool: str, s: Dict[str, Any]) -> str:
        applicable = "yes" if s.get("applicable") else "no"
        findings = s.get("findings", 0)
        notes = ", ".join([str(x) for x in (s.get("notes") or [])]) or "-"
        return f"| {tool} | {applicable} | {findings} | {notes} |"

    for tool in ("pip_audit", "npm_audit", "semgrep", "gitleaks"):
        s = summaries.get(tool) if isinstance(summaries.get(tool), dict) else {}
        label = tool.replace("_", "-")
        lines.append(_row(label, s))

    lines.append("")
    lines.append("## Tool Results (snippets)")
    lines.append("")
    for name, r in raw_tools.items():
        lines.append(f"### {name}")
        if isinstance(r, dict) and r.get("status") == "skip":
            lines.append("- status: skip (tool missing or not applicable)")
            lines.append("")
            continue

        if not isinstance(r, dict):
            lines.append("- status: unknown")
            lines.append("")
            continue

        lines.append(f"- ok: {r.get('ok')}")
        lines.append(f"- rc: {r.get('rc')}")
        if r.get("error"):
            lines.append(f"- error: {r.get('error')}")
        lines.append("")

        stderr = (r.get("stderr") or "").strip()
        stdout = (r.get("stdout") or "").strip()

        if stderr:
            lines.append("**stderr (snippet):**")
            lines.append("```")
            lines.append(stderr)
            lines.append("```")
            lines.append("")

        # keep stdout less prominent (often huge)
        if stdout:
            lines.append("**stdout (snippet):**")
            lines.append("```")
            lines.append(stdout)
            lines.append("```")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def handle(task_or_payload: Any, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if isinstance(task_or_payload, dict) and payload is None:
        payload = task_or_payload
    payload = dict(payload or {})

    ws = _workspace_from_payload(payload)
    ws.mkdir(parents=True, exist_ok=True)

    artifacts_dir = ws / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    stack = _detect_stack(ws)

    timeout_sec = int((os.getenv("VELU_SECURITY_TIMEOUT_SEC", "120").strip() or "120"))

    raw_tools: dict[str, Any] = {}

    # pip-audit (python deps)
    if stack["has_py"] and shutil.which("pip-audit"):
        raw_tools["pip_audit"] = _run(["pip-audit", "-f", "json"], cwd=ws, timeout_sec=timeout_sec)
    else:
        raw_tools["pip_audit"] = {"ok": True, "rc": 0, "status": "skip"}

    # npm audit (node deps)
    if stack["has_node"] and shutil.which("npm"):
        # Note: npm audit may require node_modules; still useful.
        raw_tools["npm_audit"] = _run(["npm", "audit", "--json"], cwd=ws, timeout_sec=timeout_sec)
    else:
        raw_tools["npm_audit"] = {"ok": True, "rc": 0, "status": "skip"}

    # semgrep baseline (optional)
    if shutil.which("semgrep"):
        raw_tools["semgrep"] = _run(
            ["semgrep", "--config", "p/ci", "--json", "."],
            cwd=ws,
            timeout_sec=timeout_sec,
        )
    else:
        raw_tools["semgrep"] = {"ok": True, "rc": 0, "status": "skip"}

    # gitleaks (optional)
    if shutil.which("gitleaks"):
        raw_tools["gitleaks"] = _run(
            ["gitleaks", "detect", "--no-git", "--report-format", "json"],
            cwd=ws,
            timeout_sec=timeout_sec,
        )
    else:
        raw_tools["gitleaks"] = {"ok": True, "rc": 0, "status": "skip"}

    # Summaries (count findings robustly)
    summaries: Dict[str, Any] = {
        "pip_audit": _summarize_pip_audit(raw_tools["pip_audit"]),
        "npm_audit": _summarize_npm_audit(raw_tools["npm_audit"]),
        "semgrep": _summarize_semgrep(raw_tools["semgrep"]),
        "gitleaks": _summarize_gitleaks(raw_tools["gitleaks"]),
    }

    # Gate policy:
    # - default: needs_review if any tool reports findings > 0
    # - allow overriding to be stricter: VELU_SECURITY_STRICT=1 also flags if any tool run failed
    needs_review = False

    any_findings = False
    any_failed = False
    for t, s in summaries.items():
        if isinstance(s, dict) and isinstance(s.get("findings"), int) and s.get("findings", 0) > 0:
            any_findings = True

    for t, r in raw_tools.items():
        if isinstance(r, dict) and r.get("status") != "skip":
            # run failed (tool missing handled by skip)
            if r.get("ok") is False:
                any_failed = True

    if any_findings:
        needs_review = True
    if _is_true("VELU_SECURITY_STRICT") and any_failed:
        needs_review = True

    # Render report
    report_md = _render_report_md(ws, summaries, raw_tools, needs_review)

    # Write report into workspace artifacts folder (packager-friendly)
    report_path = artifacts_dir / "SECURITY_REPORT.md"
    try:
        report_path.write_text(report_md, encoding="utf-8")
    except Exception:
        # Don't fail pipeline because report writing failed.
        pass

    return {
        "ok": True,
        "agent": "security_scan",
        "workspace": str(ws),
        "artifacts_dir": str(artifacts_dir),
        "report_path": str(report_path),
        # IMPORTANT: packager can embed this directly
        "security_report": report_md,
        "needs_review": needs_review,
        "summaries": summaries,
        "tools": raw_tools,
    }
