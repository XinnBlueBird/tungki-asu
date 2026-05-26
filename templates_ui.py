"""UI templates per layout_variant.

Six variants — terminal, magazine, soc, brutalist, dashboard, editorial — render
the SAME concept data (input box, processed-data card, MiMo streaming output, FAQ, About)
with completely different visual languages.

Each render() returns (page_tsx, globals_css, layout_tsx).
"""
from __future__ import annotations


def render_layout(concept: dict) -> tuple[str, str, str]:
    variant = concept["layout_variant"]
    if variant == "terminal":
        return _terminal(concept)
    if variant == "magazine":
        return _magazine(concept)
    if variant == "soc":
        return _soc(concept)
    if variant == "brutalist":
        return _brutalist(concept)
    if variant == "dashboard":
        return _dashboard(concept)
    if variant == "editorial":
        return _editorial(concept)
    raise ValueError(f"unknown layout_variant: {variant}")


_BASE_LAYOUT_TSX = """import type {{ Metadata }} from "next";
import "./globals.css";

export const metadata: Metadata = {{
  title: "{name} — {tagline}",
  description: "{tagline}. Powered by MiMo v2.5 Pro.",
}};

export default function RootLayout({{ children }}: {{ children: React.ReactNode }}) {{
  return (
    <html lang="en">
      <body className="min-h-screen overflow-x-hidden">{{children}}</body>
    </html>
  );
}}
"""


def _layout(concept: dict) -> str:
    return _BASE_LAYOUT_TSX.format(name=concept["name"], tagline=concept["tagline"].replace('"', "'"))


# ── TERMINAL ──────────────────────────────────────────────────────────────────
def _terminal(c: dict) -> tuple[str, str, str]:
    accent = c["color_scheme"]
    css = f"""@import "tailwindcss";
:root {{
  --bg: #0a0e0a;
  --bg-2: #101510;
  --line: rgba(120, 200, 120, 0.15);
  --ink: #c8e6c9;
  --ink-soft: #6b9a6b;
  --accent: {accent};
}}
html, body {{ background: var(--bg); color: var(--ink); font-family: ui-monospace, "JetBrains Mono", "Fira Code", Menlo, monospace; }}
.font-mono {{ font-family: ui-monospace, "JetBrains Mono", "Fira Code", Menlo, monospace; }}
.font-sans {{ font-family: ui-sans-serif, system-ui, sans-serif; }}
.crt {{ background-image: repeating-linear-gradient(0deg, transparent 0, transparent 2px, rgba(120,200,120,0.025) 2px, rgba(120,200,120,0.025) 3px); }}
.glow {{ color: var(--accent); text-shadow: 0 0 6px {accent}55; }}
.btn-primary {{ background: var(--accent); color: #000; }}
.btn-primary:hover {{ filter: brightness(1.15); }}
.scrollbar-clean::-webkit-scrollbar {{ width: 6px; height: 6px; }}
.scrollbar-clean::-webkit-scrollbar-thumb {{ background: rgba(120,200,120,0.2); border-radius: 3px; }}
"""
    page = _generic_page(c, header_kind="terminal")
    return page, css, _layout(c)


# ── MAGAZINE ──────────────────────────────────────────────────────────────────
def _magazine(c: dict) -> tuple[str, str, str]:
    accent = c["color_scheme"]
    css = f"""@import "tailwindcss";
:root {{
  --bg: #f5f1e8;
  --bg-2: #ffffff;
  --line: rgba(20, 20, 20, 0.10);
  --ink: #1a1a1a;
  --ink-soft: #5a5a5a;
  --accent: {accent};
}}
html, body {{ background: var(--bg); color: var(--ink); font-family: ui-sans-serif, "Inter", system-ui, sans-serif; }}
.font-serif {{ font-family: ui-serif, "Iowan Old Style", Georgia, serif; font-feature-settings: "liga", "dlig"; }}
.font-mono {{ font-family: ui-monospace, "JetBrains Mono", Menlo, monospace; }}
.btn-primary {{ background: var(--ink); color: var(--bg); }}
.btn-primary:hover {{ filter: brightness(1.2); }}
.tag-accent {{ background: {accent}1a; color: {accent}; border: 1px solid {accent}40; }}
"""
    page = _generic_page(c, header_kind="magazine")
    return page, css, _layout(c)


