#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import time
from typing import Any

import requests


def submit_autodev(
    api: str,
    idea: str,
    module: str,
    message: str,
    tests: bool = True,
    api_key: str | None = None,
) -> int:
    """Submit an autodev job and return the job_id."""
    payload = {
        "task": "autodev",
        "payload": {
            "idea": idea,
            "module": module,
            "tests": tests,
            "message": message,
        },
    }

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    r = requests.post(f"{api}/tasks", json=payload, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise SystemExit(f"API returned not-ok: {data}")
    return int(data["job_id"])


def poll_result(api: str, job_id: int, api_key: str | None = None) -> dict[str, Any]:
    """Poll /results/{job_id} until status is done/error."""
    headers: dict[str, str] = {}
    if api_key:
        headers["X-API-Key"] = api_key

    while True:
        r = requests.get(f"{api}/results/{job_id}?expand=1", headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data.get("ok"):
            raise SystemExit(f"/results returned not-ok: {data}")
        item = data["item"]
        status = str(item.get("status") or "").lower()
        if status in {"done", "error"}:
            return item
        time.sleep(0.5)


def pretty_print_autodev(item: dict[str, Any]) -> None:
    result = item.get("result") or {}
    print(f"\n=== autodev job {item.get('id')} ({item.get('status')}) ===")
    print("ok:", result.get("ok"))
    print("agent:", result.get("agent"))

    idea = result.get("idea")
    module = result.get("module")
    if idea or module:
        print(f"idea   : {idea}")
        print(f"module : {module}")

    subjobs = (result.get("subjobs_detail") or {}) if isinstance(result, dict) else {}
    if not subjobs:
        print("\n(no subjobs_detail; try ?expand=1 in /results)")
        return

    print("\n--- subjobs ---")
    for name in ["pipeline", "lint", "gitcommit"]:
        sj = subjobs.get(name)
        if not sj:
            continue
        s_status = sj.get("status")
        print(f"* {name}: id={sj.get('id')} status={s_status}")

        s_res = sj.get("result") or {}
        if name == "pipeline":
            print("  plan ok:", s_res.get("ok"))
            print("  plan   :", s_res.get("plan"))
        elif name == "lint":
            print("  lint ok:", s_res.get("ok"))
        elif name == "gitcommit":
            print("  did_commit:", s_res.get("did_commit"))
            print("  subject   :", s_res.get("subject"))
            if s_res.get("files"):
                print("  files     :", ", ".join(s_res["files"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="autodev helper CLI for velu backend")
    parser.add_argument(
        "--api",
        default=os.getenv("VELU_API", "http://127.0.0.1:8000").rstrip("/"),
        help="Base URL for velu API (default: %(default)s or $VELU_API)",
    )
    parser.add_argument(
        "--api-key",
        default=(
            os.getenv("API_KEYS", "").split(",")[0].split(":", 1)[0]
            if os.getenv("API_KEYS")
            else None
        ),  # best-effort
        help="API key to send as X-API-Key (optional)",
    )
    parser.add_argument(
        "--module", default="hello_mod", help="Target module (default: %(default)s)"
    )
    parser.add_argument("--no-tests", action="store_true", help="Disable tests in pipeline payload")
    parser.add_argument(
        "--message",
        required=True,
        help="Git commit message, e.g. 'feat: add Dutch greeting support'",
    )
    parser.add_argument(
        "idea",
        help="High-level idea, e.g. 'Add Dutch support to hello_mod.greet with tests'",
    )

    args = parser.parse_args()
    tests = not args.no_tests

    print(f"API     : {args.api}")
    print(f"module  : {args.module}")
    print(f"idea    : {args.idea}")
    print(f"message : {args.message}")
    print(f"tests   : {tests}")
    print("Submitting autodev job...")

    job_id = submit_autodev(
        api=args.api,
        idea=args.idea,
        module=args.module,
        message=args.message,
        tests=tests,
        api_key=args.api_key,
    )
    print(f"Submitted job_id={job_id}, waiting for result...")

    item = poll_result(api=args.api, job_id=job_id, api_key=args.api_key)
    pretty_print_autodev(item)


if __name__ == "__main__":
    main()
