"""Sample concept pool for TungkiAsu — TEMPLATE ONLY.

This file ships 5 example concepts so you can see the shape. Build your own
pool in `concepts.py` (gitignored). The full curated 115-concept pool is NOT
distributed — that's the operator's edge.

Each concept is a fully-specified project. Picking flow:
1. Filter pool to exclude concept_kinds already used (from used_concepts table)
2. Random shuffle the remainder
3. Pick first; rotate layout_variant relative to last 3 used

Each concept ships:
- slug, name, tagline (for repo + UI)
- concept_kind (burn tracker — never reuse the same kind)
- domain (one-liner about WHAT it does)
- problem_statement (~3 sentences for README "Why" section)
- layout_variant (terminal | magazine | soc | brutalist | dashboard | editorial)
- color_scheme (accent color CSS hex)
- api_kind (analyze | scan | inspect | generate)
- system_prompt (MiMo instructions for the /api/analyze layer)
- sample_input (placeholder text for the input field)
- input_label (form input label)
- output_sections (list of section names MiMo emits)
"""
from __future__ import annotations

CONCEPTS = [
    {
        "slug": "tokenflame",
        "name": "TokenFlame",
        "tagline": "JWT inspector & forensic analyzer",
        "concept_kind": "jwt_inspector",
        "layout_variant": "soc",
        "color_scheme": "#f97316",
        "domain": "Decode any JWT, validate signature, audit claims, surface security issues",
        "problem_statement": "Half the auth bugs in production come from JWTs with sloppy claims, missing audience checks, or accidentally-shared secrets. Generic decoders just split the payload. TokenFlame audits 12 claim categories, flags weak algorithms (none, HS256 with short keys), and explains every kid/jwks/aud issue in plain English.",
        "input_label": "Paste any JWT",
        "sample_input": "eyJhbG...sw5c",
        "system_prompt": "You are TokenFlame, a JWT forensic analyst. Audit the provided token: header algorithm, claim presence (iss, aud, sub, exp, iat, nbf, jti), expiry status, alg-confusion vulnerability, weak HMAC indicators, and registered-claim correctness. Output: VERDICT line, then numbered FINDINGS with claim references, then RECOMMENDED FIXES. SOC tone, terse, finding-coded.",
        "api_kind": "decode_jwt",
        "output_sections": ["VERDICT", "FINDINGS", "FIXES"],
    },
    {
        "slug": "regexsage",
        "name": "RegexSage",
        "tagline": "Explain & test regex patterns",
        "concept_kind": "regex_tutor",
        "layout_variant": "terminal",
        "color_scheme": "#22c55e",
        "domain": "Paste a regex, get a token-by-token explanation plus a generated test corpus",
        "problem_statement": "Regex maintained by someone who left the company is the worst kind of legacy code. RegexSage walks the pattern token-by-token in plain English, generates a synthetic test corpus that probes edge cases (greedy vs lazy, anchors, character classes), and warns about catastrophic-backtracking shapes.",
        "input_label": "Paste any regex pattern",
        "sample_input": "^([a-z0-9._%+-]+)@([a-z0-9.-]+\\\\.[a-z]{2,})$",
        "system_prompt": "You are RegexSage. Decompose the regex token-by-token, explain each anchor / class / quantifier in plain English, identify ReDoS / catastrophic-backtracking risk, and generate 8 test strings (mix of expected matches and edge-case non-matches). Output sections: BREAKDOWN (numbered tokens), RISK (one line: low/medium/high + why), TEST CORPUS (numbered list, each string with expected match Y/N).",
        "api_kind": "analyze_regex",
        "output_sections": ["BREAKDOWN", "RISK", "TEST CORPUS"],
    },
    {
        "slug": "yamllens",
        "name": "YamlLens",
        "tagline": "YAML linter & schema critic",
        "concept_kind": "yaml_linter",
        "layout_variant": "editorial",
        "color_scheme": "#0ea5e9",
        "domain": "Paste any YAML document, get structural critique + schema inference + risk flags",
        "problem_statement": "YAML accepts everything and breaks subtly. YamlLens parses your document, infers the implicit schema, flags type ambiguity (yes/no booleans, octal numbers, quoted vs unquoted strings), surfaces duplicate keys silently overriding earlier ones, and proposes a stricter shape.",
        "input_label": "Paste YAML",
        "sample_input": "name: app\nversion: 1.0\nflags:\n  - debug: yes\n  - prod: no",
        "system_prompt": "You are YamlLens. Critique YAML: STRUCTURAL ISSUES (duplicate keys, ambiguous booleans, indentation traps), INFERRED SCHEMA, RECOMMENDED REWRITE. Editorial prose tone, with rationale per critique.",
        "api_kind": "analyze_yaml",
        "output_sections": ["STRUCTURAL ISSUES", "INFERRED SCHEMA", "REWRITE"],
    },
    {
        "slug": "dnstrace",
        "name": "DnsTrace",
        "tagline": "Walk DNS resolution chain & flag misconfigs",
        "concept_kind": "dns_tracer",
        "layout_variant": "dashboard",
        "color_scheme": "#3b82f6",
        "domain": "Given a hostname or dig output, trace the resolution chain, identify CAA/SPF/DMARC gaps, surface recursive lookup risks",
        "problem_statement": "DNS is the most-blamed and least-understood layer. DnsTrace walks the resolution chain step-by-step (root → TLD → authoritative), interprets CAA/SPF/DMARC/MX records, identifies wildcard fallthrough risks, and recommends hardening per RFC 7208/7489.",
        "input_label": "Paste hostname or dig output",
        "sample_input": "example.com\n;; ANSWER SECTION:\nexample.com. 300 IN A 93.184.216.34",
        "system_prompt": "You are DnsTrace. Walk DNS: RESOLUTION CHAIN (numbered hops), RECORD AUDIT (per-type findings), MISCONFIGS, HARDENING. Dashboard tone, percentages where relevant.",
        "api_kind": "trace_dns",
        "output_sections": ["RESOLUTION CHAIN", "RECORDS", "MISCONFIGS", "HARDENING"],
    },
    {
        "slug": "envscout",
        "name": "EnvScout",
        "tagline": "Detect leaked secrets in env dumps",
        "concept_kind": "secret_scanner",
        "layout_variant": "soc",
        "color_scheme": "#dc2626",
        "domain": "Paste a .env, terraform output, or config dump — flag every secret-shaped line",
        "problem_statement": "Secrets get committed by accident every day. EnvScout takes any text dump (env files, terraform output, JSON config) and flags each line with secret-shaped content: AWS keys, GitHub tokens, JWT signatures, Stripe keys, base64-encoded credentials. Each flag includes provider hint and rotation procedure.",
        "input_label": "Paste env / config dump",
        "sample_input": "AWS_KEY=AKIAIOSFODNN7EXAMPLE\nDB_PASSWORD=hunter2",
        "system_prompt": "You are EnvScout. Scan dump for secrets: SECRETS (line, type, confidence), PROVIDER HINTS (which service issued each shape), ROTATION ORDER (which to revoke first based on blast radius). SOC tone, finding-coded.",
        "api_kind": "scan_secrets",
        "output_sections": ["SECRETS", "PROVIDERS", "ROTATION"],
    },
]


def find_concept(slug: str) -> dict | None:
    for c in CONCEPTS:
        if c["slug"] == slug:
            return c
    return None


def pick_unused(burned_kinds: set[str], burned_slugs: set[str], recent_layouts: list[str]) -> dict | None:
    """Pick a concept whose kind hasn't been burned, preferring layouts unused in last N."""
    import random
    available = [c for c in CONCEPTS if c["concept_kind"] not in burned_kinds and c["slug"] not in burned_slugs]
    if not available:
        return None
    # prefer concepts whose layout_variant isn't in recent_layouts
    fresh_layout = [c for c in available if c["layout_variant"] not in recent_layouts[-3:]]
    pool = fresh_layout if fresh_layout else available
    random.shuffle(pool)
    return pool[0]
