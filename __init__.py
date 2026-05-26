"""TungkiAsu — autonomous MiMo 100T submission bot.

Architecture:
- Telegram bot (python-telegram-bot 21) accepts gmail lists from owner
- SQLite queue persists pending submissions across restarts
- Worker (systemd unit) picks up jobs sequentially
- Per-project flow: build Next.js + push GitHub + 5 SS + submit MiMo form via WARP
- Reports per-project to owner DM, end-of-batch SS recap

NO Vercel deploy. NO progress chatter. Silent until done.
"""
