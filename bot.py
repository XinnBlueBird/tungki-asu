"""TungkiAsu bot — Telegram interface for the submission queue.

Owner-only. Send a list of gmails (one per line, or space/comma separated) and
the bot enqueues each one. Worker handles the rest in the background and DMs
back per-project + end-of-batch recap.

Commands:
  /start    — onboarding text
  /status   — show queue: pending / building / submitting / done / failed
  /list     — list pending jobs
  /cancel   — cancel pending jobs (keeps in-progress one)
  /reset    — wipe burned concepts (use with care; allows reusing concept kinds)
"""
from __future__ import annotations
import asyncio
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from jobqueue import (
    init_db, enqueue_batch, get_pending_count, get_active_batches,
    get_batch_jobs,
)


def load_env() -> tuple[str, int]:
    env_path = Path("/root/.agent/credentials/mimosubmit_bot.env")
    token = ""
    owner = 0
    for line in env_path.read_text().splitlines():
        if line.startswith("BOT_TOKEN="):
            token = line.split("=", 1)[1].strip()
        elif line.startswith("BOT_OWNER_ID="):
            owner = int(line.split("=", 1)[1].strip())
    return token, owner


BOT_TOKEN, BOT_OWNER_ID = load_env()


GMAIL_RX = re.compile(r"[A-Za-z0-9._%+-]+@gmail\.com", re.IGNORECASE)


def owner_only(handler):
    async def wrap(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user or update.effective_user.id != BOT_OWNER_ID:
            return
        return await handler(update, context)
    return wrap


@owner_only
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "TungkiAsu — autonomous MiMo 100T submission bot\n\n"
        "Drop a list of gmails (one per line, or space-separated) and I'll:\n"
        "1. Pick a fresh concept (never repeats domain)\n"
        "2. Build a Next.js project with MiMo v2.5 Pro integration\n"
        "3. Push to github.com/XinnBlueBird\n"
        "4. Capture 5 chrome-framed screenshots\n"
        "5. Submit MiMo 100T form via WARP + cloakbrowser 0.3.30\n"
        "6. DM you 'start project N' on each new project\n"
        "7. DM you the success SS + 4-line summary on completion\n\n"
        "Commands:\n"
        "/queue <gmails>   — explicit enqueue\n"
        "/status           — counts per status\n"
        "/list             — pending + in-progress jobs\n"
        "/pool             — concept pool (used / fresh remaining)\n"
        "/cancel           — cancel all pending\n"
        "/reset            — wipe burned concept history\n\n"
        "Or just paste the gmail list — auto-detected."
    )
    await update.message.reply_text(msg)


@owner_only
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import sqlite3
    from jobqueue import DB_PATH
    init_db()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT status, COUNT(*) as n FROM jobs GROUP BY status").fetchall()
    conn.close()
    lines = ["queue status:"]
    seen = {s: n for s, n in rows}
    for s in ("pending", "building", "submitting", "done", "failed"):
        lines.append(f"  {s}: {seen.get(s, 0)}")
    await update.message.reply_text("<pre>" + "\n".join(lines) + "</pre>", parse_mode="HTML")


@owner_only
async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import sqlite3
    from jobqueue import DB_PATH
    init_db()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, gmail, status, project_name FROM jobs WHERE status IN ('pending','building','submitting') ORDER BY id ASC LIMIT 50"
    ).fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("queue is empty")
        return
    lines = []
    for jid, gmail, status, name in rows:
        emoji = {"pending": "·", "building": "▸", "submitting": "▸▸"}.get(status, "?")
        lines.append(f"{emoji} #{jid} {gmail[:25]:<25} {status:<10} {name or ''}")
    await update.message.reply_text("<pre>" + "\n".join(lines) + "</pre>", parse_mode="HTML")


@owner_only
async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import sqlite3
    from jobqueue import DB_PATH
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("UPDATE jobs SET status = 'failed', error = 'cancelled' WHERE status = 'pending'")
    n = cur.rowcount
    conn.commit()
    conn.close()
    await update.message.reply_text(f"cancelled {n} pending jobs (in-progress one keeps running)")


@owner_only
async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import sqlite3
    from jobqueue import DB_PATH
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("DELETE FROM used_concepts")
    n = cur.rowcount
    conn.commit()
    conn.close()
    await update.message.reply_text(f"burned concepts wiped ({n} entries removed). Pool is full again.")


@owner_only
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    gmails = sorted(set(GMAIL_RX.findall(text)))
    if not gmails:
        await update.message.reply_text("no gmails detected — paste gmail addresses (one per line or space-separated)")
        return
    batch_id, job_ids = enqueue_batch(gmails, BOT_OWNER_ID)
    pending = get_pending_count()
    await update.message.reply_text(
        f"queued {len(gmails)} jobs · batch {batch_id}\n"
        f"in queue right now: {pending}\n"
        f"working through them silently. you'll get one DM per project as it submits."
    )


@owner_only
async def queue_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/queue <gmail1> <gmail2> ... — explicit enqueue (same as pasting)."""
    text = " ".join(context.args or [])
    gmails = sorted(set(GMAIL_RX.findall(text)))
    if not gmails:
        await update.message.reply_text("usage: /queue gmail1@gmail.com gmail2@gmail.com ...")
        return
    batch_id, _ = enqueue_batch(gmails, BOT_OWNER_ID)
    await update.message.reply_text(f"queued {len(gmails)} jobs · batch {batch_id}")


@owner_only
async def pool_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show concept pool: total, used, fresh remaining."""
    import sqlite3
    from jobqueue import DB_PATH
    from concepts import CONCEPTS
    init_db()
    conn = sqlite3.connect(DB_PATH)
    used = {r[0] for r in conn.execute("SELECT concept_kind FROM used_concepts").fetchall()}
    used_slugs = {r[0] for r in conn.execute("SELECT slug FROM used_concepts").fetchall()}
    conn.close()
    fresh = [c for c in CONCEPTS if c["concept_kind"] not in used and c["slug"] not in used_slugs]
    lines = [
        f"concept pool: {len(CONCEPTS)} total",
        f"used: {len(used_slugs)}",
        f"fresh: {len(fresh)}",
        "",
        "next picks (random order):",
    ]
    for c in fresh[:10]:
        lines.append(f"  · {c['slug']:<14} {c['layout_variant']:<10} {c['tagline'][:38]}")
    if len(fresh) > 10:
        lines.append(f"  … (+{len(fresh) - 10} more)")
    await update.message.reply_text("<pre>" + "\n".join(lines) + "</pre>", parse_mode="HTML")


def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("list", list_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(CommandHandler("queue", queue_cmd))
    app.add_handler(CommandHandler("pool", pool_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("[bot] starting polling")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
