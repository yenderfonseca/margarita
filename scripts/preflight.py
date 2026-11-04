#!/usr/bin/env python3
"""Margarita preflight: lint a Klaviyo email before it ships.

Checks: tag-based footer check, URL-only tags in href, en dashes and entities,
curly quotes, Klaviyo syntax balance, alt text, palette lock.

Usage:
  preflight.py --html email.html [--subject S]... [--preheader P]
               [--palette "#111111,#F5F1EA,#B5542E"] [--allow "#121212"]
               [--banned "word,phrase"] [--json]
  preflight.py contrast "#111111" "#F5F1EA"
  preflight.py --self-test

Exit code 1 when any FAIL is found. Stdlib only.
"""
import argparse
import html as htmllib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

FAIL, WARN = "FAIL", "WARN"

# Klaviyo legal tags (verified against help.klaviyo.com/hc/en-us/articles/4408802648731).
# Full-link forms render their own <a>; *_link forms are URL only and belong in href.
UNSUB = ("{% unsubscribe %}", "{% unsubscribe_link %}", "{% unsubscribe '")
PREFS = ("{% manage_preferences %}", "{% manage_preferences_link %}", "{% manage_preferences '")
WEBVIEW = ("{% web_view %}", "{% web_view_link %}", "{% web_view '")
FULL_LINK_IN_HREF = re.compile(r'href=["\']\s*\{%\s*(unsubscribe|manage_preferences|web_view)\s*(%\}|\')', re.I)

SPAM = ["free", "guarantee", "100%", "winner", "urgent", "act now", "limited time", "buy now",
        "click here", "risk-free", "risk free", "no obligation", "once in a lifetime", "order now",
        "cash", "cheap", "lowest price", "best price", "miracle", "amazing deal", "call now",
        "this isn't spam", "don't delete", "$$$"]

# Marketing filler from references/copy.md section 1 (warn only)
FILLER = ["elevate", "unlock", "discover the magic", "game-changer", "game changer", "curated just for you",
          "we're so excited", "look no further", "treat yourself", "must-have", "in today's world",
          "next level", "don't miss out", "best-in-class", "seamless"]

# lookbehind skips numeric entities like &#039; and &#160;
HEX_RE = re.compile(r'(?<![&\w])#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b')
RESERVED_TLD = re.compile(r'https?://[^/"\'\s]+\.(invalid|test|example|localhost)\b', re.I)
HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.I)
IMG_RE = re.compile(r'<img\b[^>]*>', re.I)


def norm_hex(h):
    h = h.lstrip("#").lower()
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return "#" + h


def contrast(a, b):
    def lum(h):
        h = norm_hex(h)[1:]
        rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        rgb = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
        return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def visible_text(content):
    t = re.sub(r'<(style|script)\b.*?</\1>', ' ', content, flags=re.S | re.I)
    t = re.sub(r'<!--.*?-->', ' ', t, flags=re.S)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'\{%.*?%\}|\{\{.*?\}\}', ' ', t, flags=re.S)
    return re.sub(r'\s+', ' ', htmllib.unescape(t)).strip()


