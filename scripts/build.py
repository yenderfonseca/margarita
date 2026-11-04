#!/usr/bin/env python3
"""Margarita build: render Klaviyo-ready emails from one spec.json.

Usage:
  build.py spec.json --out DIR             build every email in the spec, then preflight each
  build.py spec.json --out DIR --styles all|editorial,dark-premium
                                            also render each email in other styles (preview only)
  build.py --list                          list styles and blocks
  build.py --scaffold <preset|niche> <occasion>   print a starter spec ([[FILL]] marks every fact)
  build.py --self-test                     build the example spec in all 13 styles; all must PASS

The engine fills assets/shell.html with blocks from assets/blocks.html and the style tokens in
data/styles.json. Template syntax (square brackets, so it never collides with Klaviyo's {{ }} / {% %}):
  [[name]]                      value (strict: a missing value is an error, never blank)
  [[if name]] .. [[else]] .. [[/if]]   [[if not name]] .. [[/if]]
  [[each items]] .. [[/each]]   loop; inside, item fields plus n ("01"), index, first, last
Automatic: gap collapse between same-background neighbours, &nbsp; glue on the last two words of
headings / labels / buttons, straight quotes, UTM on links to the brand's domain, VML button
width and case, label and star colors chosen by contrast, local images copied to images/ and zipped.
Stdlib only.
"""
import copy
import json
import re
import shutil
import sys
import tempfile
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import preflight  # noqa: E402

TAG = re.compile(r'\[\[\s*(if not\b|if\b|each\b|else\b|/if|/each)?\s*([\w.]*)\s*\]\]')
BLOCK = re.compile(r'^<!-- BLOCK: (\w+)(.*?)-->\n(.*?)(?=\n<!-- BLOCK:|\Z)', re.S | re.M)
GLUE = {"headline", "heading", "title", "label", "cta_label", "signature", "author", "q", "a", "link_label",
        "subhead", "text", "p", "caption", "note", "terms", "quote", "intro", "signoff", "tagline", "signup_reason",
        "author_title", "signature_title"}
ROLES = ["page", "canvas", "band", "border", "ink", "ink2", "accent", "on_accent", "dark_bg", "dark_text"]
# Fixed words the blocks print, by brand.lang; brand.words overrides any of them.
WORDS = {
    "en": {"hi": "Hi", "qty": "Qty", "unsubscribe": "Unsubscribe", "preferences": "Manage preferences", "web_view": "View in browser"},
    "es": {"hi": "Hola", "qty": "Cant.", "unsubscribe": "Cancelar suscripción", "preferences": "Gestionar preferencias", "web_view": "Ver en el navegador"},
    "pt": {"hi": "Olá", "qty": "Qtd.", "unsubscribe": "Cancelar inscrição", "preferences": "Gerir preferências", "web_view": "Ver no navegador"},
    "fr": {"hi": "Bonjour", "qty": "Qté", "unsubscribe": "Se désabonner", "preferences": "Gérer mes préférences", "web_view": "Voir dans le navigateur"},
    "de": {"hi": "Hallo", "qty": "Menge", "unsubscribe": "Abmelden", "preferences": "Einstellungen verwalten", "web_view": "Im Browser ansehen"},
    "it": {"hi": "Ciao", "qty": "Qtà", "unsubscribe": "Annulla iscrizione", "preferences": "Gestisci preferenze", "web_view": "Vedi nel browser"},
}
PADS = {"thin": ("24px", "24px"), "bleed": ("0px", "0px"), "none": ("0px", "0px"),
        "header": ("32px", "24px"), "footer": ("40px", "48px")}


class BuildError(Exception):
    pass


# ---------- template engine ----------
def parse(src):
    root = []
    lists, nodes = [root], []
    pos = 0
    for m in TAG.finditer(src):
        lists[-1].append(src[pos:m.start()])
        pos = m.end()
        kw, name = m.group(1), m.group(2)
        if kw in ("if", "if not", "each"):
            n = {"kw": kw, "name": name, "body": [], "else": []}
            lists[-1].append(n)
            nodes.append(n)
            lists.append(n["body"])
        elif kw == "else":
            lists[-1] = nodes[-1]["else"]
        elif kw in ("/if", "/each"):
            if not nodes:
                raise BuildError(f"unmatched [[{kw}]]")
            nodes.pop()
            lists.pop()
        else:
            lists[-1].append({"kw": "var", "name": name})
    if nodes:
        raise BuildError(f"unclosed [[{nodes[-1]['kw']} {nodes[-1]['name']}]]")
    lists[-1].append(src[pos:])
    return root


def render(tree, ctx, where):
    out = []
    for n in tree:
        if isinstance(n, str):
            out.append(n)
        elif n["kw"] == "var":
            v = ctx.get(n["name"])
            if v is None or v == "":
                raise BuildError(f"{where}: [[{n['name']}]] has no value (add it, or wrap it in [[if {n['name']}]])")
            out.append(str(v))
        elif n["kw"] in ("if", "if not"):
            truthy = bool(ctx.get(n["name"]))
            branch = n["body"] if truthy == (n["kw"] == "if") else n["else"]
            out.append(render(branch, ctx, where))
        else:  # each
            items = ctx.get(n["name"]) or []
            for i, item in enumerate(items):
                sub = {**ctx, **item, "n": f"{i + 1:02d}", "index": i + 1, "first": i == 0, "last": i == len(items) - 1,
                       "even": i % 2 == 1}
                out.append(render(n["body"], sub, f"{where}.{n['name']}[{i}]"))
    return "".join(out)


# ---------- text helpers ----------
def glue(s):
    """Join the last two words with &nbsp; so a heading or button never ends on one word.
    Klaviyo tags are protected: a space inside {{ }} or {% %} must never become &nbsp;."""
    tags = re.findall(r"\{\{.*?\}\}|\{%.*?%\}", s)
    if tags:
        masked = s
        for i, t in enumerate(tags):
            masked = masked.replace(t, f"\x00{i}\x00", 1)
        out = glue(masked)
        for i, t in enumerate(tags):
            out = out.replace(f"\x00{i}\x00", t)
        return out
    if "&nbsp;" in s[-30:] or "<" in s or len(s.split()) < 3:
        return s  # two words split one per line is balanced, not an orphan; glued, they clip narrow tiles
    parts = s.rsplit(" ", 1)
    if len(parts) == 2 and len(parts[0].rsplit(" ", 1)[-1]) + len(parts[1]) <= 24:
        return parts[0] + "&nbsp;" + parts[1]
    return s


