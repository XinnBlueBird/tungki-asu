"""Project builder — scaffolds Next.js from a concept dict.

Each concept produces a complete project at /root/projects/<slug>/ with:
- src/app/api/analyze/route.ts (MiMo proxy with concept.system_prompt)
- src/app/api/process/route.ts (concept-specific local logic, no LLM)
- src/app/page.tsx (UI with layout variant)
- src/app/globals.css (theme matching concept.color_scheme)
- README.md (16-section pro-grade)
- .env.example, .gitignore, LICENSE, package.json deps

The layout_variant drives ALL of: hero shape, nav placement, color palette intensity,
typography choice, output panel layout. Six variants are mutually distinct.
"""
from __future__ import annotations
import json
import shutil
import subprocess
from pathlib import Path

PROJECTS_ROOT = Path("/root/projects")


def run(cmd: str, cwd: Path | None = None, env: dict | None = None) -> tuple[int, str]:
    """Run a shell command, return (returncode, combined_output)."""
    p = subprocess.run(cmd, shell=True, executable="/bin/bash", capture_output=True, text=True, cwd=cwd, env=env, timeout=600)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def scaffold(concept: dict) -> Path:
    """create-next-app + bump tsconfig + install deps."""
    slug = concept["slug"]
    proj = PROJECTS_ROOT / slug
    if proj.exists():
        shutil.rmtree(proj)
    rc, out = run(
        f"npx create-next-app@latest {slug} --typescript --tailwind --app --src-dir --no-eslint --use-npm --no-import-alias",
        cwd=PROJECTS_ROOT,
    )
    if rc != 0:
        raise RuntimeError(f"create-next-app failed: {out[-400:]}")
    # bump TS target
    tsc = proj / "tsconfig.json"
    tsc.write_text(tsc.read_text().replace('"target": "ES2017"', '"target": "ES2018"'))
    # remove default page module css
    (proj / "src/app/page.module.css").unlink(missing_ok=True)
    # install lucide
    rc, out = run("npm install lucide-react", cwd=proj)
    if rc != 0:
        raise RuntimeError(f"npm install lucide-react failed: {out[-400:]}")
    return proj


def write_env_files(proj: Path):
    (proj / ".env.example").write_text("MIMO_API_KEY=your_mimo_token_plan_key_here\n")
    (proj / ".gitignore").write_text("\n".join([
        "/node_modules", "/.next/", "/out/", "/build", ".DS_Store", "*.pem",
        "npm-debug.log*", ".env", ".env.local", ".env.*.local", "*.tsbuildinfo",
        "next-env.d.ts", ".vercel", ""
    ]))
    (proj / "LICENSE").write_text(_LICENSE)


def write_api_routes(proj: Path, concept: dict):
    """Two routes: /api/process (local logic) + /api/analyze (MiMo proxy)."""
    api = proj / "src/app/api"
    (api / "process").mkdir(parents=True, exist_ok=True)
    (api / "analyze").mkdir(parents=True, exist_ok=True)

    # /api/process — concept-specific local logic
    process_handler = _PROCESS_HANDLERS.get(concept["api_kind"], _DEFAULT_PROCESS)
    (api / "process/route.ts").write_text(process_handler)

    # /api/analyze — MiMo proxy with concept's system prompt
    sys_prompt = concept["system_prompt"].replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    analyze = f"""import {{ NextRequest }} from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const MIMO_ENDPOINT = "https://token-plan-sgp.xiaomimimo.com/v1/chat/completions";
const MIMO_MODEL = "mimo-v2.5-pro";

const SYSTEM_PROMPT = `{sys_prompt}`;

export async function POST(req: NextRequest) {{
  const apiKey = process.env.MIMO_API_KEY;
  if (!apiKey) return new Response("MIMO_API_KEY missing", {{ status: 500 }});

  const body = await req.json();
  const userPrompt = `Input:\\n${{JSON.stringify(body.input ?? body)}}\\n\\nProcess output:\\n${{JSON.stringify(body.processed ?? null)}}\\n\\nProvide your analysis.`;

  const upstream = await fetch(MIMO_ENDPOINT, {{
    method: "POST",
    headers: {{ "api-key": apiKey, "content-type": "application/json" }},
    body: JSON.stringify({{
      model: MIMO_MODEL,
      stream: true,
      max_tokens: 8192,
      messages: [
        {{ role: "system", content: SYSTEM_PROMPT }},
        {{ role: "user", content: userPrompt }},
      ],
    }}),
  }});

  if (!upstream.ok || !upstream.body) {{
    const text = await upstream.text().catch(() => "");
    return new Response(`upstream ${{upstream.status}}: ${{text.slice(0, 200)}}`, {{ status: 502 }});
  }}

  const decoder = new TextDecoder();
  const encoder = new TextEncoder();

  const stream = new ReadableStream({{
    async start(controller) {{
      const reader = upstream.body!.getReader();
      let buf = "";
      try {{
        while (true) {{
          const {{ done, value }} = await reader.read();
          if (done) break;
          buf += decoder.decode(value, {{ stream: true }});
          const lines = buf.split("\\n");
          buf = lines.pop() || "";
          for (const line of lines) {{
            const t = line.trim();
            if (!t.startsWith("data:")) continue;
            const payload = t.slice(5).trim();
            if (payload === "[DONE]") {{
              controller.enqueue(encoder.encode("data: [DONE]\\n\\n"));
              continue;
            }}
            try {{
              const json = JSON.parse(payload);
              const d = json.choices?.[0]?.delta;
              const chunk = d?.content || d?.reasoning_content || "";
              if (chunk) controller.enqueue(encoder.encode(`data: ${{JSON.stringify({{ chunk }})}}\\n\\n`));
            }} catch {{
              // skip
            }}
          }}
        }}
      }} catch (err) {{
        const m = err instanceof Error ? err.message : "stream err";
        controller.enqueue(encoder.encode(`data: ${{JSON.stringify({{ error: m }})}}\\n\\n`));
      }} finally {{
        controller.close();
      }}
    }},
  }});

  return new Response(stream, {{
    headers: {{ "content-type": "text/event-stream", "cache-control": "no-cache, no-transform", connection: "keep-alive" }},
  }});
}}
"""
    (api / "analyze/route.ts").write_text(analyze)


