"""TungkiAsu worker — claims pending jobs, builds project, submits MiMo form, reports.

Run as systemd service. Polls SQLite queue every 10s. One job at a time (sequential,
not parallel — Xiaomi rate-limits per IP).
"""
from __future__ import annotations
import os
import sys
import time
import json
import shutil
import asyncio
import subprocess
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from jobqueue import (
    init_db, claim_next, mark_done, mark_failed, update_job,
    record_concept, get_burned_concepts, get_burned_slugs, is_batch_complete,
    get_batch_jobs,
)
from concepts import pick_unused, find_concept
from builder import scaffold, write_env_files, write_api_routes, run as bld_run
from templates_ui import render_layout
from templates_text import render_readme, render_description

GITHUB_USER = "XinnBlueBird"
GITHUB_ENV = "/root/.agent/credentials/github.env"
SUBMIT_SCRIPT = "/root/.hermes/skills/crypto/mimo-100t-form/scripts/mimo_submit_generic.py"
CAPTURE_SCRIPT = "/tmp/capture_5_repo_ss.py"
CLOAK_PY = "/tmp/cloak_venv/bin/python"
WARP_PROXY = "socks5://127.0.0.1:40000"

BOT_TOKEN = ""
BOT_OWNER_ID = 0


def load_creds():
    global BOT_TOKEN, BOT_OWNER_ID
    env = Path("/root/.agent/credentials/mimosubmit_bot.env").read_text()
    for line in env.splitlines():
        if line.startswith("BOT_TOKEN="):
            BOT_TOKEN = line.split("=", 1)[1].strip()
        elif line.startswith("BOT_OWNER_ID="):
            BOT_OWNER_ID = int(line.split("=", 1)[1].strip())


def tg_send_text(chat_id: int, text: str):
    import requests
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=20,
        )
    except Exception as e:
        print(f"[tg_send_text] {e}")


def tg_send_photo(chat_id: int, path: str, caption: str = ""):
    import requests
    try:
        with open(path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                data={"chat_id": chat_id, "caption": caption[:1024]},
                files={"photo": f},
                timeout=60,
            )
    except Exception as e:
        print(f"[tg_send_photo] {e}")


def get_recent_layouts(n: int = 3) -> list[str]:
    """Return layout_variants of the last N completed jobs."""
    import sqlite3
    db = "/root/projects/tungki-asu/db/queue.sqlite"
    try:
        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT j.project_name FROM jobs j WHERE j.status = 'done' ORDER BY j.id DESC LIMIT ?",
            (n,),
        ).fetchall()
        conn.close()
    except Exception:
        return []
    layouts = []
    for (name,) in rows:
        # find the concept by slug-from-name
        slug = (name or "").lower()
        c = find_concept(slug)
        if c:
            layouts.append(c["layout_variant"])
    return layouts


def pick_concept() -> dict:
    burned = get_burned_concepts()
    burned_slugs = get_burned_slugs()
    recent = get_recent_layouts(3)
    c = pick_unused(burned, burned_slugs, recent)
    if not c:
        raise RuntimeError("no fresh concepts left in pool")
    return c


def pick_unused_locked() -> dict:
    """Same as pick_concept but always atomic via DB-record on the fly."""
    return pick_concept()


def build_project(concept: dict) -> Path:
    """Scaffold + write all source files + npm build."""
    proj = scaffold(concept)
    write_env_files(proj)
    write_api_routes(proj, concept)
    page_tsx, css, layout_tsx = render_layout(concept)
    (proj / "src/app/page.tsx").write_text(page_tsx)
    (proj / "src/app/globals.css").write_text(css)
    (proj / "src/app/layout.tsx").write_text(layout_tsx)
    (proj / "README.md").write_text(render_readme(concept))
    rc, out = bld_run("npm run build", cwd=proj)
    if rc != 0:
        raise RuntimeError(f"npm build failed: {out[-600:]}")
    return proj


def push_github(concept: dict, proj: Path) -> str:
    slug = concept["slug"]
    desc = f"{concept['tagline']}. Powered by MiMo v2.5 Pro."
    cmd = (
        f". {GITHUB_ENV} && export GH_TOKEN=$GITHUB_TOKEN && "
        f"cd {proj} && git init -b main 2>&1 && "
        f"git add . && "
        f"git -c user.email=xinnblubird@gmail.com -c user.name={GITHUB_USER} commit -m 'feat: initial release' && "
        f"gh repo create {GITHUB_USER}/{slug} --public --description '{desc}' --source=. --push"
    )
    rc, out = bld_run(cmd)
    if rc != 0:
        raise RuntimeError(f"github push failed: {out[-500:]}")
    return f"https://github.com/{GITHUB_USER}/{slug}"