def tidy(v, key, home_host, utm):
    if isinstance(v, list):
        return [tidy(x, key, home_host, utm) for x in v]
    if isinstance(v, dict):
        return {k: tidy(x, k, home_host, utm) for k, x in v.items()}
    if not isinstance(v, str):
        return v
    v = v.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
    if key == "url" or key.endswith("_url"):
        if home_host and urlparse(v).netloc.endswith(home_host) and "utm_source=" not in v:
            v += ("&" if "?" in v else "?") + utm
        return v
    if key in ("src", "photo", "icon_src", "type", "style"):
        return v
    v = re.sub(r'&(?!#?\w+;)', '&amp;', v)
    raw_html = "<" in v
    if not raw_html:
        v = v.replace('"', "&quot;")  # values also land in alt="" attributes
    if key in GLUE:
        v = glue(v)
    # never on fields that are reused inside attributes (title doubles as alt text)
    if key in {"headline", "heading", "subhead", "tagline"} and not raw_html:
        v = re.sub(r'(?<![\w-])(\w+(?:-\w+)+)(?![\w-])', r'<span style="white-space:nowrap;">\1</span>', v)
    return v


def px(v):
    return int(re.sub(r'\D', '', str(v)) or 0)


def img_size(p):
    """(width, height) of a PNG, GIF or JPEG from its header; None if unreadable."""
    b = p.read_bytes()
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(b[16:20], "big"), int.from_bytes(b[20:24], "big")
    if b[:6] in (b"GIF87a", b"GIF89a"):
        return int.from_bytes(b[6:8], "little"), int.from_bytes(b[8:10], "little")
    i = 2
    while b[:2] == b"\xff\xd8" and i + 9 < len(b):
        if b[i] != 0xFF:
            i += 1
            continue
        marker, seg = b[i + 1], int.from_bytes(b[i + 2:i + 4], "big")
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            return int.from_bytes(b[i + 7:i + 9], "big"), int.from_bytes(b[i + 5:i + 7], "big")
        i += 2 + seg
    return None


def check_images(btype, b, sizes, warn):
    """Sharpness at 2x and one shared aspect ratio per grid; email clients cannot crop."""
    need = {"hero_image": 1200, "image_band": 1200, "split_hero": 750, "spotlight": 750}.get(btype)
    if need and b.get("src") in sizes and sizes[b["src"]][0] < need:
        warn(f"{btype} image {b['src']} is {sizes[b['src']][0]}px wide; {need}px needed for a sharp 2x render")
    if btype in ("products", "category_tiles"):
        dims = [(it["src"], sizes[it["src"]]) for it in b.get("items") or [] if it.get("src") in sizes]
        for src, (w, h) in dims:
            if w < 660:
                warn(f"{btype} image {src} is {w}px wide; about 660px needed (cards stack to full width on phones)")
        ratios = {round(w / h, 2) for _, (w, h) in dims}
        if dims and min(ratios) < 0.78:
            warn(f"{btype} images are tall portraits ({min(ratios)}): grids read best at 1:1 or 4:5")
        if len(dims) > 1 and max(ratios) - min(ratios) > 0.05:
            warn(f"{btype} images have different shapes {sorted(ratios)}: crop them to one ratio first, e.g. "
                 f"sips -c <h> <w> <file> (square: equal h and w); email clients cannot crop")


# ---------- library ----------
def load_library():
    lib = {}
    for m in BLOCK.finditer((ROOT / "assets" / "blocks.html").read_text(encoding="utf-8")):
        meta = dict(kv.strip().split("=", 1) for kv in m.group(2).split("|") if "=" in kv)
        # strip only documentation comments ("<!-- " with a space); MSO conditionals stay intact
        body = re.sub(r'\n?<!-- .*?-->', '', m.group(3), flags=re.S).strip()
        lib[m.group(1)] = {"bg": meta.get("bg", "canvas").strip(), "pad": meta.get("pad", "section").strip(),
                           "req": [r.strip() for r in meta.get("req", "").split(",") if r.strip()],
                           "tree": parse(body)}
    return lib


def load_styles():
    d = json.loads((ROOT / "data" / "styles.json").read_text(encoding="utf-8"))
    return d["defaults"], d["styles"]


# ---------- per-block preparation ----------
def prep(btype, b, tok):
    gutter = px(tok["gutter_x"])
    if btype in ("products", "category_tiles"):
        items = b.get("items") or []
        cols = 2 if btype == "category_tiles" else int(b.get("columns") or (3 if len(items) in (3, 6) else 2))
        gap = 16
        b["img_w"] = (600 - 2 * gutter - gap * (cols - 1)) // cols
        b["col_pct"] = f"{100 // cols}%"
        # phones: 2-up stays side by side; 3-up stacks with a capped image so one card is not a full screen
        b["cell_class"] = "m-half" if cols == 2 else "m-stack m-gap"
        b["img_class"] = "m-img" if cols == 2 else "m-img m-cardimg"
        # the light plate (dk-keep) must shrink with the capped image, or dark mode shows light bars beside it
        b["tile_class"] = "" if cols == 2 else ("m-cardtile" if tok.get("product_tile") else "m-cardtile0")
        if any(it.get("label") for it in items):  # keep titles level across a row
            items = [it if it.get("label") else dict(it, label="&nbsp;") for it in items]
        half = gap // 2
        b["rows"] = [{"cells": [dict(it, pad_l=f"{0 if j == 0 else half}px", pad_r=f"{0 if j == cols - 1 else half}px",
                                     cell_w=b["img_w"])
                                for j, it in enumerate(items[i:i + cols])]}
                     for i in range(0, len(items), cols)]
    if btype in ("stats_row", "feature_grid"):
        b["col_pct"] = f"{100 // max(1, len(b.get('items') or [1]))}%"
    if btype == "overlay_hero":
        b["hero_h"] = int(b.get("height") or 420)
    if btype == "media_rows":
        b["half_w"] = (600 - 2 * gutter) // 2
    if btype == "mosaic":
        items = b.get("items") or []
        if len(items) not in (1, 3):
            raise BuildError("mosaic needs 1 or 3 images (one large, then two side by side)")
        lead = items[0]
        b.update(lead_src=lead["src"], lead_alt=lead.get("alt", ""), lead_url=lead.get("url", ""))
        b["pair"] = [dict(it, pad_l="0px" if j == 0 else "4px", pad_r="4px" if j == 0 else "0px") for j, it in enumerate(items[1:3])]
    if btype == "quote":
        b["byline"] = glue(b["author"] + (", " + b["author_title"] if b.get("author_title") else ""))
    if btype == "reviews":
        for it in b.get("items") or []:
            if it.get("stars"):
                it["stars_html"] = "&#9733;" * int(it["stars"])
    if btype == "cta":
        label = b.get("label", "")
        b["vml_label"] = label.upper().replace("&NBSP;", "&nbsp;") if tok["btn_case"] == "uppercase" else label
        b["vml_width"] = max(220, min(520, len(label.replace("&nbsp;", " ")) * 9 + 80))
    if btype in ("story", "letter"):
        body = b.get("body") or []
        b["paragraphs"] = [{"p": glue(p)} for p in ([body] if isinstance(body, str) else body)]
    return b