# ── SOC (security ops) ────────────────────────────────────────────────────────
def _soc(c: dict) -> tuple[str, str, str]:
    accent = c["color_scheme"]
    css = f"""@import "tailwindcss";
:root {{
  --bg: #06080d;
  --bg-2: #0c1018;
  --line: rgba(140, 160, 200, 0.10);
  --line-strong: rgba(140, 160, 200, 0.25);
  --ink: #d6dee8;
  --ink-soft: #8a96aa;
  --accent: {accent};
}}
html, body {{ background: var(--bg); color: var(--ink); font-family: ui-sans-serif, "Inter", system-ui, sans-serif; }}
.font-mono {{ font-family: ui-monospace, "JetBrains Mono", Menlo, monospace; }}
.scanline {{ background-image: repeating-linear-gradient(0deg, transparent 0, transparent 2px, rgba(140,160,200,0.025) 2px, rgba(140,160,200,0.025) 3px); }}
.btn-primary {{ background: var(--accent); color: #000; font-weight: 600; }}
.btn-primary:hover {{ filter: brightness(1.1); }}
.dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: {accent}; box-shadow: 0 0 8px {accent}80; }}
.scrollbar-clean::-webkit-scrollbar {{ width: 6px; height: 6px; }}
.scrollbar-clean::-webkit-scrollbar-thumb {{ background: rgba(140,160,200,0.2); border-radius: 3px; }}
"""
    page = _generic_page(c, header_kind="soc")
    return page, css, _layout(c)


# ── BRUTALIST ─────────────────────────────────────────────────────────────────
def _brutalist(c: dict) -> tuple[str, str, str]:
    accent = c["color_scheme"]
    css = f"""@import "tailwindcss";
:root {{
  --bg: #f4f4f0;
  --bg-2: #ffffff;
  --ink: #0a0a0a;
  --line: #0a0a0a;
  --accent: {accent};
}}
html, body {{ background: var(--bg); color: var(--ink); font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; }}
.font-mono {{ font-family: "JetBrains Mono", ui-monospace, Menlo, monospace; }}
.brutal-border {{ border: 2px solid var(--ink); }}
.brutal-shadow {{ box-shadow: 6px 6px 0 0 var(--ink); }}
.btn-primary {{ background: var(--accent); color: var(--ink); border: 2px solid var(--ink); box-shadow: 4px 4px 0 0 var(--ink); }}
.btn-primary:hover {{ transform: translate(-1px, -1px); box-shadow: 5px 5px 0 0 var(--ink); }}
.btn-primary:active {{ transform: translate(2px, 2px); box-shadow: 2px 2px 0 0 var(--ink); }}
.tag-accent {{ background: var(--accent); color: var(--ink); border: 2px solid var(--ink); }}
"""
    page = _generic_page(c, header_kind="brutalist")
    return page, css, _layout(c)


# ── DASHBOARD ─────────────────────────────────────────────────────────────────
def _dashboard(c: dict) -> tuple[str, str, str]:
    accent = c["color_scheme"]
    css = f"""@import "tailwindcss";
:root {{
  --bg: #0f1419;
  --bg-2: #1a2028;
  --bg-3: #232b35;
  --line: rgba(180, 200, 220, 0.10);
  --ink: #e2e8f0;
  --ink-soft: #94a3b8;
  --accent: {accent};
}}
html, body {{ background: var(--bg); color: var(--ink); font-family: "Inter", ui-sans-serif, system-ui, sans-serif; }}
.font-mono {{ font-family: ui-monospace, "JetBrains Mono", Menlo, monospace; }}
.card {{ background: var(--bg-2); border: 1px solid var(--line); }}
.btn-primary {{ background: var(--accent); color: #000; font-weight: 600; }}
.btn-primary:hover {{ filter: brightness(1.1); }}
.kpi-accent {{ color: {accent}; }}
"""
    page = _generic_page(c, header_kind="dashboard")
    return page, css, _layout(c)


# ── EDITORIAL ─────────────────────────────────────────────────────────────────
def _editorial(c: dict) -> tuple[str, str, str]:
    accent = c["color_scheme"]
    css = f"""@import "tailwindcss";
:root {{
  --bg: #fafaf8;
  --bg-2: #ffffff;
  --ink: #1a1a1a;
  --ink-soft: #4a4a4a;
  --line: rgba(20, 20, 20, 0.10);
  --accent: {accent};
}}
html, body {{ background: var(--bg); color: var(--ink); font-family: "Charter", ui-serif, "Iowan Old Style", Georgia, serif; }}
.font-sans {{ font-family: "Inter", ui-sans-serif, system-ui, sans-serif; }}
.font-mono {{ font-family: ui-monospace, "JetBrains Mono", Menlo, monospace; }}
.btn-primary {{ background: var(--ink); color: var(--bg); font-family: "Inter", system-ui, sans-serif; font-weight: 500; }}
.btn-primary:hover {{ filter: brightness(1.2); }}
.dropcap::first-letter {{ float: left; font-size: 4.5em; line-height: 0.85; padding-right: 8px; padding-top: 4px; color: var(--accent); font-weight: 700; }}
"""
    page = _generic_page(c, header_kind="editorial")
    return page, css, _layout(c)


