"""SQLite job queue for TungkiAsu submission bot."""
from __future__ import annotations
import sqlite3
import json
import time
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path("/root/projects/tungki-asu/db/queue.sqlite")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gmail TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending|building|submitting|done|failed
    project_name TEXT,
    repo_url TEXT,
    desc_chars INTEGER,
    captcha_status TEXT,                     -- accepted|rejected|timeout|null
    submit_status TEXT,                      -- ok|failed|null
    error TEXT,
    ss_dir TEXT,
    submit_result_png TEXT,
    owner_chat_id INTEGER NOT NULL,
    batch_id TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    started_at INTEGER,
    finished_at INTEGER
);

CREATE TABLE IF NOT EXISTS used_concepts (
    slug TEXT PRIMARY KEY,
    concept_kind TEXT NOT NULL,             -- e.g. "regex_builder", "tls_console"
    used_at INTEGER NOT NULL,
    repo_url TEXT
);

CREATE INDEX IF NOT EXISTS idx_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_batch ON jobs(batch_id);
"""

# How long a job can stay in 'building'/'submitting' before it's considered a zombie
# (worker crashed or restarted mid-build). Build is the slowest step (npm install +
# next build), typically 60-120s. 15 min is generous safety margin.
STALE_AFTER_SEC = 15 * 60

# How many times to retry a job before giving up. Each retry resets to 'pending'
# and gets re-claimed. Captures: 429 rate-limits, captcha timeouts, network blips.
MAX_RETRIES = 5


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db():
    with conn() as c:
        c.executescript(SCHEMA)
        # Idempotent migration: add retry_count column if missing
        cols = [r["name"] for r in c.execute("PRAGMA table_info(jobs)").fetchall()]
        if "retry_count" not in cols:
            c.execute("ALTER TABLE jobs ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0")


def recover_stale_jobs() -> int:
    """Requeue jobs stuck in 'building'/'submitting' beyond STALE_AFTER_SEC.

    Called once at worker boot (catches zombies from crashed/restarted workers)
    and periodically inside the main loop. Increments retry_count; jobs that
    exceed MAX_RETRIES are marked 'failed' permanently so they don't loop forever.

    Returns number of jobs recovered.
    """
    init_db()
    cutoff = int(time.time()) - STALE_AFTER_SEC
    recovered = 0
    with conn() as c:
        rows = c.execute(
            "SELECT id, retry_count, project_name FROM jobs "
            "WHERE status IN ('building', 'submitting') AND started_at < ?",
            (cutoff,),
        ).fetchall()
        for row in rows:
            new_retries = (row["retry_count"] or 0) + 1
            if new_retries > MAX_RETRIES:
                c.execute(
                    "UPDATE jobs SET status='failed', error=?, finished_at=?, retry_count=? WHERE id=?",
                    (f"max retries exceeded ({MAX_RETRIES}) — last stuck in build/submit", int(time.time()), new_retries, row["id"]),
                )
            else:
                c.execute(
                    "UPDATE jobs SET status='pending', started_at=NULL, retry_count=? WHERE id=?",
                    (new_retries, row["id"]),
                )
                recovered += 1
    return recovered


def requeue_failed() -> int:
    """Requeue all 'failed' jobs back to 'pending', respecting MAX_RETRIES.

    Worker calls this periodically so 429-failures (or anything mark_failed'd
    mid-run) get auto-retried instead of needing manual intervention.

    Returns number of jobs requeued.
    """
    init_db()
    requeued = 0
    with conn() as c:
        rows = c.execute(
            "SELECT id, retry_count FROM jobs WHERE status='failed' AND COALESCE(retry_count,0) < ?",
            (MAX_RETRIES,),
        ).fetchall()
        for row in rows:
            new_retries = (row["retry_count"] or 0) + 1
            c.execute(
                "UPDATE jobs SET status='pending', error=NULL, started_at=NULL, finished_at=NULL, retry_count=? WHERE id=?",
                (new_retries, row["id"]),
            )
            requeued += 1
    return requeued


def enqueue_batch(gmails: list[str], owner_chat_id: int) -> tuple[str, list[int]]:
    """Add a batch of gmails to the queue. Returns (batch_id, [job_ids])."""
    init_db()
    batch_id = f"batch_{int(time.time())}"
    ts = int(time.time())
    job_ids = []
    with conn() as c:
        for g in gmails:
            cur = c.execute(
                "INSERT INTO jobs (gmail, owner_chat_id, batch_id, created_at) VALUES (?, ?, ?, ?)",
                (g.strip(), owner_chat_id, batch_id, ts),
            )
            job_ids.append(cur.lastrowid)
    return batch_id, job_ids


def claim_next() -> dict | None:
    """Atomically claim the oldest pending job. Returns row dict or None."""
    init_db()
    with conn() as c:
        row = c.execute(
            "SELECT * FROM jobs WHERE status = 'pending' ORDER BY id ASC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        c.execute(
            "UPDATE jobs SET status = 'building', started_at = ? WHERE id = ?",
            (int(time.time()), row["id"]),
        )
        return dict(row)


def update_job(job_id: int, **fields):
    init_db()
    keys = ",".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [job_id]
    with conn() as c:
        c.execute(f"UPDATE jobs SET {keys} WHERE id = ?", vals)


def mark_done(job_id: int, **fields):
    update_job(job_id, status="done", finished_at=int(time.time()), **fields)


def mark_failed(job_id: int, error: str, **fields):
    update_job(job_id, status="failed", error=error[:500], finished_at=int(time.time()), **fields)


def get_batch_jobs(batch_id: str) -> list[dict]:
    init_db()
    with conn() as c:
        rows = c.execute("SELECT * FROM jobs WHERE batch_id = ? ORDER BY id ASC", (batch_id,)).fetchall()
        return [dict(r) for r in rows]


def get_pending_count() -> int:
    init_db()
    with conn() as c:
        row = c.execute("SELECT COUNT(*) as n FROM jobs WHERE status IN ('pending', 'building', 'submitting')").fetchone()
        return row["n"]


def get_active_batches() -> list[str]:
    init_db()
    with conn() as c:
        rows = c.execute(
            "SELECT DISTINCT batch_id FROM jobs WHERE status IN ('pending', 'building', 'submitting') ORDER BY batch_id ASC"
        ).fetchall()
        return [r["batch_id"] for r in rows]


def is_batch_complete(batch_id: str) -> bool:
    init_db()
    with conn() as c:
        row = c.execute(
            "SELECT COUNT(*) as n FROM jobs WHERE batch_id = ? AND status NOT IN ('done', 'failed')",
            (batch_id,),
        ).fetchone()
        return row["n"] == 0


def record_concept(slug: str, concept_kind: str, repo_url: str):
    init_db()
    with conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO used_concepts (slug, concept_kind, used_at, repo_url) VALUES (?, ?, ?, ?)",
            (slug, concept_kind, int(time.time()), repo_url),
        )


def get_burned_concepts() -> set[str]:
    init_db()
    with conn() as c:
        rows = c.execute("SELECT concept_kind FROM used_concepts").fetchall()
        return {r["concept_kind"] for r in rows}


def get_burned_slugs() -> set[str]:
    init_db()
    with conn() as c:
        rows = c.execute("SELECT slug FROM used_concepts").fetchall()
        return {r["slug"] for r in rows}