def mix(a, b, t):
    """t of color b blended into color a (sRGB), as #rrggbb."""
    a, b = preflight.norm_hex(a)[1:], preflight.norm_hex(b)[1:]
    return "#" + "".join(f"{round(int(a[i:i + 2], 16) * (1 - t) + int(b[i:i + 2], 16) * t):02X}" for i in (0, 2, 4))


def derive_palette(given, log):
    """Fill missing roles from canvas, ink and accent, only by mixing supplied colors (no new hues).
    Derive, never invent: grays are mixes of ink and canvas."""
    c = preflight.contrast
    for need in ("canvas", "ink", "accent"):
        if not given.get(need):
            raise BuildError(f"brand.palette needs at least canvas, ink and accent (missing {need})")
    bad = {k: v for k, v in given.items() if v and not re.fullmatch(r"#?[0-9a-fA-F]{3}([0-9a-fA-F]{3})?", str(v))}
    if bad:
        raise BuildError(f"brand.palette values must be hex colors: {bad}")
    p = {k: preflight.norm_hex(v).upper() for k, v in given.items() if v}

    def put(role, value, why):
        if role not in p:
            p[role] = value
            log(f"[derived] {role} {value}: {why}")
    put("page", p["canvas"], "same as canvas")
    put("band", mix(p["canvas"], p["ink"], 0.05), "5% ink on canvas")
    put("border", mix(p["canvas"], p["ink"], 0.14), "14% ink on canvas")
    # ink2: the softest ink-to-canvas mix that still reads at 4.6:1 on canvas and band
    ink2 = p["ink"]
    for t in (0.45, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1):
        cand = mix(p["ink"], p["canvas"], t)
        if min(c(cand, p["canvas"]), c(cand, p["band"])) >= 4.6:
            ink2 = cand
            break
    put("ink2", ink2, "softest ink/canvas mix that keeps 4.6:1")
    on = max((p["canvas"], p["ink"]), key=lambda x: c(x, p["accent"]))
    put("on_accent", on, "canvas or ink, whichever reads best on accent")
    dark, light = sorted((p["canvas"], p["ink"]), key=lambda x: c(x, "#000000"))
    put("dark_bg", dark, "darker of canvas and ink")
    put("dark_text", light, "lighter of canvas and ink")
    put("dark_text2", mix(p["dark_text"], p["dark_bg"], 0.25), "25% dark_bg into dark_text")
    put("dark_band", mix(p["dark_bg"], p["dark_text"], 0.07), "7% dark_text on dark_bg (tiles and bands in dark mode)")
    put("dark_border", mix(p["dark_bg"], p["dark_text"], 0.2), "20% dark_text on dark_bg")
    put("dark_lift", mix(p["dark_bg"], p["dark_text"], 0.12), "12% dark_text on dark_bg (ink bars stay visible in dark mode)")
    p["dark_accent"] = next((mix(p["accent"], p["dark_text"], t / 10) for t in range(11)
                             if min(c(mix(p["accent"], p["dark_text"], t / 10), p[k]) for k in ("dark_bg", "dark_band")) >= 4.5),
                            p["dark_text"])
    # accent_text: the accent for small labels, darkened (or lightened) toward ink until 4.5:1, keeping its hue
    acc = p["accent"]
    for t in [x / 10 for x in range(0, 11)]:
        cand = mix(p["accent"], p["ink"], t)
        if min(c(cand, p["canvas"]), c(cand, p["band"])) >= 4.5:
            acc = cand
            break
    else:
        acc = p["ink2"]
    if acc != p["accent"]:
        log(f"[derived] accent_text {acc}: accent {p['accent']} moved toward ink until 4.5:1 for small labels")
    p.setdefault("accent_text", acc)
    # inverse bars (ink background): canvas text, and a softer canvas/ink mix that keeps 4.5:1
    p["inv_text"] = p["canvas"]
    p["inv_text2"] = next((mix(p["canvas"], p["ink"], t) for t in (0.35, 0.3, 0.25, 0.2, 0.15, 0.1)
                           if c(mix(p["canvas"], p["ink"], t), p["ink"]) >= 4.5), p["canvas"])
    return p


