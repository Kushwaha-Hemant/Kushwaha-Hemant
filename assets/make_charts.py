#!/usr/bin/env python3
"""
make_charts.py -- emit the profile's SVG charts.

    python make_charts.py

Design constraints these SVGs are built to:

* **Self-contained.** GitHub renders SVG inside an <img>, which blocks every
  external request. No web fonts, no external CSS, no scripts.
* **Theme-independent.** An <img> cannot see GitHub's light/dark setting, so
  rather than shipping two variants each chart is an opaque dark card that
  reads as deliberate on either theme.
* **No invented numbers.** The focus chart counts projects that actually use a
  technology. It never claims a proficiency percentage.
"""
from __future__ import annotations

from pathlib import Path

BG = "#0b1016"
CARD = "#0e151d"
LINE = "#1e2b38"
TEXT = "#e6edf3"
MUTED = "#8b9cae"
DIM = "#5b6b7c"
ACCENT = "#22d3ee"
ACCENT_DIM = "#164e5b"

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"

# (area, projects using it, verb, technologies)
# `projects` is a count out of the six public repositories -- a fact, not a
# self-assessment. `verb` is the honest register for that area.
FOCUS = [
    ("AI, LLMs & RAG",     3, "Building",     "OpenAI · LangChain · pgvector · ChromaDB"),
    ("Backend & APIs",     4, "Building",     "FastAPI · Spring Boot · Express · REST"),
    ("Databases",          4, "Working with", "PostgreSQL · pgvector · Prisma · SQLite"),
    ("Web & Frontend",     4, "Working with", "Next.js · React · TypeScript · Tailwind"),
    ("Infra & DevOps",     3, "Exploring",    "Docker · GitHub Actions · Cloudflare"),
    ("Android",            1, "Building",     "Kotlin · Jetpack Compose · Gradle"),
]
TOTAL_PROJECTS = 6

JOURNEY = [
    ("Programming",       "C++ · Java · Python"),
    ("Software Dev",      "OOP · DSA · Git"),
    ("Backend & APIs",    "REST · FastAPI · Spring"),
    ("Databases",         "SQL · PostgreSQL"),
    ("AI / ML",           "NLP · embeddings"),
    ("LLMs & RAG",        "retrieval · agents"),
    ("Docker & CI/CD",    "compose · Actions"),
    ("Cloud & Production","deploys · monitoring"),
]


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def header(w: int, h: int, title: str, subtitle: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" role="img" aria-label="{esc(title)}">',
        "<defs>",
        '  <linearGradient id="accentBar" x1="0" y1="0" x2="1" y2="0">',
        f'    <stop offset="0%" stop-color="{ACCENT}" stop-opacity="0.95"/>',
        f'    <stop offset="100%" stop-color="#6366f1" stop-opacity="0.9"/>',
        "  </linearGradient>",
        "</defs>",
        f'<rect width="{w}" height="{h}" rx="14" fill="{BG}"/>',
        f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="14" fill="none" stroke="{LINE}"/>',
        f'<rect x="0" y="0" width="{w}" height="3" rx="1.5" fill="url(#accentBar)"/>',
        f'<text x="28" y="42" font-family="{SANS}" font-size="17" font-weight="600" fill="{TEXT}">{esc(title)}</text>',
        f'<text x="28" y="63" font-family="{MONO}" font-size="11.5" fill="{MUTED}">{esc(subtitle)}</text>',
    ]