def check_copy_line(kind, text, f):
    """Subject / preheader rules (the Margarita subject study)."""
    n = len(text)
    limit_fail, limit_warn = (60, 50) if kind == "subject" else (100, None)
    if n > limit_fail:
        f.append((FAIL, "B", f"{kind} is {n} chars (max {limit_fail}): {text!r}"))
    elif limit_warn and n > limit_warn:
        f.append((WARN, "B", f"{kind} is {n} chars (target 30-45, warn over {limit_warn}): {text!r}"))
    elif kind == "subject" and n < 20:
        f.append((WARN, "B", f"subject is only {n} chars (target 30-45): {text!r}"))
    if re.search(r'[–—]', text):
        f.append((FAIL, "A11", f"{kind} has an em or en dash: {text!r}"))
    if re.search(r'[‘’“”]', text):
        f.append((FAIL, "A11", f"{kind} has curly quotes: {text!r}"))
    if re.search(r'!{2,}|\?{2,}|!\?|\?!', text):
        f.append((FAIL, "B", f"{kind} stacks punctuation: {text!r}"))
    caps = re.findall(r"\b[A-Z]{3,}\b", text)
    if len(caps) > 1:
        f.append((WARN, "B", f"{kind} shouts ({', '.join(caps)}); one caps word at most"))
    if re.search(r'\{\{\s*(person\.)?first_name\s*\}\}', text):
        f.append((FAIL, "A13", f"{kind} uses a bare first_name tag; add |default:'...'"))
    low = text.lower()
    hits = [w for w in SPAM if re.search(r'(?<!\w)' + re.escape(w) + r'(?!\w)', low)]
    if hits:
        f.append((WARN, "S", f"{kind} spam-trigger words {hits}: keep only if a real offer backs them"))