def chrome(btype, b, base, pal, logo_inverse):
    """Header and footer layouts: logo markup and the colors each layout sits on."""
    layout = b.get("layout") or ("rich" if btype == "footer" and (b.get("links") or b.get("social") or b.get("note")) else "")
    inverse = layout == "inverse"
    c = preflight.contrast
    dark_canvas = c(pal["canvas"], "#000000") < c(pal["canvas"], "#FFFFFF")
    inv_bg = mix(pal["canvas"], pal["ink"], 0.08) if dark_canvas else pal["ink"]
    inv_fg, inv_fg2 = (pal["ink"], pal["ink2"]) if dark_canvas else (pal["inv_text"], pal["inv_text2"])
    b["inv_bg"], b["inv_fg"] = inv_bg, inv_fg
    b["is_inverse"], b["is_split"], b["is_rich"] = inverse, layout == "split", layout in ("rich", "inverse")
    color = inv_fg if inverse else pal["ink"]
    src = logo_inverse if inverse else base["logo_src"]
    margin = "0" if layout == "split" else base["align_margin"] if btype == "header" else "auto"
    if src:
        w = base["logo_width"]
        b["logo_html"] = (f'<img src="{src}" alt="{base["brand_name"]}" width="{w}" style="display:block;width:{w}px;'
                          f'max-width:{w}px;height:auto;margin:0 {margin};border:0;text-align:center;font-family:{base["heading_stack"]};'
                          f'font-size:22px;line-height:28px;letter-spacing:3px;text-transform:uppercase;color:{color};">')
    else:
        b["logo_html"] = (f'<span class="m-wordmark" style="display:block;font-family:{base["heading_stack"]};font-size:22px;line-height:28px;'
                          f'font-weight:{base["heading_weight"]};letter-spacing:3px;text-transform:uppercase;color:{color};">'
                          f'{glue(base["brand_name"]) if len(base["brand_name"]) <= 24 else base["brand_name"]}</span>')
    if btype == "footer":
        b["f_bg"] = inv_bg if inverse else pal["canvas"]
        b["f_class"] = "bg-inverse" if inverse else "bg-canvas"  # bg-inverse has no dark-mode override on purpose
        b["f_text"] = inv_fg if inverse else pal["ink"]
        b["f_text2"] = inv_fg2 if inverse else pal["ink2"]
        b["f_border"] = inv_fg2 if inverse else pal["border"]


def button_colors(pal, tok):
    """The primary button must read as a shape: accent if it stands 3:1 off the canvas, else the opposite
    end of the palette; a pale accent that only passes for text gets a hairline border (WCAG 1.4.11)."""
    c = preflight.contrast
    if c(pal["accent"], pal["canvas"]) >= 3:
        pal["btn_bg"], pal["btn_border"] = pal["accent"], False
    elif c(pal["accent"], pal["canvas"]) >= 1.15:
        pal["btn_bg"], pal["btn_border"] = pal["accent"], True
    else:
        pal["btn_bg"], pal["btn_border"] = pal["ink"], False
    pal["on_btn"] = pal["on_accent"] if pal["btn_bg"] == pal["accent"] else max((pal["canvas"], pal["ink"]), key=lambda x: c(x, pal["btn_bg"]))
    if c(pal["on_btn"], pal["btn_bg"]) < 4.5:
        raise BuildError(f"button text {pal['on_btn']} on {pal['btn_bg']} is under 4.5:1; set on_accent in the palette")


def keep_together(v, name):
    """The brand name never breaks across lines (e.g. 'Tabby & Co')."""
    esc = name.replace("&", "&amp;")
    if isinstance(v, dict):
        return {k: keep_together(x, name) if k not in ("url", "src", "alt", "type") and not k.endswith("_url") else x for k, x in v.items()}
    if isinstance(v, list):
        return [keep_together(x, name) for x in v]
    if isinstance(v, str) and " " in esc and len(esc) <= 30:
        return v.replace(esc, esc.replace(" ", "&nbsp;"))
    return v


def check_palette(pal):
    c = preflight.contrast
    probs = []
    for fg, bgs in (("ink", ("canvas", "band")), ("ink2", ("canvas", "band")),
                    ("on_accent", ("accent",)), ("dark_text", ("dark_bg",))):
        for bg in bgs:
            r = c(pal[fg], pal[bg])
            if r < 4.5:
                probs.append(f"{fg} {pal[fg]} on {bg} {pal[bg]} is {r:.2f}:1 (needs 4.5)")
    if preflight.norm_hex(pal["border"]) == preflight.norm_hex(pal["canvas"]):
        probs.append("border equals canvas (an invisible divider): pick another palette color")
    if probs:
        raise BuildError("palette roles fail contrast; re-map per references/brand-intake.md section 3:\n  "
                         + "\n  ".join(probs))


# ---------- dark mode ----------
VOID = {"area", "base", "br", "col", "hr", "img", "input", "link", "meta", "source", "wbr"}
HEX = r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b"


