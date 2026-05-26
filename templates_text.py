"""README + form description generators for TungkiAsu projects."""
from __future__ import annotations


def render_readme(concept: dict) -> str:
    name = concept["name"]
    tagline = concept["tagline"]
    domain = concept["domain"]
    problem = concept["problem_statement"]
    slug = concept["slug"]
    accent = concept["color_scheme"].lstrip("#")
    sections_human = " / ".join(concept["output_sections"])
    api_kind = concept["api_kind"]

    return f"""<div align=\"center\">

# {name}

### {tagline}

[![Powered by MiMo v2.5 Pro](https://img.shields.io/badge/Powered%20by-MiMo%20v2.5%20Pro-{accent}?style=flat-square)](https://www.xiaomi.com)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black?style=flat-square&logo=next.js)](https://nextjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178c6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Tailwind 4](https://img.shields.io/badge/Tailwind-4-06b6d4?style=flat-square&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](#license)

</div>

---

## What is {name}?

{name} is a single-page tool that {domain.lower()}. The local processing layer extracts structured data deterministically; **MiMo v2.5 Pro** then turns that structured data into the {sections_human} prose output you actually want to read.

It runs as a stateless Next.js 16 app: paste, click, get streaming analysis. No login, no tracking, no DB.

> **Concept-first design.** Every {name} screen is built around the question "what would this tool naturally look like if it shipped as a real product?" — not from a generic template pool.

## Why this exists

{problem}

{name} fixes this with two route handlers:

1. `/api/process` — pure Node logic, no LLM. Parses, validates, extracts structured fields.
2. `/api/analyze` — streams the structured data through MiMo v2.5 Pro to produce {sections_human} prose with concrete references.

Both layers ship together so you can copy the structured JSON for tooling AND read the prose for humans.

## Features

- **Deterministic structured extraction** — `/api/process` runs entirely in Node, instant, no LLM cost.
- **MiMo v2.5 Pro analysis layer** — streaming SSE: {sections_human}.
- **Stateless server** — no DB, no auth, no logging. Input → response → discarded.
- **Mobile-responsive from first commit** — works at 390×844 viewport without sidebar overflow.
- **Sample input one-click** — try the tool against a representative input before pasting your own.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  Browser                                                             │
│   ├─ POST /api/process       ──►  pure Node parser/extractor         │
│   ├─ POST /api/analyze       ──►  MiMo v2.5 Pro (SSE stream)         │
│   │                                  └─► token-plan-sgp.xiaomimimo… │
│   └─ render: streaming output panel + collapsible structured payload │
└──────────────────────────────────────────────────────────────────────┘
```

Two route handlers, no shared state, no DB.

## Tech Stack

| Layer       | Choice                              | Notes                                                     |
|-------------|-------------------------------------|-----------------------------------------------------------|
| Framework   | **Next.js 16** (App Router)         | Route handlers + RSC + client components                  |
| Language    | **TypeScript 5**                    | Strict, ES2018 target                                     |
| Styling     | **Tailwind CSS 4**                  | Custom CSS vars per theme                                 |
| AI Backend  | **MiMo v2.5 Pro** (Token Plan)      | SSE streaming, `api-key` header, dual-field parser        |

## Project Structure

```
{slug}/
├── src/
│   ├── app/
│   │   ├── api/
│   │   │   ├── process/route.ts   # local parser/extractor (no LLM)
│   │   │   └── analyze/route.ts   # MiMo v2.5 Pro stream
│   │   ├── globals.css            # theme tokens
│   │   ├── layout.tsx             # root layout
│   │   └── page.tsx               # input + output panels + FAQ + About
│   └── lib/
├── .env.example                   # MIMO_API_KEY=
├── tsconfig.json                  # ES2018 target
└── README.md                      # you are here
```

## Quick Start

### Prerequisites

- Node 20+
- A MiMo Token Plan API key

### Install

```bash
git clone https://github.com/XinnBlueBird/{slug}
cd {slug}
npm install
cp .env.example .env.local
# edit .env.local — paste your MIMO_API_KEY
```

### Run

```bash
npm run dev
# open http://localhost:3000
```

Production:

```bash
npm run build && npm run start
```

## Environment Variables

| Variable        | Required | Description                       |
|-----------------|----------|-----------------------------------|
| `MIMO_API_KEY`  | ✅ Yes   | MiMo Token Plan key for /api/analyze |

**MiMo endpoint configuration**

| Setting   | Value                                                            |
|-----------|------------------------------------------------------------------|
| Endpoint  | `https://token-plan-sgp.xiaomimimo.com/v1/chat/completions`      |
| Header    | `api-key: <your-key>` (NOT `Authorization: Bearer`)              |
| Model     | `mimo-v2.5-pro`                                                  |
| Streaming | parse BOTH `delta.content` and `delta.reasoning_content`         |

## API Reference

### `POST /api/process`

Local parser. No LLM call.

**Request**
```http
POST /api/process
content-type: application/json

{{ "input": "..." }}
```

**Response**
```json
{{
  "input": "...",
  "processed": {{ /* extracted structured data */ }}
}}
```

### `POST /api/analyze`

Stream MiMo prose analysis from input + processed data.

**Response (SSE)**
```
data: {{"chunk":"VERDICT: ...\\n"}}
data: {{"chunk":"FINDINGS:\\n1. ..."}}
data: [DONE]
```

## Token Usage & Cost

Estimate for ~1,500 analyses/month.

| Module        | Calls/month | Avg input | Avg output | Total tokens |
|---------------|-------------|-----------|------------|--------------|
| `/api/process`| 1,500       | 0         | 0          | 0 (no LLM)   |
| `/api/analyze`| 1,500       | ~600      | ~800       | ~2.1M        |
| **Total**     |             |           |            | **~2.1M**    |

Notes:
- `max_tokens: 8192` to prevent reasoning-content truncation.
- Structured pre-processing in `/api/process` keeps the prompt small.

## Deployment

Any Node 20+ host. For Vercel:

1. Push to GitHub.
2. Import in Vercel.
3. Set `MIMO_API_KEY` in Production env.
4. CLI deploys may not pick up env flags first time — persist with `vercel env add` then redeploy.

## Roadmap

- [ ] Bulk mode (paste N inputs, get N outputs)
- [ ] Permalink for shared analyses (opt-in, signed URLs)
- [ ] CLI mode: `npx {slug} <input>`
- [ ] Self-hosted MiMo proxy with response cache

## Contributing

```bash
git checkout -b feat/your-thing
npm install
npm run build
git commit -m "feat: your thing"
git push origin feat/your-thing
```

## License

MIT — see [LICENSE](LICENSE).

---

<div align=\"center\">

Built solo with **Hermes Agent** and **Claude Code**. Powered by **MiMo v2.5 Pro**.

</div>
"""


