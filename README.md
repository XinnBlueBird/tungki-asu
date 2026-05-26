# TungkiAsu

End-to-end submission worker for the Xiaomi MiMo **100T Token Plan** program.

Given a list of Gmail accounts, the bot:

1. Picks an unused project concept from a curated pool of 115 ideas (each with its own UI layout, problem domain, and MiMo-powered analyzer).
2. Scaffolds a Next.js 16 + TypeScript + Tailwind 4 app, writes the API routes and pages, runs `npm build`.
3. Pushes the project to GitHub as a public repo.
4. Deploys to Vercel for a live `https://<slug>.vercel.app` URL.
5. Captures 5 chrome-framed screenshots (2× GitHub repo + 3× live web app).
6. Fills the MiMo 100T submission form via CloakBrowser through a WARP socks5 proxy, solves the captcha, uploads the screenshots, and submits.
7. DMs the result (success or failure) back to the owner via a Telegram bot.

Runs as two systemd services (one Telegram bot for input, one worker that drains a SQLite job queue).

> ⚠️ **Use at your own risk.** This is grey-area automation against a third-party submission program. The author makes no claims about whether MiMo allows this. Read MiMo's program rules and your local laws before using. The author of this repo is not responsible for accounts banned, prizes withheld, or any other consequence of using this software.

---

## Architecture

```
Telegram bot  ──▶  SQLite queue  ──▶  Worker  ──▶  GitHub + Vercel + MiMo form
   (bot.py)        (db/queue.sqlite)   (worker.py)
```

- **`bot.py`** — Telegram handler. Owner sends a list of Gmails; bot creates one job row per Gmail in `jobs` table, status `pending`.
- **`worker.py`** — Polls `jobs` every 10s, claims one at a time, runs the full pipeline. One job at a time keeps the IP score healthy.
- **`builder.py`** — Scaffolds `create-next-app`, writes `.env.example`, license, gitignore, etc.
- **`templates_ui.py`** — 6 layout variants (`terminal`, `magazine`, `soc`, `brutalist`, `dashboard`, `editorial`). Each project gets a different layout to avoid template-clone detection.
- **`templates_text.py`** — README template, MiMo description renderer (auto-trims to 1200 char limit).
- **`concepts.py`** — The 115-project pool. Each concept ships a slug, name, tagline, layout variant, problem statement, system prompt for MiMo, and output sections.
- **`jobqueue.py`** — SQLite ops, claim/done/failed transitions, used-concept tracking.

---

## Pipeline (per project, ~5–7 min)

| # | Step | What happens | Outputs |
|---|---|---|---|
| 1 | Concept pick | Pick an unused concept_kind, rotate layout away from last 3 | `slug`, `concept` dict |
| 2 | Scaffold + build | `create-next-app`, write API routes + pages, `npm install lucide-react`, `npm build` | `/root/projects/<slug>/` |
| 3 | GitHub push | `gh repo create --public --source=. --push` | `https://github.com/<USER>/<slug>` |
| 4 | Vercel deploy | `vercel-cli --prod --yes --name <slug>` | `https://<slug>.vercel.app` |
| 5 | Screenshots | Playwright + Chrome-frame skill: 2 GitHub + 3 live web | `/tmp/<slug>_ss/repo_{1..5}.png` |
| 6 | MiMo submit | CloakBrowser via WARP socks5, fills 5 fields, solves captcha, uploads SS | `/tmp/<slug>_submit_result.png` |
| 7 | Telegram DM | Photo of the submitted form + repo + live URL caption | message to owner |

---

## Requirements

