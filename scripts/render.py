#!/usr/bin/env python3
"""Margarita render check: screenshots + measured layout checks for one email.

Usage: render.py email.html [--out DIR]

Writes render-680.png (desktop: 600px shell + gutter, above the 620px breakpoint),
render-375.png (phone), render-320.png (small phone) and render-375-images-off.png (every <img> swapped for its
styled alt text, the way blocking clients show it) and render-375-dark.png (prefers-color-scheme: dark;
fails any text under 3:1 against its real background). Prints a JSON summary; exit 1 on
horizontal overflow, orphan words, broken images or a primary button under 44px.

Needs Playwright for Python. Uses Playwright's Chromium, else the installed Chrome.
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

# Orphans: a text block that wraps and leaves exactly one word on its last line.
MEASURE_JS = r"""() => {
  const sel = 'h1,h2,h3,p,td.m-chip,table.m-btn a';
  const orphans = [];
  for (const el of document.querySelectorAll(sel)) {
    const text = el.innerText.trim();
    // two words (one per line is balanced) and raw Klaviyo tags (one name once rendered) cannot orphan
    if (!text || text.length > 320 || el.closest('[style*="display:none"]') || /\{\{|\{%/.test(text) || text.split(/\s+/).length < 3) continue;
    const tops = [];
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let n; (n = walker.nextNode());) {
      const re = /\S+/g; let m;
      while ((m = re.exec(n.data))) {
        const r = document.createRange(); r.setStart(n, m.index); r.setEnd(n, m.index + m[0].length);
        const b = r.getBoundingClientRect();
        if (b.width) tops.push([Math.round(b.top), m[0]]);
      }
    }
    const lines = [...new Set(tops.map(t => t[0]))];
    if (lines.length > 1) {
      const last = tops.filter(t => t[0] === lines[lines.length - 1]);
      if (last.length === 1) orphans.push({tag: el.tagName.toLowerCase(), word: last[0][1], text: text.slice(0, 80)});
    }
  }
  // text pushed past its own box (overlapping neighbours) even when the page itself does not overflow
  const clipped = [...document.querySelectorAll('p,h1,h2,h3,td.m-chip,a')].filter(e => {
    const r = e.getBoundingClientRect(); return r.width && e.scrollWidth > e.clientWidth + 2 && getComputedStyle(e).display !== 'inline';
  }).map(e => e.innerText.trim().slice(0, 60));
  // images: distortion (rendered shape vs source shape), 2x sharpness, tall heroes, uneven grid rows
  const distorted = [], image_warnings = [];
  for (const i of document.images) {
    const b = i.getBoundingClientRect();
    if (!i.naturalWidth || !b.width || !b.height) continue;
    const src = (i.getAttribute('src') || '').split('/').pop().slice(0, 50);
    const want = i.naturalWidth / i.naturalHeight, got = b.width / b.height;
    if (Math.abs(got - want) / want > 0.08) distorted.push(`${src} ${i.naturalWidth}x${i.naturalHeight} shown ${Math.round(b.width)}x${Math.round(b.height)}`);
    if (i.naturalWidth < b.width * 1.9) image_warnings.push(`${src} is ${i.naturalWidth}px for a ${Math.round(b.width)}px slot (soft at 2x)`);
    if (b.width >= 560 && b.height > b.width * 1.3) image_warnings.push(`${src} is a tall hero (${Math.round(b.height)}px) that pushes the copy below the fold`);
  }
  for (const tr of document.querySelectorAll('tr')) {
    const imgs = [...tr.querySelectorAll(':scope > td img')].filter(i => i.getBoundingClientRect().height);
    const hs = imgs.map(i => Math.round(i.getBoundingClientRect().height));
    if (hs.length > 1 && Math.max(...hs) - Math.min(...hs) > 4 && new Set(imgs.map(i => Math.round(i.getBoundingClientRect().top))).size === 1)
      image_warnings.push(`row images differ in height (${hs.join(' / ')}px): crop them to one ratio`);
  }
  const btn = document.querySelector('table.m-btn a[href]');
  const box = btn ? btn.getBoundingClientRect() : null;
  return {
    overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
    orphans,
    clipped,
    distorted,
    image_warnings: [...new Set(image_warnings)],
    broken_images: [...document.images].filter(i => i.complete && !i.naturalWidth && i.src).map(i => i.getAttribute('src')),
    button_height: box && box.width ? Math.round(box.height) : 0,
  };
}"""

# Dark mode: every visible text element must keep 3:1 against the background it actually sits on.
DARK_JS = r"""() => {
  const rgb = s => { const m = s.match(/[\d.]+/g); return m ? m.slice(0, 4).map(Number) : [0, 0, 0, 0]; };
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const bgOf = el => { for (let e = el; e; e = e.parentElement) { const c = rgb(getComputedStyle(e).backgroundColor); if (c.length < 4 || c[3] > 0) return c; } return [255, 255, 255]; };
  const lost = [];
  for (const el of document.querySelectorAll('h1,h2,h3,p,a,span,td')) {
    const own = [...el.childNodes].some(n => n.nodeType === 3 && n.data.trim());
    if (!own || !el.getBoundingClientRect().width) continue;
    const a = lum(rgb(getComputedStyle(el).color)), b = lum(bgOf(el));
    const ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    if (ratio < 3) lost.push(`${el.tagName.toLowerCase()} "${el.textContent.trim().slice(0, 40)}" ${ratio.toFixed(2)}:1`);
  }
  return lost;
}"""

IMAGES_OFF_JS = r"""() => {
  for (const img of [...document.images]) {
    const s = document.createElement('span');
    s.textContent = img.alt;
    s.setAttribute('style', img.getAttribute('style') || '');
    s.style.display = 'block'; s.style.height = 'auto'; s.style.padding = img.alt ? '12px 0' : '0';
    img.replaceWith(s);
  }
}"""


def launch(p):
    try:
        return p.chromium.launch()
    except Exception:
        return p.chromium.launch(channel="chrome")


def main():
    args = sys.argv[1:]
    if args[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    if not args:
        sys.exit(__doc__)
    html = Path(args[0]).resolve()
    out = Path(args[args.index("--out") + 1]) if "--out" in args else html.parent
    out.mkdir(parents=True, exist_ok=True)
    report, errors = {"file": str(html), "checks": []}, []
    with sync_playwright() as p:
        browser = launch(p)
        for width, images_off in ((680, False), (375, False), (320, False), (375, True)):
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.on("console", lambda m: m.type == "error" and errors.append(m.text))
            page.goto(html.as_uri(), wait_until="networkidle")
            if images_off:
                page.evaluate(IMAGES_OFF_JS)
            name = f"render-{width}{'-images-off' if images_off else ''}.png"
            page.screenshot(path=str(out / name), full_page=True)
            r = page.evaluate(MEASURE_JS)
            r.update(width=width, images_off=images_off, screenshot=str(out / name))
            report["checks"].append(r)
            page.close()
        dark = browser.new_page(viewport={"width": 375, "height": 900}, color_scheme="dark")
        dark.goto(html.as_uri(), wait_until="networkidle")
        name = "render-375-dark.png"
        dark.screenshot(path=str(out / name), full_page=True)
        report["dark_lost"] = sorted(set(dark.evaluate(DARK_JS)))
        dark.close()
        browser.close()
    report["console_errors"] = sorted(set(errors))
    # a missing or collapsed primary button reads as 0 and fails; 48px is the house minimum
    bad = [c for c in report["checks"] if c["overflow"] or c["orphans"] or c["clipped"] or c["distorted"]
           or (c["broken_images"] and not c["images_off"]) or c["button_height"] < 48]
    if report["console_errors"]:
        bad.append("console errors")
    if report["dark_lost"]:
        bad.append("text lost in dark mode")
    report["status"] = "FAIL" if bad else "PASS"
    print(json.dumps(report, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