# ── GENERIC PAGE TEMPLATE (keys interpolated per concept) ─────────────────────
def _generic_page(c: dict, header_kind: str) -> str:
    name = c["name"]
    tagline = c["tagline"]
    domain = c["domain"]
    problem = c["problem_statement"].replace("`", "\\`")
    input_label = c["input_label"]
    sample = c["sample_input"].replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    sections = ", ".join(f'"{s}"' for s in c["output_sections"])
    sections_human = " / ".join(c["output_sections"])

    header = _HEADER_BY_KIND[header_kind].format(name=name, tagline=tagline)

    page = _PAGE_TPL.format(
        name=name, tagline=tagline, domain=domain, problem=problem,
        input_label=input_label, sample=sample, sections=sections, header=header,
    )
    # post-format: replace the SECTIONS-human marker with the resolved plain text
    # (was a JS template literal `${{SECTIONS.join(" / ")}}` but inner double-quotes
    # broke the outer FAQ string — pre-resolve to plain text to avoid syntax errors)
    page = page.replace("__SECTIONS_HUMAN__", sections_human)
    return page


_HEADER_BY_KIND = {
    "terminal": """<header className="border-b border-[var(--line)] sticky top-0 bg-[var(--bg)]/90 backdrop-blur z-20">
        <div className="max-w-6xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="glow text-sm font-mono">$</span>
            <span className="font-mono text-sm font-medium">{name}</span>
            <span className="text-[10px] text-[var(--ink-soft)] font-mono uppercase tracking-widest hidden md:inline">v1 · ready</span>
          </div>
          <span className="hidden md:inline text-[10px] font-mono text-[var(--ink-soft)] uppercase tracking-widest">// powered by MiMo v2.5 Pro</span>
        </div>
      </header>""",
    "magazine": """<header className="border-b border-[var(--line)] sticky top-0 bg-[var(--bg)]/90 backdrop-blur z-20">
        <div className="max-w-6xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="font-serif text-xl leading-none">{name}</div>
            <div className="text-[11px] font-mono text-[var(--ink-soft)] tracking-widest uppercase hidden md:inline">— {tagline}</div>
          </div>
          <span className="hidden md:inline text-[11px] tag-accent font-mono px-2 py-0.5 rounded-full">MiMo v2.5 Pro</span>
        </div>
      </header>""",
    "soc": """<header className="border-b border-[var(--line)] sticky top-0 bg-[var(--bg)]/90 backdrop-blur z-20">
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <span className="dot" />
            <span className="text-sm font-semibold">{name}</span>
            <span className="hidden md:inline text-[10px] tracking-[0.22em] uppercase font-mono text-[var(--ink-soft)]">console online</span>
          </div>
          <span className="hidden md:inline text-[10px] font-mono text-[var(--ink-soft)] tracking-widest uppercase">powered by MiMo v2.5 Pro</span>
        </div>
      </header>""",
    "brutalist": """<header className="border-b-2 border-[var(--ink)] sticky top-0 bg-[var(--bg)] z-20">
        <div className="max-w-6xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between gap-4">
          <div className="font-mono font-bold text-lg uppercase">{name}</div>
          <span className="hidden md:inline text-[11px] font-mono tag-accent px-2 py-0.5 uppercase">MiMo v2.5 Pro</span>
        </div>
      </header>""",
    "dashboard": """<header className="border-b border-[var(--line)] sticky top-0 bg-[var(--bg)]/90 backdrop-blur z-20">
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded bg-[var(--bg-3)] grid place-items-center text-[12px] kpi-accent font-bold font-mono">·</div>
            <span className="font-semibold text-sm">{name}</span>
          </div>
          <span className="hidden md:inline text-[10px] font-mono text-[var(--ink-soft)] uppercase tracking-widest">MiMo v2.5 Pro</span>
        </div>
      </header>""",
    "editorial": """<header className="border-b border-[var(--line)] sticky top-0 bg-[var(--bg)]/90 backdrop-blur z-20">
        <div className="max-w-5xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-baseline gap-3">
            <div className="text-xl font-bold">{name}</div>
            <div className="text-[11px] font-sans font-medium text-[var(--ink-soft)] tracking-widest uppercase hidden md:inline">{tagline}</div>
          </div>
          <span className="hidden md:inline text-[11px] font-sans text-[var(--ink-soft)] tracking-widest uppercase">MiMo v2.5 Pro</span>
        </div>
      </header>""",
}