def render_description(concept: dict, repo_url: str, vercel_url: str = "") -> str:
    """Generate ~1100 char form description, then verify length."""
    name = concept["name"]
    tagline = concept["tagline"]
    domain = concept["domain"]
    problem = concept["problem_statement"]
    sections = "/".join(concept["output_sections"])

    # Live URL line — only included if vercel_url is non-empty
    live_line = f"\n\nLive: {vercel_url}" if vercel_url else ""

    # tight first draft
    desc = (
        f"I built {name}, {tagline.lower()}. {domain}. "
        f"\n\nProblem: {problem} "
        f"\n\n{name} fixes this via two route handlers. /api/process is pure Node — parses input, extracts structured data, runs validation. No LLM, instant, $0 per call. "
        f"/api/analyze is the MiMo v2.5 Pro layer — streams a {sections} prose output via SSE so you read it as it generates. "
        f"\n\nMiMo integration: api-key header (not Bearer), token-plan-sgp endpoint, mimo-v2.5-pro, max_tokens 8192 to prevent reasoning truncation, parses BOTH delta.content & delta.reasoning_content. "
        f"\n\nStack: Next.js 16, TS 5, Tailwind 4, lucide-react. ES2018, no DB, no auth, no logging. Mobile-responsive from first commit. "
        f"\n\nRepo: {repo_url}"
        f"{live_line}"
    )

    # If over 1200, run progressive trims
    if len(desc) <= 1200:
        return desc

    # tier 1: drop adjective stacks
    desc2 = desc.replace("(not Bearer), ", "")
    desc2 = desc2.replace(" to prevent reasoning truncation", "")
    desc2 = desc2.replace(" so you read it as it generates", "")
    if len(desc2) <= 1200:
        return desc2

    # tier 2: collapse problem
    short_problem = problem.split(". ")[0] + "."  # first sentence only
    desc3 = (
        f"I built {name}, {tagline.lower()}. {domain}. "
        f"\n\nProblem: {short_problem} "
        f"\n\n{name} fixes this via two route handlers. /api/process is pure Node — parses input, extracts structured data. /api/analyze is the MiMo v2.5 Pro layer — streams a {sections} output via SSE. "
        f"\n\nMiMo integration: api-key header, token-plan-sgp endpoint, mimo-v2.5-pro, max_tokens 8192, parses BOTH delta.content & delta.reasoning_content. "
        f"\n\nStack: Next.js 16, TS 5, Tailwind 4, lucide-react. ES2018, no DB, no auth, no logging. Mobile-responsive. "
        f"\n\nRepo: {repo_url}"
        f"{live_line}"
    )
    if len(desc3) <= 1200:
        return desc3

    # tier 3: minimal
    desc4 = (
        f"I built {name}, {tagline.lower()}. {domain}. "
        f"\n\n{name} ships two route handlers. /api/process parses input in pure Node. /api/analyze streams MiMo v2.5 Pro output ({sections}) via SSE. "
        f"\n\nMiMo: api-key header, token-plan-sgp endpoint, mimo-v2.5-pro, max_tokens 8192, parses BOTH content & reasoning_content. "
        f"\n\nStack: Next.js 16, TS 5, Tailwind 4. No DB, no auth, no logging. "
        f"\n\nRepo: {repo_url}"
        f"{live_line}"
    )
    return desc4