# -- Process handlers per api_kind --

_DEFAULT_PROCESS = """import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const body = await req.json();
  // pass-through: most concepts just hand the input straight to MiMo
  return NextResponse.json({ input: body.input, processed: null });
}
"""

_JWT_PROCESS = """import { NextRequest, NextResponse } from "next/server";
export const runtime = "nodejs";

function decode(token: string) {
  const parts = token.split(".");
  if (parts.length !== 3) throw new Error("malformed JWT (expected 3 parts)");
  const [h, p] = parts;
  const decode64 = (s: string) => JSON.parse(Buffer.from(s.replace(/-/g, "+").replace(/_/g, "/"), "base64").toString("utf8"));
  return { header: decode64(h), payload: decode64(p) };
}

export async function POST(req: NextRequest) {
  try {
    const { input } = await req.json();
    const { header, payload } = decode((input as string).trim());
    const now = Math.floor(Date.now() / 1000);
    const expired = payload.exp ? payload.exp < now : null;
    const algo = header.alg;
    const claims = ["iss", "sub", "aud", "exp", "iat", "nbf", "jti"];
    const claimsPresent = claims.filter((k) => payload[k] != null);
    return NextResponse.json({
      input,
      processed: { header, payload, expired, algo, claimsPresent, claimsMissing: claims.filter((c) => !claimsPresent.includes(c)) },
    });
  } catch (err) {
    return NextResponse.json({ error: err instanceof Error ? err.message : "decode failed" }, { status: 400 });
  }
}
"""

_REGEX_PROCESS = """import { NextRequest, NextResponse } from "next/server";
export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const { input } = await req.json();
  let valid = true; let error = "";
  try { new RegExp(input); } catch (e) { valid = false; error = e instanceof Error ? e.message : "invalid regex"; }
  // crude ReDoS heuristic: nested quantifiers
  const redosRisk = /\\([^)]*[*+]\\)[*+]|\\.\\*.*\\.\\*|\\(.+\\+.+\\).+|\\([^)]*\\|[^)]*\\)\\+/.test(input);
  return NextResponse.json({ input, processed: { valid, error, redosRisk } });
}
"""

_YAML_PROCESS = _DEFAULT_PROCESS  # YAML parsing is heavy; let MiMo handle structure
_DNS_PROCESS = """import { NextRequest, NextResponse } from "next/server";
import { promises as dns } from "node:dns";
export const runtime = "nodejs";

async function resolve(name: string, type: "A" | "AAAA" | "MX" | "TXT" | "CNAME" | "CAA" | "NS") {
  try {
    if (type === "A") return await dns.resolve4(name);
    if (type === "AAAA") return await dns.resolve6(name);
    if (type === "MX") return await dns.resolveMx(name);
    if (type === "TXT") return await dns.resolveTxt(name);
    if (type === "CNAME") return await dns.resolveCname(name);
    if (type === "CAA") return await dns.resolveCaa(name);
    if (type === "NS") return await dns.resolveNs(name);
  } catch (e) {
    return null;
  }
}

export async function POST(req: NextRequest) {
  const { input } = await req.json();
  const domain = (input as string).trim().toLowerCase();
  const [a, aaaa, mx, txt, cname, caa, ns] = await Promise.all([
    resolve(domain, "A"), resolve(domain, "AAAA"), resolve(domain, "MX"),
    resolve(domain, "TXT"), resolve(domain, "CNAME"), resolve(domain, "CAA"), resolve(domain, "NS"),
  ]);
  const dmarc = await resolve(`_dmarc.${domain}`, "TXT");
  const spfTxt = (txt || []).find((r) => r.join("").toLowerCase().startsWith("v=spf1"));
  return NextResponse.json({
    input: domain,
    processed: { domain, a, aaaa, mx, txt, cname, caa, ns, dmarc, hasSpf: !!spfTxt, hasDmarc: !!dmarc },
  });
}
"""

