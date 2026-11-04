#!/usr/bin/env python3
"""Margarita gallery: one page that shows every built email at desktop and phone width, plus popup mockups.

Usage: gallery.py DIR [--title "Preview"]

Finds every DIR/**/email.html (including build.py --styles previews in _styles/), and writes
DIR/gallery.html with each email in live frames at 600px and 375px, labeled by folder name, plus a
filter box. Open it in a browser (file://). Stdlib only.
"""
import html
import sys
from pathlib import Path

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>
<style>
:root{{--bg:#f4f2ee;--ink:#1d1d1b;--muted:#6b6a66;--card:#fff;--line:#e2dfd8}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151514;--ink:#eeece6;--muted:#a19f98;--card:#1f1f1d;--line:#33322f}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
header{{position:sticky;top:0;z-index:2;display:flex;gap:16px;align-items:center;flex-wrap:wrap;padding:14px 24px;
background:var(--bg);border-bottom:1px solid var(--line)}}
h1{{font-size:17px;margin:0;font-weight:650}} .count{{color:var(--muted)}}
input:not([type=checkbox]){{flex:1;min-width:200px;max-width:360px;padding:8px 12px;border:1px solid var(--line);border-radius:8px;
background:var(--card);color:var(--ink);font:inherit}}
label{{color:var(--muted);display:flex;gap:6px;align-items:center}}
main{{padding:24px;display:grid;gap:28px}}
section{{min-width:0;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px}}
section h2{{margin:0 0 4px;font-size:15px}} section p{{margin:0 0 12px;color:var(--muted);font-size:13px}}
.frames{{display:flex;gap:18px;overflow-x:auto;align-items:flex-start}}
iframe{{border:1px solid var(--line);border-radius:6px;background:#fff;flex:none;height:{height}px}}
.w600{{width:600px}} .w375{{width:375px}} body.phone-only .w600{{display:none}}
a{{color:inherit}}
</style></head><body>
<header><h1>{title}</h1><span class="count">{n} items</span>
<input id="q" placeholder="Filter by niche or style" aria-label="Filter">
<label><input type="checkbox" id="phone"> Phone only</label></header>
<main>{sections}</main>
<script>
const q=document.getElementById('q'),cards=[...document.querySelectorAll('section')];
q.addEventListener('input',()=>{{const v=q.value.toLowerCase();cards.forEach(c=>c.hidden=!c.dataset.k.includes(v));}});
document.getElementById('phone').addEventListener('change',e=>document.body.classList.toggle('phone-only',e.target.checked));
</script></body></html>"""


def main():
    a = sys.argv[1:]
    if a[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    if not a:
        sys.exit(__doc__)
    root = Path(a[0]).resolve()
    title = a[a.index("--title") + 1] if "--title" in a else "Margarita preview"
    # show the filled preview copy when the build wrote one (Klaviyo tags replaced by samples)
    emails = sorted(root.rglob("email.html"))
    sections = []
    for e in emails:
        shown = e.with_name("preview.html") if e.with_name("preview.html").is_file() else e
        rel = shown.relative_to(root).as_posix()
        name = e.parent.name
        meta = e.parent / "email.md"
        sub = ""
        if meta.is_file():
            lines = meta.read_text(encoding="utf-8").splitlines()
            sub = " · ".join(l.split(": ", 1)[-1] for l in lines if l.startswith("## Subject A") or l.startswith("- Theme"))
        sections.append(
            f'<section data-k="{html.escape(rel.lower())}"><h2>{html.escape(name)}</h2><p>{html.escape(sub)} · '
            f'<a href="{html.escape(rel)}">open</a></p><div class="frames">'
            f'<iframe class="w600" src="{html.escape(rel)}" loading="lazy" title="{html.escape(name)} desktop"></iframe>'
            f'<iframe class="w375" src="{html.escape(rel)}" loading="lazy" title="{html.escape(name)} phone"></iframe>'
            f'</div></section>')
    for m in sorted(root.rglob("popups/*/mockup.html")):
        rel = m.relative_to(root).as_posix()
        name = f"{m.parent.parent.parent.name} popup:\u00a0{m.parent.name}"
        sheet = m.with_name("build-sheet.md")
        link = f' · <a href="{html.escape(sheet.relative_to(root).as_posix())}">build sheet</a>' if sheet.is_file() else ""
        sections.append(f'<section data-k="{html.escape(rel.lower())} popup"><h2>{html.escape(name)}</h2><p>Klaviyo form mockup{link}</p>'
                        f'<iframe src="{html.escape(rel)}" loading="lazy" title="{html.escape(name)}" style="width:100%;height:860px;"></iframe></section>')
    out = root / "gallery.html"
    out.write_text(PAGE.format(title=html.escape(title), n=len(sections), height=1400, sections="\n".join(sections)),
                   encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
