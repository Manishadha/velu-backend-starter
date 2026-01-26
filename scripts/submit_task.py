#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, Tuple


def _get_json(url: str, headers: Dict[str, str] | None = None) -> Dict[str, Any]:
    req = urllib.request.Request(url, method="GET", headers=headers or {})
    with urllib.request.urlopen(req) as r:
        raw = r.read().decode("utf-8")
    return json.loads(raw) if raw.strip() else {}


def _post_json(url: str, payload: dict, headers: Dict[str, str] | None = None) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    merged = {"Content-Type": "application/json"}
    if headers:
        merged.update(headers)

    req = urllib.request.Request(url, data=data, headers=merged, method="POST")
    with urllib.request.urlopen(req) as r:
        raw = r.read().decode("utf-8")
    return json.loads(raw) if raw.strip() else {}


def _discover_submit_endpoint(base_url: str, headers: Dict[str, str]) -> str:
    """
    Your openapi has POST /tasks, so we try to find the best "submit task" endpoint.
    """
    openapi_url = base_url.rstrip("/") + "/openapi.json"
    doc = _get_json(openapi_url, headers=headers)
    paths = doc.get("paths") or {}
    if not isinstance(paths, dict):
        raise SystemExit("openapi.json has no 'paths' map")

    candidates: list[Tuple[int, str]] = []
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        post = methods.get("post")
        if not isinstance(post, dict):
            continue

        summary = str(post.get("summary") or "").lower()
        op_id = str(post.get("operationId") or "").lower()
        hay = f"{path.lower()} {summary} {op_id}"

        score = 0
        # Prefer exact task submit endpoint
        if path == "/tasks":
            score += 500
        if "task" in hay:
            score += 100
        if "submit" in hay:
            score += 50
        if "job" in hay or "queue" in hay or "pipeline" in hay:
            score += 10

        if score > 0:
            candidates.append((score, path))

    if not candidates:
        raise SystemExit(
            "Could not auto-discover submit endpoint from openapi.json. "
            "Pass --endpoint explicitly."
        )

    candidates.sort(reverse=True)
    return candidates[0][1]


def _build_headers(token: str, api_key: str) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    t = (token or "").strip()
    k = (api_key or "").strip()
    if t:
        headers["Authorization"] = f"Bearer {t}"
    if k:
        headers["X-API-Key"] = k  #  correct header
    return headers


def main() -> int:
    ap = argparse.ArgumentParser(description="Submit a Velu task to the local API.")
    ap.add_argument(
        "--base-url",
        default=os.getenv("VELU_API_URL", "http://127.0.0.1:8010"),
        help="Base URL for Velu API (default: $VELU_API_URL or http://127.0.0.1:8010)",
    )
    ap.add_argument(
        "--endpoint",
        default=os.getenv("VELU_SUBMIT_ENDPOINT", ""),
        help="Submit endpoint path. If empty, auto-detect from /openapi.json",
    )
    ap.add_argument(
        "--json",
        dest="json_path",
        default=None,
        help="Path to JSON payload file. If omitted, reads JSON from stdin.",
    )
    ap.add_argument(
        "--token",
        default=os.getenv("VELU_TOKEN", ""),
        help="Bearer token for Velu API (default: $VELU_TOKEN)",
    )
    ap.add_argument(
        "--api-key",
        default=os.getenv("VELU_API_KEY", ""),
        help="API key for Velu API (sent as X-API-Key) (default: $VELU_API_KEY)",
    )
    args = ap.parse_args()

    # Load payload
    if args.json_path:
        payload_raw = open(args.json_path, "r", encoding="utf-8").read()
    else:
        payload_raw = sys.stdin.read()

    if not payload_raw.strip():
        print("Empty JSON payload (provide --json file or pipe JSON on stdin).", file=sys.stderr)
        return 2

    payload = json.loads(payload_raw)

    # Normalize payload into TaskIn: {"task": "...", "payload": {...}}
    if isinstance(payload, dict) and "task" not in payload:
        payload = {"task": "plan", "payload": payload}

    if isinstance(payload, dict) and isinstance(payload.get("task"), dict):
        payload = {"task": "plan", "payload": payload["task"]}

    headers = _build_headers(args.token, args.api_key)

    endpoint = args.endpoint.strip()
    if not endpoint:
        endpoint = _discover_submit_endpoint(args.base_url, headers=headers)

    url = args.base_url.rstrip("/") + endpoint

    try:
        res = _post_json(url, payload, headers=headers)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        print(f"HTTP {e.code} for {url}", file=sys.stderr)
        if body.strip():
            print(body, file=sys.stderr)
        return 1

    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