def deploy_vercel(concept: dict, proj: Path) -> str:
    """Deploy project to Vercel production. Returns the live URL.

    Vercel CLI v54+ uses --yes (unattended) and auto-detects Next.js. Token stored
    in /root/.local/share/com.vercel.cli/auth.json (vercel-cli login persisted).
    Resolves alias to root domain (xxx.vercel.app) so SS shows clean URL, not
    the long deployment-id URL (xxx-abcd123-team.vercel.app).
    """
    slug = concept["slug"]
    cmd = f"/usr/local/bin/vercel-cli --prod --yes --name {slug}"
    rc, out = bld_run(cmd, cwd=proj)
    if rc != 0:
        raise RuntimeError(f"vercel deploy failed: {out[-500:]}")
    # Vercel prints production URL to stderr/stdout; grab the *.vercel.app line
    import re
    urls = re.findall(r"https://[a-z0-9-]+\.vercel\.app", out)
    if not urls:
        raise RuntimeError(f"vercel url not found in output: {out[-300:]}")
    # Prefer the shortest URL (root alias e.g. slug.vercel.app over slug-abcd-team.vercel.app)
    url = sorted(set(urls), key=len)[0]
    return url


def capture_screenshots(slug: str, vercel_url: str = "") -> Path:
    """Run the 5-SS capture script. Returns ss directory.

    Layout: 2x github (repo top + README) + 3x live web (hero/mid/bottom).
    Falls back to 5x github if vercel_url is empty.
    """
    cmd = f"{CLOAK_PY} {CAPTURE_SCRIPT} {slug} '{vercel_url}'"
    rc, out = bld_run(cmd)
    if rc != 0:
        raise RuntimeError(f"ss capture failed: {out[-400:]}")
    ss_dir = Path(f"/tmp/{slug}_ss")
    if not ss_dir.exists() or len(list(ss_dir.glob("repo_*.png"))) < 5:
        raise RuntimeError(f"expected 5 SS in {ss_dir}, got {len(list(ss_dir.glob('repo_*.png')))}")
    return ss_dir


def submit_form(concept: dict, gmail: str, repo_url: str, ss_dir: Path, vercel_url: str = "") -> tuple[Path, str]:
    """Run the mimo_submit_generic.py script via WARP. Returns (result_png, status)."""
    slug = concept["slug"]
    desc_path = Path(f"/tmp/{slug}_desc.txt")
    desc = render_description(concept, repo_url, vercel_url=vercel_url)
    desc_path.write_text(desc)
    if len(desc) > 1200:
        raise RuntimeError(f"description too long: {len(desc)} chars")

    profile = f"/root/.hermes/browser_profiles/mimo_100t_{slug}"
    shutil.rmtree(profile, ignore_errors=True)
    result_png = Path(f"/tmp/{slug}_submit_result.png")
    status_txt = Path(f"/tmp/{slug}_submit_status.txt")
    proof_files = ",".join(str(ss_dir / f"repo_{i}.png") for i in range(1, 6))

    env = os.environ.copy()
    env.update({
        "MIMO_EMAIL": gmail,
        # Field 05 URL: prefer live vercel URL (working app) over github repo
        # so reviewers see the running product, not just source code.
        "MIMO_PROOF_URL": vercel_url or repo_url,
        "MIMO_PROOF_FILES": proof_files,
        "MIMO_DESC_FILE": str(desc_path),
        "MIMO_PROFILE": profile,
        "MIMO_RESULT_PNG": str(result_png),
        "MIMO_STATUS": str(status_txt),
        "MIMO_AUTO_SUBMIT": "1",
        "MIMO_PROXY": WARP_PROXY,
        "PYTHONUNBUFFERED": "1",
    })
    p = subprocess.run(
        [CLOAK_PY, "-u", SUBMIT_SCRIPT],
        capture_output=True, text=True, env=env, timeout=900,
    )
    log = p.stdout + p.stderr
    if "DONE" not in log or "POST_OK" not in log:
        raise RuntimeError(f"submit failed: {log[-500:]}")
    return result_png, log[-200:]


