from __future__ import annotations

from typing import Any, Dict, List


def _as_tables(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = payload.get("tables") or []
    if isinstance(raw, list):
        return [t for t in raw if isinstance(t, dict)]
    return []


def _norm_name(value: Any) -> str:
    return str(value or "").strip()


def _existing_index_keys(table: Dict[str, Any]) -> List[List[str]]:
    out: List[List[str]] = []
    for idx in table.get("indexes") or []:
        if not isinstance(idx, dict):
            continue
        cols = idx.get("columns") or []
        if isinstance(cols, list):
            names = [c for c in (str(x).strip() for x in cols) if c]
            if names:
                out.append(names)
    return out


def _has_index_on(table: Dict[str, Any], col_name: str) -> bool:
    col_name = col_name.strip()
    if not col_name:
        return False
    for cols in _existing_index_keys(table):
        if len(cols) == 1 and cols[0] == col_name:
            return True
        if col_name in cols:
            return True
    return False


def _analyze_column(table: Dict[str, Any], col: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    tname = _norm_name(table.get("name"))
    cname = _norm_name(col.get("name"))
    ctype = _norm_name(col.get("type")).lower()

    existing_idx = _has_index_on(table, cname)

    if cname.endswith("_id"):
        if not existing_idx:
            issues.append(
                {
                    "table": tname,
                    "column": cname,
                    "severity": "medium",
                    "kind": "missing_index",
                    "message": f"Column {cname} on {tname} looks like a foreign key; consider adding an index.",
                    "suggested_index": [cname],
                }
            )

    if cname in {"created_at", "updated_at"} or cname.endswith("_at"):
        if ctype in {"timestamp", "timestamptz", "datetime"} and not existing_idx:
            issues.append(
                {
                    "table": tname,
                    "column": cname,
                    "severity": "low",
                    "kind": "missing_index",
                    "message": f"Timestamp column {cname} on {tname} may benefit from an index for range queries.",
                    "suggested_index": [cname],
                }
            )

    if cname in {"email", "username"}:
        unique = bool(col.get("unique"))
        if not unique:
            issues.append(
                {
                    "table": tname,
                    "column": cname,
                    "severity": "medium",
                    "kind": "missing_uniqueness",
                    "message": f"Column {cname} on {tname} looks like a login identifier; consider adding a unique constraint.",
                }
            )

    if ctype in {"text", "varchar", "string"}:
        max_len = col.get("max_length")
        if max_len is None:
            issues.append(
                {
                    "table": tname,
                    "column": cname,
                    "severity": "low",
                    "kind": "missing_length",
                    "message": f"Text column {cname} on {tname} has no max_length; consider bounding it for performance.",
                }
            )

    return issues


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    tables = _as_tables(payload)
    table_results: List[Dict[str, Any]] = []
    all_issues: List[Dict[str, Any]] = []

    for table in tables:
        tname = _norm_name(table.get("name"))
        cols = table.get("columns") or []
        if not isinstance(cols, list):
            cols = []
        t_issues: List[Dict[str, Any]] = []
        suggested_indexes: List[List[str]] = []

        for col in cols:
            if not isinstance(col, dict):
                continue
            col_issues = _analyze_column(table, col)
            t_issues.extend(col_issues)
            for issue in col_issues:
                idx = issue.get("suggested_index")
                if isinstance(idx, list) and idx:
                    names = [c for c in (str(x).strip() for x in idx) if c]
                    if names and names not in suggested_indexes:
                        suggested_indexes.append(names)

        all_issues.extend(t_issues)
        table_results.append(
            {
                "name": tname,
                "issues": t_issues,
                "suggested_indexes": suggested_indexes,
            }
        )

    summary = {
        "total_tables": len(table_results),
        "total_issues": len(all_issues),
    }

    return {
        "ok": True,
        "agent": "db_schema_optimizer",
        "tables": table_results,
        "issues": all_issues,
        "summary": summary,
    }