_HEADERS_PROCESS = """import { NextRequest, NextResponse } from "next/server";
export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const { input } = await req.json();
  let url: URL;
  try { url = new URL((input as string).trim().startsWith("http") ? input : `https://${input}`); }
  catch { return NextResponse.json({ error: "invalid url" }, { status: 400 }); }
  try {
    const res = await fetch(url.toString(), { method: "GET", redirect: "follow" });
    const headers: Record<string, string> = {};
    res.headers.forEach((v, k) => { headers[k.toLowerCase()] = v; });
    const baseline = ["strict-transport-security", "content-security-policy", "x-frame-options",
      "x-content-type-options", "referrer-policy", "permissions-policy",
      "cross-origin-opener-policy", "cross-origin-resource-policy"];
    const present = baseline.filter((h) => headers[h] != null);
    return NextResponse.json({
      input: url.toString(), processed: { status: res.status, headers, baselinePresent: present, baselineMissing: baseline.filter((h) => !present.includes(h)) },
    });
  } catch (err) {
    return NextResponse.json({ error: err instanceof Error ? err.message : "fetch failed" }, { status: 502 });
  }
}
"""

_UUID_PROCESS = """import { NextRequest, NextResponse } from "next/server";
export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const { input } = await req.json();
  const u = (input as string).trim().replace(/[{}]/g, "").toLowerCase();
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(u)) {
    return NextResponse.json({ error: "not a UUID" }, { status: 400 });
  }
  const hex = u.replace(/-/g, "");
  const version = parseInt(hex[12], 16);
  let timestamp: string | null = null; let mac: string | null = null;
  if (version === 1) {
    const t = BigInt("0x" + hex.slice(13, 16) + hex.slice(8, 12) + hex.slice(0, 8));
    const epoch = Number((t - 122192928000000000n) / 10000n);
    timestamp = new Date(epoch).toISOString();
    mac = hex.slice(20).match(/../g)!.join(":");
  } else if (version === 7) {
    const t = parseInt(hex.slice(0, 12), 16);
    timestamp = new Date(t).toISOString();
  }
  return NextResponse.json({ input: u, processed: { version, hex, timestamp, mac } });
}
"""

_REDACT_PROCESS = """import { NextRequest, NextResponse } from "next/server";
export const runtime = "nodejs";

const PATTERNS: Array<[string, RegExp]> = [
  ["EMAIL", /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/g],
  ["PHONE", /(\\+?\\d{1,3}[\\s-]?)?\\(?\\d{3}\\)?[\\s.-]?\\d{3}[\\s.-]?\\d{4}/g],
  ["SSN", /\\b\\d{3}-\\d{2}-\\d{4}\\b/g],
  ["CARD", /\\b(?:\\d{4}[\\s-]?){3}\\d{4}\\b/g],
  ["IP", /\\b(?:\\d{1,3}\\.){3}\\d{1,3}\\b/g],
];

export async function POST(req: NextRequest) {
  const { input } = await req.json();
  const text = input as string;
  const detections: Array<{ category: string; original: string; placeholder: string }> = [];
  let redacted = text;
  const counters: Record<string, number> = {};
  for (const [cat, rx] of PATTERNS) {
    redacted = redacted.replace(rx, (m) => {
      counters[cat] = (counters[cat] || 0) + 1;
      const ph = `[${cat}_${counters[cat]}]`;
      detections.push({ category: cat, original: m, placeholder: ph });
      return ph;
    });
  }
  return NextResponse.json({ input: text, processed: { detections, redacted } });
}
"""

_PROCESS_HANDLERS = {
    "decode_jwt": _JWT_PROCESS,
    "analyze_regex": _REGEX_PROCESS,
    "analyze_yaml": _YAML_PROCESS,
    "scan_dns": _DNS_PROCESS,
    "audit_headers": _HEADERS_PROCESS,
    "decode_uuid": _UUID_PROCESS,
    "redact_pii": _REDACT_PROCESS,
}


_LICENSE = """MIT License

Copyright (c) 2026 XinnBlueBird

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
