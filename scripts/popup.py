#!/usr/bin/env python3
"""Margarita popups: mockups and Klaviyo build sheets for native sign-up forms.

Usage: popup.py spec.json --out DIR

Reads the spec's "popups" list (brand, palette and style come from the same spec) and writes, per
popup, DIR/popups/<slug>/mockup.html (desktop over a dimmed page, phone, every step, success and
teaser) and DIR/popups/<slug>/build-sheet.md (the exact settings to enter in Klaviyo's form editor).
These are designs for Klaviyo's form builder, not code for the site. Exit 1 when a check fails.
Stdlib only.
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PRESETS = json.loads((ROOT / "data" / "popups.json").read_text(encoding="utf-8"))


def check(p, preset):
    """Copy and compliance checks; returns a list of (level, message)."""
    f = []

    def need(k, why):
        if not p.get(k):
            f.append(("FAIL", f"{k} is required: {why}"))
    need("headline", "every form opens with one")
    need("button", "the submit label")
    need("success_headline", "the success step")
    if "real offer" in preset.get("needs", []):
        need("offer", "this preset only exists for a real offer")
        need("terms", "an offer without terms is not an offer")
    if p.get("sms_headline") or p["preset"] == "sms-two-step":
        need("sms_disclosure", "Klaviyo requires disclosure language wherever SMS consent is collected")
    if p.get("countdown_to") and not re.search(r"\d", str(p["countdown_to"])):
        f.append(("FAIL", "countdown_to must be a real date"))
    if p["preset"] == "preference-quiz" and len(p.get("options") or []) < 3:
        f.append(("FAIL", "the quiz needs 3 to 4 real options"))
    for k in ("label", "headline", "subhead", "button", "success_headline", "success_text", "decline", "terms", "teaser"):
        v = str(p.get(k) or "")
        if re.search(r"[–—]", v):
            f.append(("FAIL", f"{k} has an em or en dash"))
        if re.search(r"[‘’“”]", v):
            f.append(("FAIL", f"{k} has curly quotes"))
        if re.search(r"!{2,}", v):
            f.append(("FAIL", f"{k} stacks exclamation points"))
    if len(str(p.get("headline", "")).split()) > 9:
        f.append(("WARN", "headline over 9 words; a popup is read in two seconds"))
    if len(str(p.get("button", "")).split()) > 4:
        f.append(("WARN", "button over 4 words"))
    if re.search(r"(?i)\bi (hate|don't like|prefer paying)", str(p.get("decline", ""))):
        f.append(("WARN", "decline link shames the visitor; use a plain 'No thanks'"))
    return f


def card(p, tok, pal, fonts, step, mobile):
    """One form step as static HTML: a picture of the Klaviyo form, not a working form."""
    pill = tok["radius"] == "999px"
    box_r = "16px" if pill or build.px(tok["radius"]) >= 8 else "2px"
    head = (f"font-family:{fonts[0]};font-weight:{tok['heading_weight']};text-transform:{tok['heading_case']};"
            f"letter-spacing:{tok['heading_tracking']};color:{pal['ink']};")
    body = f"font-family:{fonts[1]};color:{pal['ink2']};"
    border = f"border:1px solid {pal['ink']};" if tok.get("btn_border") or pal.get("btn_border") else "border:0;"
    btn = (f"display:block;width:100%;box-sizing:border-box;padding:15px 18px;{border}border-radius:{tok['radius']};"
           f"background:{pal['btn_bg']};color:{pal['on_btn']};font-family:{fonts[1]};font-size:{tok['btn_size']};font-weight:700;"
           f"letter-spacing:{tok['btn_tracking']};text-transform:{tok['btn_case']};text-align:center;")
    field = (f"display:block;width:100%;box-sizing:border-box;padding:14px;margin:0 0 20px;border:1px solid {pal['border']};"
             f"border-radius:{'999px' if pill else '4px'};background:{pal['canvas']};color:{pal['ink2']};font-family:{fonts[1]};font-size:15px;")
    # same last-two-word glue as the emails, so no form line ends on one word
    e = lambda k: build.glue(html.escape(str(p.get(k) or ""))).replace("&amp;nbsp;", "&nbsp;")
    inner = []
    if step == "success":
        inner.append(f'<p style="margin:0 0 10px;{head}font-size:{"26px" if mobile else "30px"};line-height:1.15;">{e("success_headline")}</p>')
        if p.get("success_text"):
            inner.append(f'<p style="margin:0 0 18px;{body}font-size:15px;line-height:1.55;">{e("success_text")}</p>')
        if p.get("code"):
            inner.append(f'<div style="margin:0 0 16px;padding:14px;border:1px dashed {pal["ink"]};text-align:center;{head}font-size:24px;letter-spacing:4px;">{e("code")}</div>')
        inner.append(f'<div style="{btn}">{e("success_button") or ("Back to the site" if p["preset"] in ("launch-waitlist", "holiday-early-access") else "Start shopping")}</div>')
    elif step == "sms":
        inner.append(f'<p style="margin:0 0 10px;{head}font-size:24px;line-height:1.2;">{e("sms_headline") or "Want texts too?"}</p>')
        inner.append(f'<div style="{field}">Phone number</div><div style="{btn}">{e("sms_button") or "Sign me up"}</div>')
        inner.append(f'<p style="margin:12px 0 0;{body}font-size:10px;line-height:1.45;">{e("sms_disclosure")}</p>')
        inner.append(f'<p style="margin:12px 0 0;text-align:center;{body}font-size:13px;text-decoration:underline;">Skip</p>')
    elif step == "question":
        inner.append(f'<p style="margin:0 0 16px;{head}font-size:24px;line-height:1.2;">{e("question")}</p>')
        inner += [f'<div style="{field}">&#9675;&nbsp; {html.escape(o)}</div>' for o in p.get("options") or []]
        inner.append(f'<div style="{btn}">Next</div>')
    else:
        if p.get("label"):
            inner.append(f'<p style="margin:0 0 12px;font-family:{fonts[1]};font-size:{tok["label_size"]};font-weight:700;letter-spacing:{tok["label_tracking"]};text-transform:{tok["label_case"]};color:{pal["accent_text"]};">{e("label")}</p>')
        inner.append(f'<p style="margin:0 0 12px;{head}font-size:{"28px" if mobile else "34px"};line-height:1.12;">{e("headline")}</p>')
        if p.get("subhead"):
            inner.append(f'<p style="margin:0 0 20px;{body}font-size:15px;line-height:1.55;">{e("subhead")}</p>')
        if p.get("countdown_to"):
            inner.append(f'<p style="margin:0 0 4px;{body}font-size:13px;">Opens {e("countdown_to")}</p>'
                         f'<p style="margin:0 0 18px;{head}font-size:26px;letter-spacing:2px;">02d : 14h : 08m</p>')
        label = "Birthday (MM/DD)" if p["preset"] == "birthday-capture" else "Email address"
        inner.append(f'<div style="{field}">{label}</div>')
        if p.get("age_gate"):
            inner.append(f'<p style="margin:0 0 12px;{body}font-size:13px;">&#9744;&nbsp; I confirm I am {e("age_gate")} or older</p>')
        inner.append(f'<div style="{btn}">{e("button")}</div>')
        if p.get("terms"):
            inner.append(f'<p style="margin:12px 0 0;{body}font-size:11px;line-height:1.45;">{e("terms")}</p>')
        if p.get("decline"):
            inner.append(f'<p style="margin:14px 0 0;text-align:center;{body}font-size:13px;text-decoration:underline;">{e("decline")}</p>')
    form = f'<div style="padding:{"28px 24px" if mobile else "44px 40px"};">{"".join(inner)}</div>'
    img = p.get("image") and not mobile and step in ("email", "question")
    close = f'<div style="position:absolute;top:10px;right:12px;width:32px;height:32px;line-height:32px;text-align:center;font:20px Arial;color:{pal["ink"]};">&#215;</div>'
    width = "335px" if mobile else ("720px" if img else "440px")
    grid = (f'<div style="display:grid;grid-template-columns:1fr 1fr;"><div style="background:{pal["band"]} url(\'{html.escape(p["image"])}\') center/cover;min-height:440px;"></div>{form}</div>'
            if img else form)
    if p["_type"] == "full page" and not mobile:
        width = "100%"
    return (f'<div style="position:relative;width:{width};max-width:100%;background:{pal["canvas"]};border:1px solid {pal["border"]};'
            f'border-radius:{box_r};overflow:hidden;box-shadow:0 18px 60px rgba(0,0,0,.25);">{close}{grid}</div>')


def frame(title, content, w, h, page_bg, kind="popup", mobile=False):
    """A faux page with the form placed the way Klaviyo shows that form type."""
    place = {"popup": "align-items:center;justify-content:center;",
             "flyout": "align-items:flex-end;justify-content:center;" if mobile else "align-items:flex-end;justify-content:flex-end;padding:24px;",
             "full page": "align-items:stretch;justify-content:stretch;padding:0;",
             "embed": "align-items:center;justify-content:center;"}.get(kind, "align-items:center;justify-content:center;")
    overlay = "" if kind in ("embed", "flyout") and not mobile else '<div style="position:absolute;inset:0;background:rgba(20,20,20,.45);"></div>'
    lines = "".join(f'<div style="position:absolute;left:24px;right:24px;top:{30 + i * 26}px;height:10px;border-radius:5px;background:rgba(0,0,0,.08);"></div>' for i in range(5))
    return (f'<figure style="margin:0;max-width:100%;overflow-x:auto;"><figcaption style="font:600 13px system-ui;margin:0 0 8px;color:#55534e;">{title}</figcaption>'
            f'<div style="width:{w}px;height:{h}px;box-sizing:border-box;border-radius:10px;background:{page_bg};display:flex;{place}'
            f'position:relative;overflow:hidden;">{lines}{overlay}<div style="position:relative;display:flex;{"width:100%;" if kind == "full page" or (mobile and kind == "flyout") else ""}">{content}</div></div></figure>')


def build_sheet(brand, preset, p, style_id, tok, pal, fonts, findings):
    rows = [("Form type", preset["type"]), ("List", preset["list"]), ("Show form", preset["timing"]),
            ("Frequency", preset["frequency"]), ("Targeting", preset["targeting"]), ("Teaser", p.get("teaser") or preset["teaser"]),
            ("Style", f"{style_id}: corner radius {tok['radius']}, {tok['btn_case']} button text, fonts {fonts[0]} / {fonts[1]}"),
            ("Colors", f"background {pal['canvas']}, text {pal['ink']}, secondary {pal['ink2']}, button {pal['btn_bg']} with {pal['on_btn']} text, fields {pal['border']}")]
    copy = [("Age gate", p.get("age_gate") and f"Age gate input: {p['age_gate']}+"), ("Label", p.get("label")), ("Headline", p.get("headline")), ("Subhead", p.get("subhead")), ("Button", p.get("button")),
            ("Offer", p.get("offer")), ("Terms", p.get("terms")), ("Decline link", p.get("decline")), ("Countdown to", p.get("countdown_to")),
            ("Question", p.get("question")), ("Options", ", ".join(p.get("options") or []) or None),
            ("SMS headline", p.get("sms_headline")), ("SMS disclosure", p.get("sms_disclosure")),
            ("Success headline", p.get("success_headline")), ("Success text", p.get("success_text")), ("Coupon", p.get("code"))]
    md = [f"# {brand['name']}: {preset['name']} ({preset['type']})", "", f"Use when: {preset['use_when']}.", "",
          "## Klaviyo settings", "| Setting | Value |", "|---|---|"] + [f"| {k} | {v} |" for k, v in rows]
    md += ["", "## Steps (Klaviyo form editor)"]
    md += [f"{i}. **{s['name']}**: " + ", ".join(s["components"]) for i, s in enumerate(preset["steps"], 1)]
    md += [f"{len(preset['steps']) + 1}. **Success**: {preset['success']}", "", "## Copy", "| Field | Text |", "|---|---|"]
    md += [f"| {k} | {v} |" for k, v in copy if v]
    md += ["", "## Mobile (Klaviyo guidance)", "- Keep the side image set to Desktop so phones get the form only.",
           "- Turn off 'Click outside form to close' on mobile; make the close icon easy to tap.",
           "- Keep side margins so the popup does not run edge to edge; flyouts dock to the bottom.",
           "- On pages that rank in organic search, use a time delay so the form does not cover content at once.",
           "", "## Checks"] + ([f"- {l}: {m}" for l, m in findings] or ["- PASS: copy and compliance checks"])
    return "\n".join(md) + "\n"


def main():
    a = sys.argv[1:]
    if a[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    if not a:
        sys.exit(__doc__)
    spec_path = Path(a[0])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    out = Path(a[a.index("--out") + 1]) if "--out" in a else spec_path.parent
    defaults, styles = build.load_styles()
    brand = spec["brand"]
    worst = 0
    for p in spec.get("popups") or []:
        if p.get("preset") not in PRESETS:
            sys.exit(f"unknown popup preset {p.get('preset')!r}; one of {', '.join(k for k in PRESETS if k != '_doc')}")
        preset = PRESETS[p["preset"]]
        style_id = p.get("style") or spec["style"]
        tok = {**defaults, **styles[style_id]["tokens"]}
        pal = build.derive_palette(dict(brand["palette"]), lambda _: None)
        build.button_colors(pal, tok)
        fonts = (brand["heading_stack"], brand["body_stack"])
        findings = check(p, preset)
        steps = ["question", "email"] if p["preset"] == "preference-quiz" else ["email"] + (["sms"] if p.get("sms_disclosure") else [])
        kind = preset["type"]
        p["_type"] = kind
        page = build.mix(pal["canvas"], pal["ink"], 0.12)  # the faux page behind the form, never the form's own color
        phone_note = " (side image hidden, as Klaviyo\u00a0advises)" if p.get("image") else ""
        figs = [frame(f"Desktop: {kind}, first step", card(p, tok, pal, fonts, steps[0], False), 900, 580, page, kind),
                frame(f"Phone: first step{phone_note}", card(p, tok, pal, fonts, steps[0], True), 375, 720, page, kind, True)]
        figs += [frame(f"Phone: {st} step", card(p, tok, pal, fonts, st, True), 375, 720, page, kind, True) for st in steps[1:]]
        figs.append(frame("Phone: success step", card(p, tok, pal, fonts, "success", True), 375, 720, page, kind, True))
        if p.get("teaser"):
            t = (f'<div style="padding:12px 18px;border-radius:999px;background:{pal["btn_bg"]};color:{pal["on_btn"]};'
                 f'font:700 13px {fonts[1]};">{html.escape(p["teaser"])}</div>')
            figs.append(frame("Teaser (reopens the form)", t, 375, 200, page, "embed"))
        d = out / "popups" / p["slug"]
        d.mkdir(parents=True, exist_ok=True)
        if p.get("image") and "://" not in p["image"]:  # the mockup loads it by bare filename
            src = spec_path.parent / (spec.get("assets_dir") or ".") / p["image"]
            if not src.is_file():
                sys.exit(f"popup image not found: {src}")
            shutil.copy2(src, d / Path(p["image"]).name)
            p = dict(p, image=Path(p["image"]).name)
        fl = brand.get("fonts_link")
        title = f"{html.escape(brand['name'])}: {html.escape(preset['name'])}"
        (d / "mockup.html").write_text(
            '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{title} form mockup</title>' + (f'<link rel="stylesheet" href="{html.escape(fl)}">' if fl else "")
            + '</head><body style="margin:0;padding:28px;background:#f4f2ee;font-family:system-ui;">'
            f'<h1 style="font:650 18px system-ui;margin:0 0 4px;">{title} ({preset["type"]})</h1>'
            '<p style="margin:0 0 22px;color:#6b6a66;font-size:13px;">Mockup of a Klaviyo sign-up form. Build it in Klaviyo from build-sheet.md; this page is not a working&nbsp;form.</p>'
            f'<div style="display:flex;flex-wrap:wrap;gap:28px;align-items:flex-start;">{"".join(figs)}</div></body></html>', encoding="utf-8")
        (d / "build-sheet.md").write_text(build_sheet(brand, preset, p, style_id, tok, pal, fonts, findings), encoding="utf-8")
        status = "FAIL" if any(l == "FAIL" for l, _ in findings) else "PASS"
        print(f"{status}  {d}  ({preset['name']}, {preset['type']})")
        for l, m in findings:
            print(f"  {l} {m}")
        worst = max(worst, int(status == "FAIL"))
    return worst


if __name__ == "__main__":
    sys.exit(main())
