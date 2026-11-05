#!/usr/bin/env python3
"""Margarita library: the bundled example emails, by niche, occasion and style.

Usage:
  library.py find [--niche WORD] [--style ID] [--occasion WORD]   list matching entries (stdlib)
  library.py index                                                 rebuild library/previews, index.json and
                                                                   INDEX.md from library/specs (needs Playwright)

Every entry is a fictional demo brand. Use an entry for structure, block order and look, never for
facts: products, prices, offers and reviews always come from the real brand (law 1).
To add an entry: drop a spec with a "library" block (niche_key, niche, alternates, optional
occasion and occasion_kind) into library/specs/, then run `library.py index`.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "library"
PREVIEW_W, PREVIEW_H = 400, 1000      # thumbnail: the first screen and a half of a 600px email


def entries():
    return json.loads((LIB / "index.json").read_text(encoding="utf-8"))


def find(args):
    want = dict(zip(args[::2], args[1::2]))
    for e in entries():
        if "--niche" in want and want["--niche"].lower() not in (e["niche"] + " " + e["niche_key"]).lower():
            continue
        if "--style" in want and want["--style"] not in [e["style"], *e["alternates"]]:
            continue
        if "--occasion" in want and want["--occasion"].lower() not in (e.get("occasion") or e["theme"]):
            continue
        styles = ", ".join([e["style"] + " (primary)", *e["alternates"]])
        print(f'{e["id"]}: {e["niche"]} | {e.get("occasion") or e["theme"]} | {styles}\n'
              f'  subject: {e["subject"]}\n  spec: library/{e["spec"]}\n  preview: library/{e["previews"][e["style"]]}')


def index():
    sys.path.insert(0, str(ROOT / "scripts"))
    from render import launch                       # Chromium, else the installed Chrome
    from playwright.sync_api import sync_playwright
    from PIL import Image
    import io
    out_dir = LIB / "previews"
    out_dir.mkdir(exist_ok=True)
    rows = []
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
        browser = launch(p)
        for spec_path in sorted((LIB / "specs").glob("*.json")):
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            meta, email = spec["library"], spec["emails"][0]
            slug, build_out = email["slug"], Path(tmp) / spec_path.stem
            cmd = [sys.executable, str(ROOT / "scripts" / "build.py"), str(spec_path), "--out", str(build_out)]
            if meta["alternates"]:
                cmd += ["--styles", ",".join(meta["alternates"])]
            if subprocess.run(cmd, capture_output=True, text=True).returncode != 0:
                sys.exit(f"build failed: {spec_path.name} (run build.py on it to see why)")
            previews = {}
            for style in [spec["style"], *meta["alternates"]]:
                page_dir = build_out / slug if style == spec["style"] else build_out / "_styles" / f"{slug}--{style}"
                page = browser.new_page(viewport={"width": 600, "height": 900})
                page.goto((page_dir / "preview.html").as_uri(), wait_until="networkidle")
                im = Image.open(io.BytesIO(page.screenshot(full_page=True))).convert("RGB")
                page.close()
                tall = round(600 * PREVIEW_H / PREVIEW_W)
                im = im.crop((0, 0, 600, min(im.height, tall)))
                im = im.resize((PREVIEW_W, round(im.height * PREVIEW_W / 600)), Image.LANCZOS)
                name = f"{slug}.jpg" if style == spec["style"] else f"{slug}--{style}.jpg"
                im.save(out_dir / name, quality=78, optimize=True, progressive=True)
                previews[style] = f"previews/{name}"
            rows.append({"id": slug, "niche_key": meta["niche_key"], "niche": meta["niche"],
                         "occasion": meta.get("occasion"), "occasion_kind": meta.get("occasion_kind"),
                         "theme": email["theme"], "brand": spec["brand"]["name"], "subject": email["subject"][0],
                         "preheader": email["preheader"], "style": spec["style"], "alternates": meta["alternates"],
                         "blocks": [b["type"] for b in email["blocks"]], "spec": f"specs/{spec_path.name}", "previews": previews})
            print(f"  {slug}: {len(previews)} preview(s)")
        browser.close()
    (LIB / "index.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(rows)
    print(f"library: {len(rows)} entries, {sum(len(r['previews']) for r in rows)} previews")


def write_markdown(rows):
    styles = json.loads((ROOT / "data" / "styles.json").read_text(encoding="utf-8"))["styles"]
    tour = next((r for r in rows if len(r["previews"]) == len(styles)), None)
    md = ["# Margarita library", "",
          f"{len(rows)} example emails from fictional demo brands, each with a spec that `scripts/build.py` rebuilds",
          "and a preview of the first screen. Generated by `scripts/library.py index`; do not edit by hand.", "",
          "**Use it to show, not to copy.** When the user is choosing a look, show the matching preview before",
          "building anything. Borrow structure, block order and rhythm from a spec. Never reuse its copy, products,",
          "prices, offers or photos for a real brand: every fact comes from the real brand (law 1).", "",
          "Query it: `python3 scripts/library.py find --niche candles`, `--style dark-premium`, `--occasion bfcm`.", ""]
    if tour:
        md += ["## Style tour", "", f"One email ({tour['brand']}, {tour['niche']}) in all {len(styles)} styles:", "",
               "| Style | What it is | Preview |", "|---|---|---|"]
        for sid, s in styles.items():
            md.append(f"| `{sid}` | {s['name']}: best for {s['best_for']} | [{tour['id']}]({tour['previews'][sid]}) |")
        md.append("")
    for title, sel in (("By niche", lambda r: not r["occasion"]), ("By occasion and flow", lambda r: r["occasion"])):
        md += [f"## {title}", "", "| Entry | Niche | Theme / occasion | Styles (previews) | Blocks | Spec |", "|---|---|---|---|---|---|"]
        for r in (r for r in rows if sel(r)):
            links = ", ".join(f"[{s}]({path})" for s, path in r["previews"].items())
            label = f"{r['occasion']} ({r['occasion_kind']})" if r["occasion"] else r["theme"]
            md.append(f"| {r['id']}: {r['subject']} | {r['niche']} | {label} | {links} | {len(r['blocks'])} | [{r['spec'].split('/')[-1]}]({r['spec']}) |")
        md.append("")
    md += ["Photos are hotlinked from Unsplash (free under the Unsplash License). Brand names, domains (`.test`),",
           "products and reviews are invented for the demos.", ""]
    (LIB / "INDEX.md").write_text("\n".join(md), encoding="utf-8")


def main():
    a = sys.argv[1:]
    if a[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    if not a or a[0] not in ("find", "index"):
        sys.exit(__doc__)
    find(a[1:]) if a[0] == "find" else index()
    return 0


if __name__ == "__main__":
    sys.exit(main())