def check_html(content, path=None, subjects=(), preheader=None, palette=None, allow=(), banned=()):
    f = []
    lower = content.lower()
    nocomment = re.sub(r'<!--(?!\[if).*?-->', '', content, flags=re.S)
    text = visible_text(content)

    # A1 legal footer: by Klaviyo tag, never by literal link text
    for name, forms in (("unsubscribe", UNSUB), ("manage preferences", PREFS), ("web view", WEBVIEW)):
        if not any(x in content for x in forms):
            f.append((FAIL, "A1", f"missing Klaviyo {name} tag ({' or '.join(forms[:2])})"))
    for m in FULL_LINK_IN_HREF.finditer(content):
        f.append((FAIL, "A1", f"{{% {m.group(1)} %}} renders a full link; inside href use {{% {m.group(1)}_link %}}"))

    # A2 sender identity and postal address
    if "organization.full_address" not in content and "organization.street_address" not in content:
        f.append((FAIL, "A2", "footer needs the postal address: {{ organization.full_address }}"))
    if "organization.name" not in content:
        f.append((WARN, "A2", "footer has no {{ organization.name }}"))

    # A3 placeholders (in copy and link targets)
    haystack = text.lower() + " " + " ".join(HREF_RE.findall(lower))
    for needle in ("lorem ipsum", "fixme", "your-brand.com", "example.com", "placeholder"):
        if re.search(r'(?<![\w-])' + re.escape(needle) + r'(?![\w-])', haystack):
            f.append((FAIL, "A3", f"placeholder text: {needle!r}"))
    # TODO only as a marker: "todo" is an ordinary word in Spanish and Portuguese ("TODO EL SABOR")
    if re.search(r'\bTODO\s*[:(]|\[\s*TODO\s*\]', text, re.I):
        f.append((FAIL, "A3", "placeholder text: 'TODO'"))
    if re.search(r'href=["\']#?["\']', content):
        f.append((FAIL, "A3", 'a link points nowhere (href="#" or empty)'))
    if re.search(r'<img[^>]+src=["\']\s*["\']', content, re.I):
        f.append((FAIL, "A3", "empty img src"))
    reserved = sorted(set(m.group(0) for m in RESERVED_TLD.finditer(content)))
    if reserved:
        f.append((WARN, "A3", f"reserved or unresolvable domain, replace before sending: {', '.join(reserved[:3])}"))

    # A4 unfilled builder tokens
    leaks = sorted(set(re.findall(r'\[\[[^\]]+\]\]|\{\{\s*[A-Z][A-Z0-9_]+\s*\}\}', content)))
    if leaks:
        f.append((FAIL, "A4", f"unfilled tokens: {', '.join(leaks[:8])}"))

    # A5 UTM on external links
    # judge the link's host, not its query string (utm_source=klaviyo is in every tagged link); fonts are not links
    hosts = r'klaviyo|facebook|instagram|tiktok|youtube|twitter|x\.com|pinterest|fonts\.googleapis|fonts\.gstatic'
    ext = [u for u in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\']', content, re.I) if u.startswith("http")
           and not re.search(hosts, urlparse(u).netloc, re.I)]
    missing = [u for u in ext if "utm_source=" not in u]
    if missing:
        f.append((WARN, "A5", f"{len(missing)}/{len(ext)} external links lack utm_source: {', '.join(missing[:3])}"))

    # A6 mobile, A7 dark mode, A8 Outlook
    if "width=device-width" not in lower:
        f.append((WARN, "A6", "no viewport meta"))
    if "@media" not in lower or "max-width" not in lower:
        f.append((WARN, "A6", "no mobile breakpoint"))
    if "min-height:48px" not in lower.replace(" ", ""):
        f.append((WARN, "A6", "no 48px touch-target rule"))
    if "prefers-color-scheme" not in lower and "data-ogsc" not in lower:
        f.append((WARN, "A7", "no dark-mode CSS"))
    if "<!--[if mso]>" not in content:
        f.append((WARN, "A8", "no MSO conditionals for Outlook"))

    # A9 size (Gmail clips at ~102 KB)
    kb = len(content.encode("utf-8")) / 1024
    if kb > 200:
        f.append((FAIL, "A9", f"HTML is {kb:.0f} KB (over 200)"))
    elif kb > 102:
        f.append((WARN, "A9", f"HTML is {kb:.0f} KB; Gmail clips around 102"))

    # A10 banned words (brand voice rules)
    for w in banned:
        if w and w.lower() in text.lower():
            f.append((FAIL, "A10", f"banned phrase: {w!r}"))

    # A11 house style: dashes and curly quotes, raw or as entities
    if re.search(r'[–—]|&[mn]dash;|&#821[12];|&#x201[34];', nocomment, re.I):
        f.append((FAIL, "A11", "em or en dash in the email (rewrite with a comma, colon or period)"))
    if re.search(r'[‘’“”]|&[lr][sd]quo;|&#821[6-9];|&#822[01];', nocomment, re.I):
        f.append((FAIL, "A11", "curly quotes in the email (use straight quotes)"))

    # A13 Klaviyo template syntax (unbalanced tags fail Klaviyo's parser)
    for open_, close in (("if", "endif"), ("for", "endfor")):
        o = len(re.findall(r'\{%\s*' + open_ + r'\b', content))
        c = len(re.findall(r'\{%\s*' + close + r'\s*%\}', content))
        if o != c:
            f.append((FAIL, "A13", f"{{% {open_} %}} x{o} but {{% {close} %}} x{c}"))
    if re.search(r'\*\|[A-Z_]+\|\*|%%[^%\s]+%%', content):
        f.append((FAIL, "A13", "non-Klaviyo merge syntax (*|TAG|* or %%tag%%); Klaviyo only parses {{ }} and {% %}"))
    # ponytail: "guarded" means any {% if first_name %} in the file, not per-tag scope
    guarded = re.search(r'\{%\s*if\s+(person\.)?first_name\s*%\}', content)
    if re.search(r'\{\{\s*(person\.)?first_name\s*\}\}', content) and not guarded:
        f.append((FAIL, "A13", "bare first_name tag; always add |default:'...'"))
    if "{% current_year %}" in content:
        f.append((FAIL, "A13", "{% current_year %} is not a documented Klaviyo tag; use {% today \"%Y\" as year %}{{ year }}"))

    # A14 images: alt text, and local files must exist for the import zip
    for tag in IMG_RE.findall(content):
        if not re.search(r'\balt=', tag, re.I):
            f.append((FAIL, "A14", f"img without alt: {tag[:90]}"))
        m = re.search(r'src=["\']([^"\']*)["\']', tag, re.I)
        src = m.group(1) if m else ""
        if src and not re.match(r'(https?:)?//|\{', src) and path is not None:
            if not (Path(path).parent / src).is_file():
                f.append((FAIL, "A14", f"local image not found next to the HTML: {src}"))
            else:
                f.append((WARN, "A14", f"local image {src}: ship it inside klaviyo-import.zip"))
    if len(IMG_RE.findall(content)) >= 2 and len(text) < 250:
        f.append((WARN, "A14", f"only {len(text)} chars of live text; with images off the email is nearly blank"))

    # A16 things email clients or Klaviyo strip or break
    for pat, msg in ((r'<svg\b', "inline SVG"), (r'position\s*:\s*absolute', "absolute positioning"),
                     (r'<script\b', "script"), (r'<form\b', "form"), (r'<iframe\b', "iframe"),
                     (r'<video\b', "video tag")):
        if re.search(pat, content, re.I):
            f.append((FAIL, "A16", f"{msg} is not email-safe"))

    # A17 palette lock: every color must come from the supplied palette
    if palette:
        ok = {norm_hex(c) for c in list(palette) + list(allow)}
        used = {norm_hex(m.group(0)) for m in HEX_RE.finditer(nocomment)}
        off = sorted(used - ok)
        if off:
            f.append((FAIL, "A17", f"colors outside the palette: {', '.join(off)}"))

    # C1/C3 one primary CTA (primary buttons are tables with class m-btn)
    btns = re.findall(r'<table[^>]*class=["\'][^"\']*\bm-btn\b.*?</table>', content, re.I | re.S)
    n_cta = len(btns)
    if n_cta == 0:
        f.append((FAIL, "C1", "no primary CTA (a table with class m-btn)"))
    elif n_cta > 1:
        f.append((FAIL, "C3", f"{n_cta} primary CTAs; one per email, the rest are text links"))
    for b in btns:
        outside_mso = re.sub(r'<!--\[if mso\]>.*?<!\[endif\]-->', '', b, flags=re.S)
        if not re.search(r'<a\s[^>]*href=', outside_mso, re.I):
            f.append((FAIL, "C1", "primary CTA has no HTML <a href> outside the Outlook VML (button invisible in most clients)"))

    # Body punctuation
    if re.search(r'!{2,}', text):
        f.append((FAIL, "B", "stacked exclamation points in body copy"))
    if text.count("!") > 2:
        f.append((WARN, "B", "more than 2 exclamation points in the body"))
    fill = [w for w in FILLER if re.search(r'(?<!\w)' + re.escape(w) + r'(?!\w)', text.lower())]
    if fill:
        f.append((WARN, "S", f"marketing filler {fill}: replace with a fact from the site"))

    for s in subjects:
        check_copy_line("subject", s, f)
    if preheader is not None:
        check_copy_line("preheader", preheader, f)
        for s in subjects:
            if s.strip() and s.strip().lower() in preheader.lower():
                f.append((FAIL, "B", "preheader repeats the subject; it should complete it"))
        if preheader not in content:
            f.append((WARN, "B", "preheader text not found in the hidden preheader div"))
    return f