def build_focus() -> str:
    w, h = 900, 396
    row_h, top = 44, 96
    seg_w, seg_gap = 26, 5
    bar_x = 660
    out = header(w, h, "Engineering Focus",
                 "areas by number of shipped projects — not self-rated proficiency")
    out.append(f'<line x1="28" y1="78" x2="{w-28}" y2="78" stroke="{LINE}"/>')

    for i, (area, n, verb, tech) in enumerate(FOCUS):
        y = top + i * row_h
        out.append(
            f'<text x="28" y="{y}" font-family="{SANS}" font-size="13.5" '
            f'font-weight="600" fill="{TEXT}">{esc(area)}</text>'
        )
        out.append(
            f'<text x="28" y="{y+16}" font-family="{MONO}" font-size="10.5" '
            f'fill="{DIM}">{esc(tech)}</text>'
        )
        out.append(
            f'<text x="{bar_x-14}" y="{y}" text-anchor="end" font-family="{MONO}" '
            f'font-size="10.5" fill="{ACCENT}" opacity="0.85">{esc(verb.lower())}</text>'
        )
        for s in range(TOTAL_PROJECTS):
            x = bar_x + s * (seg_w + seg_gap)
            filled = s < n
            fill = ACCENT if filled else CARD
            stroke = "" if filled else f' stroke="{LINE}"'
            opacity = 0.92 if filled else 1
            out.append(
                f'<rect x="{x}" y="{y-11}" width="{seg_w}" height="9" rx="2.5" '
                f'fill="{fill}"{stroke} opacity="{opacity}"/>'
            )
        out.append(
            f'<text x="{bar_x + TOTAL_PROJECTS*(seg_w+seg_gap) + 4}" y="{y}" '
            f'font-family="{MONO}" font-size="10.5" fill="{MUTED}">{n}/6</text>'
        )
        if i < len(FOCUS) - 1:
            out.append(
                f'<line x1="28" y1="{y+26}" x2="{w-28}" y2="{y+26}" '
                f'stroke="{LINE}" opacity="0.5"/>'
            )

    out.append(
        f'<text x="28" y="{h-20}" font-family="{MONO}" font-size="10" fill="{DIM}">'
        f'each block = one public repository that genuinely uses the technology'
        f'</text>'
    )
    out.append("</svg>")
    return "\n".join(out)


def build_journey() -> str:
    w, h = 900, 250
    out = header(w, h, "Developer Journey",
                 "how the work has compounded — foundations first, production last")

    n = len(JOURNEY)
    # Labels are centre-anchored, so the end nodes need enough margin for half
    # a label. Too tight and "Cloud & Production" runs off the card.
    x0, x1 = 84, w - 92
    span = (x1 - x0) / (n - 1)
    y = 150

    out.append(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{LINE}" stroke-width="2"/>')
    out.append(
        f'<line x1="{x0}" y1="{y}" x2="{x0 + span*(n-1)}" y2="{y}" '
        f'stroke="url(#accentBar)" stroke-width="2" opacity="0.55"/>'
    )

    for i, (label, sub) in enumerate(JOURNEY):
        cx = x0 + i * span
        latest = i == n - 1
        r = 7 if latest else 5
        out.append(
            f'<circle cx="{cx:.1f}" cy="{y}" r="{r+4}" fill="{BG}"/>'
        )
        out.append(
            f'<circle cx="{cx:.1f}" cy="{y}" r="{r}" fill="{ACCENT if latest else CARD}" '
            f'stroke="{ACCENT}" stroke-width="{2 if latest else 1.4}" '
            f'opacity="{1 if latest else 0.85}"/>'
        )
        up = i % 2 == 0
        ty = y - 26 if up else y + 38
        sy = ty - 15 if up else ty + 14
        out.append(
            f'<text x="{cx:.1f}" y="{ty}" text-anchor="middle" font-family="{SANS}" '
            f'font-size="12" font-weight="600" fill="{TEXT}">{esc(label)}</text>'
        )
        out.append(
            f'<text x="{cx:.1f}" y="{sy}" text-anchor="middle" font-family="{MONO}" '
            f'font-size="9.5" fill="{DIM}">{esc(sub)}</text>'
        )
        out.append(
            f'<line x1="{cx:.1f}" y1="{y - (12 if up else -12)}" x2="{cx:.1f}" '
            f'y2="{y - (r if up else -r)}" stroke="{LINE}"/>'
        )

    out.append("</svg>")
    return "\n".join(out)


def main():
    here = Path(__file__).parent
    for name, svg in (("engineering-focus.svg", build_focus()),
                      ("developer-journey.svg", build_journey())):
        (here / name).write_text(svg, encoding="utf-8")
        print(f"  wrote {name}  ({len(svg):,} bytes)")


if __name__ == "__main__":
    main()