class _Walk(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []  # (line, col, raw, tag, attrs, depth_change)

    def handle_starttag(self, tag, attrs):
        line, col = self.getpos()
        self.tags.append((line, col, self.get_starttag_text(), tag, dict(attrs), "open" if tag not in VOID else "void"))

    def handle_startendtag(self, tag, attrs):
        line, col = self.getpos()
        self.tags.append((line, col, self.get_starttag_text(), tag, dict(attrs), "void"))

    def handle_endtag(self, tag):
        line, col = self.getpos()
        self.tags.append((line, col, None, tag, None, "close"))


def darken(html, pal):
    """Dark-mode classes from the surface each element really sits on (Apple Mail, iOS Mail, Outlook.com).
    Surfaces close to the canvas turn dark_bg (canvas, page) or dark_band (bands, tiles); accent bands,
    inverse bars and image cells keep their colors, and so does the text on them. Text that would drop
    under 4.5:1 on its dark surface moves to dark_text, dark_text2 or dark_accent; light hairlines go dark_border.
    A button that would melt into the dark canvas (an ink button) flips to dark_text with dark_bg text;
    an ink bar (announcement, inverse footer, accent band) lifts to dark_lift so it still reads as a band.
    ponytail: logos and photos are not touched; a dark logo on a transparent PNG needs a light version
    (brand.logo_inverse) or a solid background in the file."""
    c = preflight.contrast
    nh = lambda h: preflight.norm_hex(h).upper()
    light = lambda h: c(h, "#000000") > c(h, "#FFFFFF")
    if not light(pal["canvas"]):  # dark styles are already dark
        return html.replace("/*dk-media*/", "").replace("/*dk-ogs*/", "")
    accents = {nh(pal["accent"]), nh(pal["accent_text"])} - {nh(pal["ink"]), nh(pal["ink2"])}
    canvases = {nh(pal["canvas"]), nh(pal["page"])}

    def want(col, surf):
        if not col or not surf or c(col, surf) >= 4.5:
            return col
        if light(surf):  # an inverted button
            return pal["dark_bg"]
        if col == nh(pal["ink"]):  # the strongest light-mode text stays the strongest in dark
            return pal["dark_text"]
        if col in accents:
            return pal["dark_accent"]
        t2 = pal["dark_text2"] if c(pal["dark_text2"], surf) >= 4.5 else pal["dark_text"]
        return pal["dark_text"] if c(col, pal["canvas"]) >= 7 else t2

    classes = {}

    def cls(prop, value):
        return classes.setdefault((prop, nh(value)), f"dk{len(classes) + 1}")

    w = _Walk()
    w.feed(html)
    starts = [0]
    for i, ch in enumerate(html):
        if ch == "\n":
            starts.append(i + 1)
    # tag, dark surface (None: keeps its colors), light color, dark color, button state (None, "in", or its swapped bg)
    stack = [("root", nh(pal["dark_bg"]), None, None, None, None)]  # last: a lifted ink bar's light-mode color
    edits, outer = [], None
    for line, col, raw, tag, attrs, kind in w.tags:
        if kind == "close":
            while len(stack) > 1:
                if stack.pop()[0] == tag:
                    break
            continue
        _, surf, l_col, d_col, btn, lift = stack[-1]
        if tag == "table" and "m-btn" in (attrs.get("class") or "").split():
            btn, outer = "in", surf
        style = attrs.get("style") or ""
        keep = "dk-keep" in (attrs.get("class") or "").split()  # a light plate behind product photos
        bg = re.search(r"background(?:-color)?\s*:\s*(" + HEX + ")", style) or re.search("^(" + HEX + ")$", attrs.get("bgcolor") or "")
        add = []
        if keep or "url(" in style or attrs.get("background"):
            surf = None
        elif bg:
            b = nh(bg.group(1))
            if btn and (b == btn or btn == "in" and outer and c(b, outer) < 1.5):
                btn, surf = b, nh(pal["dark_text"])
                add.append(cls("background-color", surf))
            else:
                parent = surf
                surf = (nh(pal["dark_bg"]) if b in canvases else nh(pal["dark_band"])) if light(b) and c(b, pal["canvas"]) < 1.3 else None
                if surf:
                    add.append(cls("background-color", surf))
                elif parent and c(b, parent) < 1.15 or b == lift:  # an ink bar would melt into the dark canvas: lift it
                    add.append(cls("background-color", pal["dark_lift"]))
                    lift, surf = b, nh(pal["dark_lift"])
        own = re.search(r"(?<![-\w])color\s*:\s*(" + HEX + ")", style)
        if own:
            l_col = nh(own.group(1))
            d = want(l_col, surf)
            if d != l_col:
                add.append(cls("color", d))
            d_col = d
        elif bg or surf is None:
            d = want(l_col, surf) if surf else l_col
            if l_col and d != d_col:
                add.append(cls("color", d))
            d_col = d
        brd = re.search(r"border(?:-(?:top|bottom|left|right))?\s*:[^;]*?(" + HEX + ")", style)
        if surf and brd and light(brd.group(1)) and c(brd.group(1), pal["canvas"]) < 1.6:
            add.append(cls("border-color", pal["dark_border"]))
        elif surf and brd and c(nh(brd.group(1)), surf) < 3:  # e.g. an ink coupon frame on dark_band
            add.append(cls("border-color", pal["dark_text2"]))
        if add:
            edits.append((starts[line - 1] + col, raw, add))
        if kind == "open":
            stack.append((tag, surf, l_col, d_col, btn, lift))
    for off, raw, add in reversed(edits):
        assert html[off:off + len(raw)] == raw, raw
        m = re.search(r'\sclass="([^"]*)"', raw)
        new = (raw[:m.start(1)] + m.group(1) + " " + " ".join(add) + raw[m.end(1):]) if m else \
            re.sub(r"^<(\w[\w:-]*)", lambda t: f'<{t.group(1)} class="{" ".join(add)}"', raw, count=1)
        html = html[:off] + new + html[off + len(raw):]
    media = "\n".join(f".{k}{{{p}:{v} !important;}}" for (p, v), k in classes.items())
    ogs = "\n".join(f"[data-{'ogsb' if p == 'background-color' else 'ogsc'}] .{k}{{{p}:{v} !important;}}" for (p, v), k in classes.items())
    return html.replace("/*dk-media*/", media).replace("/*dk-ogs*/", ogs)


# ---------- build one email ----------
def build_email(spec, email, style_id, lib, defaults, styles, out_dir, assets_dir):
    if style_id not in styles:
        raise BuildError(f"unknown style {style_id!r}; see build.py --list")
    tok = {**defaults, **styles[style_id]["tokens"]}
    brand = spec["brand"]
    derived = []
    given = dict(brand["palette"])
    c = preflight.contrast
    if styles[style_id].get("canvas") == "dark" and c(given["canvas"], "#000000") > c(given["ink"], "#000000"):
        # a dark style on a light palette: same colors, swapped ends; every other role is re-derived
        given = {"canvas": given["ink"], "ink": given["canvas"], "accent": given["accent"]}
        derived.append(f"[derived] style {style_id}: canvas and ink swapped to give a dark canvas from the same palette")
    pal = derive_palette(given, derived.append)
    if not email["slug"].count("--"):
        for line in derived:
            print(f"  {email['slug']}: {line}", file=sys.stderr)
    check_palette(pal)
    if tok.get("band_mode") == "tint" and "band" not in brand["palette"]:
        tint = mix(pal["canvas"], pal["accent"], 0.14)
        if min(c(pal["ink"], tint), c(pal["ink2"], tint)) >= 4.5:
            pal["band"] = tint
    button_colors(pal, tok)
    band_orig = pal["band"]
    if tok.get("flat"):
        pal["band"] = pal["canvas"]
    label_color = pal["accent_text"]
    star_color = pal["accent"] if c(pal["accent"], pal["band"]) >= 3 else pal["accent_text"]
    home = brand.get("home_url", "")
    host = urlparse(home).netloc.replace("www.", "")
    slug = email["slug"]
    utm = f"utm_source=klaviyo&utm_medium=email&utm_campaign={spec.get('utm_prefix', host.split('.')[0])}_{slug.split('--')[0]}"
    base = {
        **pal, **{k: v for k, v in tok.items() if not isinstance(v, list)},
        "tile_bg": band_orig if tok.get("product_tile") else pal["canvas"],
        "btn_border": bool(tok.get("btn_border") or pal["btn_border"]),
        "hero_pad": f"24px {tok['gutter_x']} 0 {tok['gutter_x']}" if tok.get("image_inset") else "0",
        "hero_bg": pal["canvas"] if tok.get("image_inset") else pal["band"],
        "hero_radius": tok["img_radius"] if tok.get("image_inset") else "0px",
        "tile_pad": "12px" if tok.get("product_tile") else "0px",
        "gutter": tok["gutter_x"], "align_margin": "auto" if tok["align"] == "center" else "0",
        "arcsize": f"{min(50, round(px(tok['radius']) / 52 * 100))}%", "label_color": label_color,
        "star_color": star_color, "heading_stack": brand["body_stack"] if tok.get("heading_family") == "body" and brand.get("heading_source") != "site" else brand["heading_stack"],
        "body_stack": brand["body_stack"],
        "body_fallback": brand.get("body_fallback") or re.sub(r"^'[^']*',\s*", "", brand["body_stack"]),
        "brand_name": brand["name"], "home_url": tidy(home, "url", host, utm), "lang": brand.get("lang", "en"),
        "logo_src": brand.get("logo_src"), "logo_width": brand.get("logo_width", 140),
        "fonts_link": brand.get("fonts_link"), "subject": email["subject"][0], "preheader": email["preheader"],
    }
    lang = str(base["lang"]).split("-")[0].lower()
    if lang not in WORDS and not brand.get("words"):
        raise BuildError(f"brand.lang {base['lang']!r} has no built-in words ({', '.join(WORDS)}); add brand.words with {', '.join(WORDS['en'])}")
    base.update({f"w_{k}": v for k, v in {**WORDS.get(lang, WORDS["en"]), **brand.get("words", {})}.items()})
    email_dir = out_dir / slug
    img_dir = email_dir / "images"
    local = []

    def localize(src):
        if not src or re.match(r'(https?:)?//|\{', src):
            return src
        p = Path(src) if Path(src).is_absolute() else (assets_dir / src)
        if not p.is_file():
            raise BuildError(f"{slug}: image not found: {p}")
        img_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, img_dir / p.name)
        local.append(p.name)
        if p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".gif"):
            raise BuildError(f"{slug}: {p.name}: email clients need JPG, PNG or GIF (convert: sips -s format jpeg)")
        size = img_size(p)
        if size:
            sizes[f"images/{p.name}"] = size
        return f"images/{p.name}"

    sizes = {}

    def warn(msg):
        print(f"  warn {slug}: {msg}", file=sys.stderr)

    if base["logo_src"]:
        base["logo_src"] = localize(base["logo_src"])
    logo_inverse = localize(brand.get("logo_inverse_src")) if brand.get("logo_inverse_src") else None

    blocks = []
    for i, raw in enumerate(email["blocks"]):
        btype = raw["type"]
        if btype not in lib:
            raise BuildError(f"{slug}: unknown block {btype!r}; see build.py --list")
        if btype in tok.get("hide", []):
            print(f"  note: style {style_id} leaves out {btype} in {slug}", file=sys.stderr)
            continue
        b = tidy(copy.deepcopy(raw), "", host, utm)
        b = keep_together(b, brand["name"])
        if b.get("src"):
            b["src"] = localize(b["src"])
        for it in b.get("items") or []:
            for k in ("src", "photo", "icon_src"):
                if isinstance(it, dict) and it.get(k):
                    it[k] = localize(it[k])
        check_images(btype, b, sizes, warn)
        lack = [r for r in lib[btype]["req"] if not b.get(r)]
        if lack:
            raise BuildError(f"{slug}: block {i} {btype} needs {lack}; drop the block if the facts do not exist")
        b = prep(btype, b, tok)
        if btype in ("header", "footer"):
            chrome(btype, b, base, pal, logo_inverse)
        bg = "inverse" if b.get("is_inverse") else lib[btype]["bg"]
        if btype == "hero_text" and tok.get("hero_band") == "accent" and pal["btn_bg"] == pal["accent"] and not pal["btn_border"]:
            bg = "accentband"
        if tok.get("flat") and bg == "band":
            bg = "canvas"
        kind = lib[btype]["pad"]
        sy = tok["section_y"]
        pt, pb = PADS.get(kind) or (("32px", sy) if kind == "cta" else (sy, sy))
        blocks.append({"type": btype, "data": b, "bg": bg, "kind": kind, "pad_t": pt, "pad_b": pb})

    # gap collapse: same-background neighbours share one gap; the cta keeps its own 32px top
    for prev, cur in zip(blocks, blocks[1:]):
        if prev["bg"] != cur["bg"] or {"bleed", "none", "footer"} & {prev["kind"], cur["kind"]}:
            continue
        if cur["kind"] == "cta":
            prev["pad_b"] = "0px"
        else:
            prev["pad_b"] = f"{max(px(prev['pad_b']), px(cur['pad_t']))}px"
            cur["pad_t"] = "0px"
    n_cta = sum(b["type"] == "cta" for b in blocks)
    if n_cta != 1:
        raise BuildError(f"{slug}: needs exactly one cta block (has {n_cta})")

    html_blocks = []
    for b in blocks:
        ctx = {**base, **b["data"], "pad_t": b["pad_t"], "pad_b": b["pad_b"],
               "bg": pal.get(b["bg"], pal["canvas"]), "bg_class": f"bg-{b['bg']}"}
        if b["bg"] == "accentband":  # style signature: hero copy on a full accent band
            ctx.update(bg=pal["accent"], bg_class="bg-accentband", ink=pal["on_btn"], ink2=pal["on_btn"], label_color=pal["on_btn"])
        html_blocks.append(f"<!-- {b['type']} -->\n" + render(lib[b["type"]]["tree"], ctx, f"{slug}.{b['type']}"))
    shell = parse((ROOT / "assets" / "shell.html").read_text(encoding="utf-8"))
    html = render(shell, {**base, "blocks": "\n".join(html_blocks)}, f"{slug}.shell")
    html = darken(html, pal)

    email_dir.mkdir(parents=True, exist_ok=True)
    (email_dir / "email.html").write_text(html, encoding="utf-8")
    if local:
        with zipfile.ZipFile(email_dir / "klaviyo-import.zip", "w", zipfile.ZIP_DEFLATED) as z:
            z.write(email_dir / "email.html", "email.html")
            for name in sorted(set(local)):
                z.write(img_dir / name, f"images/{name}")
    write_md(email, style_id, email_dir, brand["name"])
    (email_dir / "preview.html").write_text(preview_fill(html, brand["name"]), encoding="utf-8")
    findings = preflight.check_html(html, email_dir / "email.html", email["subject"], email["preheader"],
                                    sorted({v for v in pal.values() if isinstance(v, str)} | {band_orig, mix(pal['canvas'], pal['ink'], 0.08)}), spec.get("allow", []), spec.get("banned", []))
    return email_dir / "email.html", findings