def report(findings, path, as_json):
    status = "FAIL" if any(l == FAIL for l, _, _ in findings) else "PASS"
    if as_json:
        print(json.dumps({"file": str(path), "status": status,
                          "findings": [{"level": l, "code": c, "message": m} for l, c, m in findings]}))
    else:
        print(f"{status}  {path}  ({sum(l == FAIL for l, _, _ in findings)} fail, "
              f"{sum(l == WARN for l, _, _ in findings)} warn)")
        for l, c, m in findings:
            print(f"  {l:4} {c:4} {m}")
    return status


def self_test():
    here = Path(__file__).resolve().parent.parent
    good = (here / "assets" / "example.html").read_text(encoding="utf-8")
    pal = ["#1F2A24", "#F4EFE6", "#B5542E", "#FFFFFF", "#5C635E", "#E4DCCD"]  # example.spec.json palette
    subj, pre = ["Meet the Harbor Mug, thrown by hand"], "Glazed in batches of forty, in Maine."
    base = check_html(good, None, subj, pre, pal)
    assert not [x for x in base if x[0] == FAIL], f"example.html should pass: {base}"
    cta = good[good.find('<table role="presentation" cellspacing="0" cellpadding="0" border="0" class="m-btn"'):]
    mutations = {
        "A1": good.replace("{% unsubscribe_link %}", ""),
        "A2": good.replace("organization.full_address", "organization.nothing"),
        "A3": good.replace('href="https://', 'href="#" data-x="https://', 1),
        "A4": good.replace("</h1>", "[[headline]]</h1>", 1),
        "A11": good.replace("</h1>", " – now</h1>", 1),
        "A13": good.replace("</body>", "{% if x %}</body>", 1),
        "A14": re.sub(r'(<img\b[^>]*?)\salt="[^"]*"', r'\1', good, count=1),
        "A16": good.replace("</body>", "<svg></svg></body>", 1),
        "A17": good.replace("#B5542E", "#FF00AA", 1),
        "C3": good.replace("</body>", cta[:cta.find("</table>") + 8] + "</body>", 1),
    }
    for code, mutated in mutations.items():
        got = {c for l, c, _ in check_html(mutated, None, subj, pre, pal) if l == FAIL}
        assert code in got, f"mutation {code} not caught; got {got}"
    href_full = good.replace("{% manage_preferences_link %}", "{% manage_preferences %}")
    assert "A1" in {c for l, c, _ in check_html(href_full, None, subj, pre, pal) if l == FAIL}, "full-link tag in href"
    assert [x for x in check_html(good, None, ["x" * 61], pre, pal) if x[:2] == (FAIL, "B")], "61-char subject"
    assert [x for x in check_html(good, None, subj, "Meet the Harbor Mug, thrown by hand today", pal) if x[:2] == (FAIL, "B")], \
        "preheader repeating subject"
    ent = good.replace("</h1>", " it&#039;s&#160;here</h1>", 1)
    assert "A17" not in {c for l, c, _ in check_html(ent, None, subj, pre, pal) if l == FAIL}, "entity read as color"
    fails = lambda h: {c for l, c, _ in check_html(h, None, subj, pre, pal) if l == FAIL}
    assert "A3" not in fails(good.replace("</h1>", " TODO EL SABOR, todo aqu&iacute;</h1>", 1)), "Spanish 'todo' read as placeholder"
    assert "A3" in fails(good.replace("</h1>", " TODO: price</h1>", 1)), "TODO marker missed"
    assert round(contrast("#000000", "#FFFFFF"), 1) == 21.0
    print(f"self-test PASS ({len(mutations) + 3} mutations caught, example.html clean)")


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == "contrast":
        r = contrast(sys.argv[2], sys.argv[3])
        print(f"{r:.2f}:1  {'AA ok' if r >= 4.5 else 'AA large text only' if r >= 3 else 'FAIL'}")
        return 0
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--html", action="append", default=[])
    p.add_argument("--subject", action="append", default=[])
    p.add_argument("--preheader")
    p.add_argument("--palette", default="")
    p.add_argument("--allow", default="")
    p.add_argument("--banned", default="")
    p.add_argument("--json", action="store_true")
    p.add_argument("--self-test", action="store_true")
    a = p.parse_args()
    if a.self_test:
        self_test()
        return 0
    if not a.html:
        p.error("--html is required")
    split = lambda s: [x.strip() for x in s.split(",") if x.strip()]
    worst = "PASS"
    for h in a.html:
        content = Path(h).read_text(encoding="utf-8")
        fs = check_html(content, h, a.subject, a.preheader, split(a.palette), split(a.allow), split(a.banned))
        if report(fs, h, a.json) == "FAIL":
            worst = "FAIL"
    return 1 if worst == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