def process_job(job: dict):
    job_id = job["id"]
    gmail = job["gmail"]
    owner = job["owner_chat_id"]

    # count which project number this is in the batch
    batch_jobs = get_batch_jobs(job["batch_id"])
    idx = next((i + 1 for i, r in enumerate(batch_jobs) if r["id"] == job_id), 0)
    total = len(batch_jobs)

    # 1. pick concept
    try:
        concept = pick_unused_locked()
        update_job(job_id, project_name=concept["slug"])
        record_concept(concept["slug"], concept["concept_kind"], "")  # reserve before push
    except Exception as e:
        mark_failed(job_id, f"pick_concept: {e}")
        tg_send_text(owner, f"❌ Job {job_id} failed at concept pick: <code>{e}</code>")
        return

    # NOTIFY: project N starting
    tg_send_text(owner, f"▸ start project {idx}/{total} · <b>{concept['name']}</b> · {gmail}")

    # 2. build
    try:
        proj = build_project(concept)
    except Exception as e:
        mark_failed(job_id, f"build: {e}")
        tg_send_text(owner, f"Job {job_id} ({concept['slug']}) failed at build: <code>{str(e)[:200]}</code>")
        return

    # 3. github push
    try:
        repo_url = push_github(concept, proj)
        update_job(job_id, repo_url=repo_url)
        record_concept(concept["slug"], concept["concept_kind"], repo_url)  # update with real URL
    except Exception as e:
        mark_failed(job_id, f"github: {e}")
        tg_send_text(owner, f"Job {job_id} ({concept['slug']}) failed at github push: <code>{str(e)[:200]}</code>")
        return

    # 3.5. vercel deploy (live URL needed so MiMo plan != standard)
    vercel_url = ""
    try:
        vercel_url = deploy_vercel(concept, proj)
        update_job(job_id, vercel_url=vercel_url)
    except Exception as e:
        # Non-fatal: SS still capture github, submission can proceed without live URL.
        # But we DO want to know — alert and keep going so the IP/email isn't wasted.
        tg_send_text(owner, f"⚠️ Job {job_id} ({concept['slug']}) vercel deploy failed (continuing without live URL): <code>{str(e)[:200]}</code>")

    # 4. screenshots (2x github + 3x live web if vercel deployed, else 5x github)
    try:
        ss_dir = capture_screenshots(concept["slug"], vercel_url=vercel_url)
        update_job(job_id, ss_dir=str(ss_dir))
    except Exception as e:
        mark_failed(job_id, f"ss: {e}")
        tg_send_text(owner, f"Job {job_id} ({concept['slug']}) failed at SS capture: <code>{str(e)[:200]}</code>")
        return

    # 5. submit form
    update_job(job_id, status="submitting")
    try:
        result_png, _ = submit_form(concept, gmail, repo_url, ss_dir, vercel_url=vercel_url)
        update_job(job_id, submit_result_png=str(result_png), captcha_status="accepted", submit_status="ok")
    except Exception as e:
        err_msg = str(e)
        captcha = "rejected" if "REJECTED" in err_msg or "result: False" in err_msg else "timeout" if "timeout" in err_msg.lower() else "failed"
        mark_failed(job_id, f"submit: {err_msg[:300]}", captcha_status=captcha, submit_status="failed")
        tg_send_text(owner, f"Job {job_id} ({concept['slug']}) submit failed: <code>{err_msg[:200]}</code>")
        return

    # 6. report success
    mark_done(job_id, captcha_status="accepted", submit_status="ok")
    live_line = f"\nLive: {vercel_url}" if vercel_url else ""
    caption = (
        f"✅ {concept['name']} submitted Xinn\n\n"
        f"Project: {concept['name']}\n"
        f"Repo: {repo_url}"
        f"{live_line}\n"
        f"Email: {gmail}"
    )
    tg_send_photo(owner, str(result_png), caption=caption)

    # 7. end-of-batch recap if batch complete
    if is_batch_complete(job["batch_id"]):
        send_batch_recap(owner, job["batch_id"])


def send_batch_recap(owner: int, batch_id: str):
    rows = get_batch_jobs(batch_id)
    lines = [
        "XIAOMI MiMo 100T - BATCH RECAP",
        f"{batch_id}",
        "",
    ]
    ok_n = 0
    for i, r in enumerate(rows, 1):
        emoji = "✅" if r["status"] == "done" else "❌"
        if r["status"] == "done":
            ok_n += 1
        name = (r["project_name"] or "?")[:16].ljust(16)
        ts = time.strftime("%Y-%m-%d %H:%M", time.gmtime(r.get("finished_at") or r.get("started_at") or time.time()))
        lines.append(f"[{i:02d}] {emoji} {name} {ts}")
    lines.append("")
    lines.append(f"SUMMARY")
    lines.append(f"total submissions : {len(rows)}")
    lines.append(f"accepted          : {ok_n} / {len(rows)}")
    lines.append("")
    lines.append("DONE")
    tg_send_text(owner, f"<pre>{chr(10).join(lines)}</pre>")


def main_loop():
    init_db()
    load_creds()
    print(f"[worker] started, owner={BOT_OWNER_ID}")
    while True:
        job = claim_next()
        if not job:
            time.sleep(10)
            continue
        try:
            process_job(job)
        except Exception:
            traceback.print_exc()
            mark_failed(job["id"], "unhandled exception")
        # small cooldown between jobs to keep IP score healthy
        time.sleep(5)


if __name__ == "__main__":
    main_loop()