### System
- Linux (tested on Ubuntu 24.04)
- Python 3.11+
- Node.js 20+ with `npm`
- `git`
- `gh` (GitHub CLI)
- `vercel-cli` (`/usr/local/bin/vercel-cli`, login persisted)
- `warp-cli` running in proxy mode on `127.0.0.1:40000`
- [CloakBrowser](https://github.com/CloakHQ/CloakBrowser) (a Chromium fork with patched fingerprints) installed at `/tmp/cloak_venv/`
- A working `mimo_submit_generic.py` script (ships separately in the Hermes Agent skills tree — see `worker.py:32` for the path)

### Telegram
- A bot created via [@BotFather](https://t.me/BotFather)
- Your numeric Telegram user id (the owner the bot will accept commands from)

### Accounts
- A GitHub PAT with `repo` scope
- Vercel CLI logged in once (`vercel-cli login` — token persists at `~/.local/share/com.vercel.cli/auth.json`)
- 2captcha API key (consumed by the MiMo submit script — see that script's docs)

---

## Setup

1. **Clone**
   ```bash
   git clone https://github.com/<your-fork>/tungki-asu.git
   cd tungki-asu
   ```

2. **Python venv**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install requests
   ```

3. **Credentials (NOT committed)**

   Copy `.env.example` to figure out what files to create. The worker reads them from these absolute paths by default:

   - `/root/.agent/credentials/mimosubmit_bot.env`
     ```
     BOT_TOKEN=123456:AA...
     BOT_OWNER_ID=123456789
     ```
   - `/root/.agent/credentials/github.env`
     ```
     GITHUB_TOKEN=ghp_...
     ```

   `chmod 600` both files.

4. **Vercel login (one-time)**
   ```bash
   /usr/local/bin/vercel-cli login
   ```

5. **WARP proxy (one-time)**
   ```bash
   warp-cli set-mode proxy
   warp-cli connect
   ```

6. **Edit constants in `worker.py`** to match your environment:
   - `GITHUB_USER`
   - paths (`GITHUB_ENV`, `SUBMIT_SCRIPT`, `CLOAK_PY`, etc.)
   - `WARP_PROXY` if using a different port

7. **Create database**
   ```bash
   mkdir -p db
   sqlite3 db/queue.sqlite < /dev/null   # empty file; first worker run creates schema
   ```

8. **Install systemd units**
   ```bash
   sudo cp systemd/tungki-asu-bot.service /etc/systemd/system/
   sudo cp systemd/tungki-asu-worker.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now tungki-asu-bot tungki-asu-worker
   ```

   Logs go to:
   - `/var/log/tungki-asu-bot.log`
   - `/var/log/tungki-asu-worker.log`

---

## Usage

DM the bot from the owner Telegram account. Send a list of Gmail addresses (one per line, or comma/space separated). The bot creates jobs and replies with the batch id. The worker picks them up one-by-one and DMs you a screenshot per submission.

The per-project description always ends with:

```
Repo: https://github.com/<USER>/<slug>
Live: https://<slug>.vercel.app
```

Field 05 of the MiMo form is set to the **live URL** (not the repo) so reviewers see a working app, not source code.

---

## Project structure

```
tungki-asu/
├── bot.py                  # Telegram handler (owner-only)
├── worker.py               # Job-queue drainer + pipeline orchestrator
├── builder.py              # Next.js scaffolding + npm build
├── concepts.py             # 115-project concept pool
├── templates_ui.py         # 6 layout variants for the generated UI
├── templates_text.py       # README + MiMo description renderer
├── jobqueue.py             # SQLite queue ops
├── systemd/                # Service unit files
├── db/                     # SQLite database (gitignored)
└── .env.example            # Credential template
```

---

## Concept pool

115 projects, each unique. Categories include JWT inspectors, regex tools, YAML linters, container scanners, IAM auditors, JSON-to-types generators, k8s manifest generators, log clusterers, schema diffs, SBOM auditors, OIDC auditors, GraphQL cost analyzers, HAProxy/Kafka/Prometheus auditors, and many more. See `concepts.py`.

---

## Failure modes

| Failure | What happens | Recovery |
|---|---|---|
| `npm build` syntax error | Job marked failed, error logged | Fix template; re-queue |
| GitHub push fails | Job marked failed | Check `gh auth status`, retry |
| Vercel deploy fails | **Non-fatal** — worker logs warning, continues without live URL (uses repo URL for field 05, falls back to 5× GitHub SS) | Optional |
| SS capture fails (<5 PNGs) | Job marked failed | Check Chromium / Playwright install |
| MiMo form submit fails (captcha rejected, server `result: False`) | Job retried up to 3× (built into submit script); marked failed after | Often a single rejection — re-submit with new browser profile |

The worker keeps `used_concepts` per slug so the next job never picks a recently-used concept.

---

## License

MIT. See `LICENSE`.

---

## Disclaimer

This is a research / personal-use tool. The author wrote it to study the MiMo 100T submission flow and Next.js scaffolding patterns. **You are responsible for your own use.** Do not use this against any third-party service in violation of its terms. Do not use it to submit fraudulent content. The author is not affiliated with Xiaomi or MiMo.