def preview_fill(html, brand_name):
    """Review copy only (never import it): Klaviyo tags replaced with sample values, as Klaviyo's preview would."""
    html = re.sub(r"\{\{\s*(?:person\.)?first_name\|default:'([^']*)'\s*\}\}", r"\1", html)
    html = re.sub(r"\{\{\s*person\|lookup:'[^']*'\|default:'([^']*)'\s*\}\}", r"\1", html)
    html = html.replace("{{ organization.name }}", brand_name).replace("{{ organization.full_address }}", "123 Sample Street, City, ST 00000")
    html = re.sub(r"\{%\s*(unsubscribe_link|manage_preferences_link|web_view_link)\s*%\}", "#preview", html)
    html = re.sub(r"\{%\s*for item in event\.extra\.line_items\s*%\}(.*?)\{%\s*endfor\s*%\}", r"\1", html, flags=re.S)
    html = re.sub(r"\{\{\s*item\.product\.images\.0\.src\s*\}\}", "", html)
    html = re.sub(r"\{\{\s*item\.product\.title\s*\}\}", "Sample product", html)
    html = re.sub(r"\{\{\s*item\.quantity\s*\}\}", "1", html)
    html = re.sub(r"\{%\s*if item\.line_price\s*%\}.*?\{%\s*endif\s*%\}", "", html, flags=re.S)
    html = re.sub(r"\{%\s*coupon_code[^%]*%\}", "SAMPLECODE", html)
    return html.replace("<title>", "<title>PREVIEW ONLY: ", 1)