_PAGE_TPL = """\"use client\";

import {{ useState }} from "react";

const SAMPLE = `{sample}`;
const SECTIONS = [{sections}];

export default function Home() {{
  const [input, setInput] = useState("");
  const [processed, setProcessed] = useState<unknown>(null);
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run() {{
    if (!input.trim()) return;
    setLoading(true); setError(""); setProcessed(null); setOutput("");
    try {{
      const proc = await fetch("/api/process", {{
        method: "POST", headers: {{ "content-type": "application/json" }},
        body: JSON.stringify({{ input }}),
      }});
      const procJson = await proc.json();
      if (!proc.ok) {{ setError(procJson.error || "process failed"); setLoading(false); return; }}
      setProcessed(procJson.processed);
      const ana = await fetch("/api/analyze", {{
        method: "POST", headers: {{ "content-type": "application/json" }},
        body: JSON.stringify({{ input, processed: procJson.processed }}),
      }});
      if (!ana.ok || !ana.body) {{ setError(`analyze ${{ana.status}}`); setLoading(false); return; }}
      const reader = ana.body.getReader();
      const dec = new TextDecoder(); let buf = "";
      while (true) {{
        const {{ done, value }} = await reader.read();
        if (done) break;
        buf += dec.decode(value, {{ stream: true }});
        const lines = buf.split("\\n"); buf = lines.pop() || "";
        for (const line of lines) {{
          if (!line.startsWith("data:")) continue;
          const p = line.slice(5).trim();
          if (!p || p === "[DONE]") continue;
          try {{
            const j = JSON.parse(p);
            if (j.chunk) setOutput((s) => s + j.chunk);
            if (j.error) setError(j.error);
          }} catch {{ /* skip */ }}
        }}
      }}
    }} catch (e) {{
      setError(e instanceof Error ? e.message : "failed");
    }} finally {{ setLoading(false); }}
  }}

  return (
    <main className="min-h-screen overflow-x-hidden">
      {header}
      <section className="max-w-6xl mx-auto px-4 md:px-6 pt-10 md:pt-16 pb-8">
        <div className="text-[11px] uppercase tracking-[0.22em] text-[var(--ink-soft)] font-mono">{tagline}</div>
        <h1 className="text-3xl md:text-5xl font-bold leading-[1.05] mt-3 max-w-3xl">{name}.</h1>
        <p className="text-[15px] md:text-base mt-4 max-w-prose leading-relaxed">{domain}</p>

        <div className="mt-8 grid grid-cols-1 lg:grid-cols-[1.1fr_1fr] gap-6 items-start">
          <div className="space-y-3">
            <div className="text-[11px] tracking-[0.22em] uppercase font-mono text-[var(--ink-soft)]">{input_label}</div>
            <textarea
              value={{input}}
              onChange={{(e) => setInput(e.target.value)}}
              placeholder={{SAMPLE}}
              rows={{8}}
              className="w-full p-3 bg-[var(--bg-2)] border border-[var(--line)] rounded-md font-mono text-[12.5px] focus:outline-none focus:border-[var(--accent)] scrollbar-clean min-h-[180px]"
            />
            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={{run}} disabled={{loading || !input.trim()}}
                className="btn-primary px-4 py-2 rounded-md text-sm cursor-pointer disabled:opacity-50"
              >
                {{loading ? "Running…" : "Run analysis"}}
              </button>
              <button
                onClick={{() => setInput(SAMPLE)}} type="button"
                className="px-3 py-2 text-[12px] font-mono text-[var(--ink-soft)] hover:text-[var(--accent)] cursor-pointer"
              >
                ↪ insert sample
              </button>
              {{error && <span className="text-red-500 text-[12px] font-mono">! {{error}}</span>}}
            </div>
          </div>

          <div className="bg-[var(--bg-2)] rounded-md border border-[var(--line)]">
            <div className="px-4 py-3 border-b border-[var(--line)] flex items-center justify-between">
              <span className="text-[11px] tracking-[0.22em] uppercase font-mono text-[var(--ink-soft)]">analysis output</span>
              <span className="text-[10px] font-mono text-[var(--ink-soft)]">{{loading ? "streaming" : output ? "done" : "idle"}}</span>
            </div>
            <div className="p-4 min-h-[260px] max-h-[480px] overflow-auto font-mono text-[12.5px] leading-relaxed whitespace-pre-wrap scrollbar-clean">
              {{!output && !loading && <span className="opacity-50 italic font-sans">Output will stream here. Click "Run analysis".</span>}}
              {{output}}
              {{loading && !output && <span className="opacity-50">…</span>}}
            </div>
          </div>
        </div>

        {{processed != null && (
          <details className="mt-6 bg-[var(--bg-2)] rounded-md border border-[var(--line)]">
            <summary className="cursor-pointer px-4 py-2.5 text-[12px] tracking-[0.22em] uppercase font-mono text-[var(--ink-soft)] hover:text-[var(--accent)]">processed payload (raw)</summary>
            <pre className="px-4 pb-4 text-[11.5px] font-mono whitespace-pre-wrap break-all scrollbar-clean overflow-auto">{{JSON.stringify(processed, null, 2)}}</pre>
          </details>
        )}}
      </section>

      <FAQSection />
      <AboutSection />
      <Footer />
    </main>
  );
}}

function FAQSection() {{
  const items = [
    {{ q: "Does {name} store my input?", a: "No. Input is sent to the server, processed in memory, streamed back, and discarded. There is no database, no logging, no analytics tracking." }},
    {{ q: "What does the MiMo layer add?", a: "The local /api/process route extracts structured data deterministically. MiMo v2.5 Pro then turns that structured data into the __SECTIONS_HUMAN__ prose output. You get both layers — raw JSON in the collapsible panel, prose in the main output." }},
    {{ q: "Can I run this offline?", a: "The /api/process route runs entirely in Node and works offline. Only /api/analyze (the prose layer) needs the MiMo Token Plan endpoint. If you don't set MIMO_API_KEY, the tool still functions — you just won't get the prose layer." }},
    {{ q: "How accurate is the MiMo output?", a: "MiMo v2.5 Pro is a reasoning-class model with chain-of-thought routing. Output is deterministic when the local /api/process layer hands it structured input. For critical decisions, treat output as a draft, not a verdict." }},
  ];
  return (
    <section className="max-w-6xl mx-auto px-4 md:px-6 py-12 border-t border-[var(--line)] mt-12">
      <div className="text-[11px] uppercase tracking-[0.22em] text-[var(--ink-soft)] font-mono">FAQ</div>
      <h2 className="text-2xl md:text-3xl font-bold mt-2">Operational questions, briefly answered.</h2>
      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-x-10 gap-y-6">
        {{items.map((it) => (
          <div key={{it.q}}>
            <div className="text-[14.5px] font-medium">{{it.q}}</div>
            <div className="text-[13px] text-[var(--ink-soft)] mt-1.5 leading-relaxed">{{it.a}}</div>
          </div>
        ))}}
      </div>
    </section>
  );
}}

function AboutSection() {{
  return (
    <section className="max-w-6xl mx-auto px-4 md:px-6 py-12 border-t border-[var(--line)]">
      <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-8">
        <div>
          <div className="text-[11px] uppercase tracking-[0.22em] text-[var(--ink-soft)] font-mono">About</div>
          <div className="text-2xl md:text-3xl font-bold mt-2">Why this exists.</div>
        </div>
        <div className="text-[14px] leading-relaxed text-[var(--ink-soft)] space-y-4">
          <p>{problem}</p>
          <p>{name} ships as a single Next.js app — local processing in /api/process, streaming MiMo prose in /api/analyze. No DB, no auth, no telemetry. Your input never leaves the request.</p>
        </div>
      </div>
    </section>
  );
}}

function Footer() {{
  return (
    <footer className="border-t border-[var(--line)] mt-12">
      <div className="max-w-6xl mx-auto px-4 md:px-6 py-6 flex items-center justify-between gap-4 flex-wrap text-[11px] text-[var(--ink-soft)] font-mono">
        <div>{name} · MIT</div>
        <div className="flex items-center gap-3">
          <span className="px-2 py-0.5 rounded-full text-[10px]" style={{{{background: "var(--accent)20", color: "var(--accent)", border: "1px solid var(--accent)40"}}}}>Powered by MiMo v2.5 Pro</span>
        </div>
      </div>
    </footer>
  );
}}
"""

# (no post-replace needed — the marker is resolved per-call inside _generic_page)
