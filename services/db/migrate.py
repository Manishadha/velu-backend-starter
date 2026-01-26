from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Iterable

import psycopg
import re

MIGRATIONS_DIR = Path(__file__).with_name("migrations")
_MIG_RE = re.compile(r"^(?P<num>\d+)_.*\.sql$")


def _should_skip() -> bool:
    if os.getenv("VELU_SKIP_MIGRATIONS") == "1":
        return True
    if "pytest" in sys.modules:
        return True
    if os.getenv("VELU_TESTING") == "1":
        return True
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    return False


def _db_url() -> str:
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    if url.lower().startswith("postgresql+psycopg://"):
        url = "postgresql://" + url.split("://", 1)[1]
    if url.lower().startswith("postgres://"):
        url = "postgresql://" + url.split("://", 1)[1]
    return url


def _iter_sql_files() -> Iterable[Path]:
    if not MIGRATIONS_DIR.exists():
        return []

    files = [p for p in MIGRATIONS_DIR.iterdir() if p.is_file() and p.suffix == ".sql"]

    
    def sort_key(p: Path):
        m = _MIG_RE.match(p.name)
        if not m:
            
            return (10**9, p.name)
        return (int(m.group("num")), p.name)

    files_sorted = sorted(files, key=sort_key)

    
    bad = [p.name for p in files_sorted if not _MIG_RE.match(p.name)]
    if bad:
        raise RuntimeError(
            "Migration files must be named like '0001_name.sql'. Bad files: " + ", ".join(bad)
        )

    return files_sorted

def migrate() -> None:
    # Respect explicit skip
    if os.getenv("VELU_SKIP_MIGRATIONS") == "1":
        return

    # Skip during pytest (collection + runtime safe)
    if os.getenv("PYTEST_CURRENT_TEST") or "pytest" in sys.modules:
        return

    # Unit-test mode (explicit)
    if os.getenv("VELU_TESTING") == "1":
        return

    # If DATABASE_URL is not set, nothing to migrate (local/sqlite mode)
    db_raw = (os.getenv("DATABASE_URL") or "").strip()
    if not db_raw:
        return

    url = _db_url()

    last_error = None
    for attempt in range(10):  # ~30s total
        try:
            with psycopg.connect(url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS schema_migrations (
                            version TEXT PRIMARY KEY,
                            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                        );
                        """
                    )

                    cur.execute("SELECT version FROM schema_migrations;")
                    applied = {row[0] for row in cur.fetchall()}

                    for path in _iter_sql_files():
                        print("MIGRATE:", path.name, flush=True)
                        version = path.stem
                        if version in applied:
                            continue

                        sql = path.read_text(encoding="utf-8")

                        try:
                            cur.execute(sql)
                        except Exception as e:
                            raise RuntimeError(f"Migration failed in {path.name}: {e}") from e

                        cur.execute(
                            "INSERT INTO schema_migrations(version) VALUES (%s)",
                            (version,),
                        )


                conn.commit()
            return  # success

        except Exception as exc:
            last_error = exc
            time.sleep(3)

    raise RuntimeError(f"Database not ready after retries: {last_error}")


if __name__ == "__main__":
    migrate()