def write_md(email, style_id, email_dir, brand_name):
    lines = [f"# {email['slug']}: {email.get('idea', email.get('theme', ''))}",
             f"- Theme: {email.get('theme', '')}    - Style: {style_id}",
             f"- Audience: {email.get('audience', '')}    - Send: {email.get('send', '')}",
             f"- Klaviyo name: {email.get('klaviyo_name', brand_name + ' | Campaign | ' + email['slug'])}", ""]
    for i, s in enumerate(email["subject"]):
        lines.append(f"## Subject {'AB'[i] if i < 2 else i + 1} ({len(s)} chars): {s}")
    if email.get("ab_variable"):
        lines.append(f"A/B variable: {email['ab_variable']}")
    lines += [f"## Preview text ({len(email['preheader'])} chars): {email['preheader']}", "", "## Copy by block"]
    # readable copy for review: text fields quoted, links after "->", lists as sub-bullets; no src or layout noise
    hide = {"type", "url", "src", "layout", "columns", "image_right", "photo", "icon_src", "height", "stars"}
    clean = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(s).replace("&nbsp;", " "))).strip()

    def fields(d):
        return " / ".join(f'{k}: "{clean(v)}"' for k, v in d.items() if k not in hide and isinstance(v, str))

    for b in email["blocks"]:
        head = fields(b)
        lines.append(f"- [{b['type']}]" + (f" {head}" if head else "") + (f" -> {b['url']}" if b.get("url") else ""))
        for k, v in b.items():
            if k in hide or not isinstance(v, list):
                continue
            for x in v:
                sub = fields(x) if isinstance(x, dict) else f'"{clean(x)}"'
                lines.append(f"  - {k}: {sub}" + (f" -> {x['url']}" if isinstance(x, dict) and x.get("url") else ""))
    lines += ["", "## Sources for every fact in this email"]
    lines += [f"- \"{s['claim']}\" <- {s['source']}" for s in email.get("sources", [])] or ["- (none listed)"]
    (email_dir / "email.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------- scaffold ----------
F = lambda what: f"[[FILL: {what}]]"  # preflight A4 fails any left behind
ITEMS = {
    "products": lambda: [{"title": F("product title"), "price": F("price as shown"), "url": F("product url"), "src": F("image")}] * 2,
    "category_tiles": lambda: [{"title": F("collection"), "url": F("collection url"), "src": F("image")}] * 2,
    "steps": lambda: [{"title": F("step"), "text": F("one line")}] * 3,
    "reviews": lambda: [{"quote": F("real review"), "author": F("reviewer as shown")}],
    "trust_row": lambda: [{"text": F("real policy")}] * 2,
    "feature_grid": lambda: [{"title": F("feature"), "text": F("one line")}] * 3,
    "ingredients": lambda: [{"title": F("ingredient"), "text": F("what it does, as sourced")}] * 2,
    "stats_row": lambda: [{"value": F("real number"), "label": F("what it counts")}] * 3,
    "faq": lambda: [{"q": F("question"), "a": F("answer from the site")}] * 2,
    "link_list": lambda: [{"label": F("collection"), "url": F("url")}] * 3,
    "media_rows": lambda: [{"src": F("image"), "alt": F("alt"), "title": F("title"), "text": F("one line"), "url": F("url")}] * 2,
    "mosaic": lambda: [{"src": F("image"), "alt": F("alt"), "url": F("url")}] * 3,
    "press_strip": lambda: [{"name": F("real outlet")}] * 2,
    "social": lambda: [{"label": "Instagram", "url": F("profile url")}],
}


def scaffold(preset_key, occasion_id):
    data = lambda f: json.loads((ROOT / "data" / f).read_text(encoding="utf-8"))
    presets, occ, lib = data("presets.json"), data("occasions.json"), load_library()
    preset = presets.get(preset_key) or {}
    if not preset:
        import csv
        row = next((r for r in csv.DictReader((ROOT / "data" / "niches.csv").open()) if r["niche"].lower() == preset_key.lower()), None)
        if not row:
            raise BuildError(f"unknown preset or niche {preset_key!r}: use a data/presets.json key or a data/niches.csv niche")
        preset = {"style": row["styles"].split(",")[0].strip(), "niche": row["niche"]}
    o = next((g[occasion_id] for g in occ.values() if isinstance(g, dict) and occasion_id in g), None)
    if not o:
        ids = [k for g in occ.values() if isinstance(g, dict) for k in g]
        raise BuildError(f"unknown occasion {occasion_id!r}; one of: {', '.join(ids)}")
    steps = o.get("emails") or [{"job": o["angle"], "delay": o.get("when", ""), "skeleton": o["skeleton"]}]
    emails = []
    for i, st in enumerate(steps, 1):
        blocks = []
        for t in st["skeleton"]:
            blk = {"type": t, **{r: F(r) for r in lib[t]["req"] if r not in ("items", "rows")}}
            if t in ITEMS:
                blk["items"] = ITEMS[t]()
            if t == "comparison":
                blk["rows"] = [{"label": F("attribute"), "left": F("ours"), "right": F("theirs")}]
            if t == "header" and o.get("header") in ("split", "inverse", "nav"):
                blk["layout"] = "centered" if o["header"] == "nav" else o["header"]
                blk["links"] = [{"label": F("nav label"), "url": F("url")}] * 3
            if t == "footer":
                blk.update(layout=o.get("footer", "simple"), signup_reason=F("why they get this email"))
            blocks.append(blk)
        emails.append({"slug": f"{i:02d}-{occasion_id}", "theme": o.get("theme", occasion_id), "idea": st["job"],
                       "send": st.get("delay", ""), "subject": [F("subject A"), F("subject B")], "preheader": F("preview text"),
                       "blocks": blocks, "sources": [{"claim": F("each fact"), "source": F("url or asset")}]})
    fonts = preset.get("fonts", {})
    return {"_scaffold": {"preset": preset_key, "occasion": occasion_id, "needs": o.get("needs", []),
                          "angle": o.get("angle", ""), "sensitivity": o.get("sensitivity", ""), "popup": o.get("popup")},
            "style": preset["style"], "utm_prefix": F("short brand slug"),
            "brand": {"name": F("brand name"), "home_url": F("https://brand.com/"),
                      "heading_stack": f"'{fonts['heading']}', Georgia, serif" if fonts else F("heading stack"),
                      "body_stack": f"'{fonts['body']}', Helvetica, Arial, sans-serif" if fonts else F("body stack"),
                      **({"fonts_link": fonts["google"]} if fonts.get("google") else {}),
                      "palette": {"canvas": F("hex"), "ink": F("hex"), "accent": F("hex")}},
            "emails": emails}


# ---------- CLI ----------
def build(spec_path, out, styles_arg=None, quiet=False):
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    lib = load_library()
    defaults, styles = load_styles()
    out = Path(out)
    assets_dir = Path(spec.get("assets_dir") or Path(spec_path).parent)
    worst = "PASS"
    for email in spec["emails"]:
        style_id = email.get("style") or spec["style"]
        path, fs = build_email(spec, email, style_id, lib, defaults, styles, out, assets_dir)
        failed = any(l == "FAIL" for l, _, _ in fs)
        if not quiet:
            preflight.report(fs, path, False)
        worst = "FAIL" if failed else worst
        if styles_arg:
            for sid in (list(styles) if styles_arg == "all" else styles_arg.split(",")):
                try:
                    _, sfs = build_email(spec, dict(email, slug=f"{email['slug']}--{sid}"), sid, lib, defaults,
                                         styles, out / "_styles", assets_dir)
                except BuildError as err:
                    print(f"  style preview {sid}: skipped, {str(err).splitlines()[0]}")
                    continue
                if any(l == "FAIL" for l, _, _ in sfs):
                    worst = "FAIL"
                    print(f"  style preview {sid}: FAIL {[m for l, _, m in sfs if l == 'FAIL']}")
    return worst


def self_test():
    spec = ROOT / "assets" / "example.spec.json"
    _, styles = load_styles()
    with tempfile.TemporaryDirectory() as tmp:
        assert build(spec, tmp, "all", quiet=True) == "PASS", "example spec should PASS in every style"
        for sid in styles:
            html = next(Path(tmp, "_styles").glob(f"*--{sid}/email.html")).read_text()
            assert "[[" not in html, f"style {sid}: unfilled token"
        bad = json.loads(spec.read_text())
        hero = next(b for b in bad["emails"][0]["blocks"] if b["type"] == "hero_text")
        hero.pop("headline")
        p = Path(tmp, "bad.json")
        p.write_text(json.dumps(dict(bad, assets_dir=str(spec.parent))))
        try:
            build(p, Path(tmp, "bad"), quiet=True)
            raise AssertionError("missing required field was not caught")
        except BuildError as e:
            assert "needs" in str(e), e
        try:
            render(parse("[[nope]]"), {}, "t")
            raise AssertionError("missing token was not caught")
        except BuildError:
            pass
        assert glue("Shop the Harbor Mug") == "Shop the Harbor&nbsp;Mug"
    assert glue("A treat for {{ person|lookup:'Pet name'|default:'your cat' }}") == "A treat&nbsp;for {{ person|lookup:'Pet name'|default:'your cat' }}" or "{{ person|lookup:'Pet name'|default:'your cat' }}" in glue("A treat for {{ person|lookup:'Pet name'|default:'your cat' }}")
    print(f"build self-test PASS ({len(styles)} styles built from the example spec, all preflight clean)")


def main():
    a = sys.argv[1:]
    if a[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    if not a:
        sys.exit(__doc__)
    try:
        if a[0] == "--self-test":
            self_test()
            return 0
        if a[0] == "--scaffold":
            print(json.dumps(scaffold(a[1], a[2]), indent=1, ensure_ascii=False))
            return 0
        if a[0] == "--list":
            _, styles = load_styles()
            print("STYLES")
            for k, v in styles.items():
                print(f"  {k:15} {v['name']:18} canvas={v['canvas']:5} best for: {v['best_for']}")
            print("BLOCKS")
            for k, v in load_library().items():
                print(f"  {k:15} bg={v['bg']:6} pad={v['pad']:8} required: {', '.join(v['req']) or '-'}")
            return 0
        out = a[a.index("--out") + 1] if "--out" in a else "margarita-out"
        styles_arg = a[a.index("--styles") + 1] if "--styles" in a else None
        return 1 if build(a[0], out, styles_arg) == "FAIL" else 0
    except BuildError as e:
        print(f"BUILD ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
