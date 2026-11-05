---
name: margarita
description: >
  This skill should be used when the user wants finished, send-ready marketing emails for a specific
  brand, usually with a brand URL, an asset folder or hex colors: "make a launch email for <brand>",
  "sale campaign from this link and these photos", "welcome series for <url> in these colors",
  "Klaviyo-ready template for this brand", "winback email for <brand>", "show me email styles for my
  candle shop". Covers 56 niches and 13 visual styles. Delivers subjects A/B, preview text, on-voice
  copy, client-safe HTML with Klaviyo tags, an import zip and notes on inferred brand elements and
  compliance. Prefer it over general email-marketing skills when the deliverable is the finished brand email
  itself. Not for campaign calendars
  or strategy, flow, segment or Liquid logic, fixing existing HTML or MJML, SaaS onboarding
  sequences, cold outreach or transactional mail.
---

# Margarita

Marketing email with taste: the Margarita library's evidence on what curated DTC brands send (block
order, subject habits, flow timing) plus a templating engine with 13 styles and 31 blocks, turned
into finished emails a person can import into Klaviyo and send.

Version 2.2 (2026-11-05). Record it in notes.md. This skill is self-contained and works in any agent
that reads `SKILL.md` skills (Claude Code, Claude.ai, Google Antigravity). Every path below is
relative to this skill's folder, the folder that holds this file (for example
`~/.claude/skills/margarita/` or `~/.gemini/config/skills/margarita/`).

## Inputs

| Input | Required | If missing |
|---|---|---|
| Brand link | One of link / assets is needed | Work from the assets and brief; every voice and product cue becomes `[inferred]` |
| Asset folder | | Use the site's https images; no images at all means text-led blocks and a letter or text-only style |
| Palette (hex) | Yes in spirit | Take the colors the site uses and log them as `[inferred] palette from site`. Never pick your own |
| Brief, campaign type, audience, style, offer, banned words, output folder | No | Decide per `references/campaign-selection.md` and note each decision |

Stop and ask only when there is neither a link, nor assets, nor a brief that names the brand.
Otherwise deliver, and list what the user should adjust.

## Setup (not optional)

Print this line as soon as intake (step 2) has the facts, before writing any copy, and reprint it
if anything changes:

```
MARGARITA_PREFLIGHT: link=<ok via firecrawl|ok via webfetch|ok via browser|unreachable: reason> assets=<N files, N usable images> palette=<N colors> niche=<niches.csv row> style=<id> library_mcp=<available|absent>
```

## The laws (enforced by `scripts/build.py`, `scripts/preflight.py` or the fact log)

1. **Facts come from sources.** Products, prices, offers, codes, deadlines, stock, reviews, stats and
   policies come from the link, the assets or the brief, verbatim. Missing fact: drop the line or the
   block (the build refuses a block without its required fields). Every claim is listed with its
   source in the spec's `sources`, which lands in `email.md`.
2. **The palette is law.** Every color in the HTML is a supplied color (A17); the build refuses
   palette roles that fail 4.5:1 contrast. Neutrals the palette lacks are added only per
   `references/brand-intake.md` section 3, listed in the spec's `allow` and logged.
3. **One email, one idea, one primary CTA** (the build refuses zero or two `cta` blocks). 3 to 6 body blocks.
4. **Klaviyo-correct.** URL-only legal tags in `href`, `{{ organization.full_address }}`, every
   `first_name` with a default, balanced tags, no foreign merge syntax (built into the blocks; A1, A2, A13).
5. **Client-safe and mobile-first.** Tables, inline styles, bulletproof VML button, 620px breakpoint,
   48px taps, no SVG/script/forms/absolute positioning, under 102 KB (A6, A8, A9, A16, render.py).
6. **Readable with images off.** Live-text headlines and offers, styled descriptive alt, bgcolor on
   image cells (A14, render.py images-off).
7. **House style.** No em or en dashes, straight quotes, no stacked `!!`, no orphan words, 28-32px
   above the CTA, no cramped stacks (A11, B, render.py, screenshot review).
8. **Sounds like the brand.** Match the voice samples; cut filler (`references/copy.md` section 1).
9. **The niche's compliance column holds.** Alcohol, supplements, CBD, finance, kids, eco and other
   regulated claims follow `data/niches.csv` `compliance`.

## Workflow

| Step | Do | Read |
|---|---|---|
| 1 | Read the request: link, asset folder, palette, brief, output folder | |
| 2 | **Intake**, then print the setup line. Fetch the link (Firecrawl if installed, else the agent's web fetch or browser; pages saved to `.source/`), inventory the asset folder, map the palette to roles with contrast checks. Start `notes.md` with the brand profile and the inferred list | `references/brand-intake.md` |
| 3 | **Decide** niche (`data/niches.csv`, or a saved preset in `data/presets.json`), occasion (`data/occasions.json`), style, number of emails, audience, playbook. Check `library/INDEX.md` (or `scripts/library.py find --niche <x> --occasion <y>`) for a matching example and its block order. Start the spec with `build.py --scaffold <preset or niche> <occasion>`. One-line assumption each in notes.md | `references/campaign-selection.md` (sections 1, 3, 3b), `data/styles.json`, `data/themes.csv`, `data/industry_playbooks.json` |
| 4 | **Optional:** if a Margarita library MCP (tools `search_emails`, `search_components`) is connected, look up 2 to 3 reference emails by niche and intention for layout cues only | `references/campaign-selection.md` section 6 |
| 5 | **Write** per email: subject A and B, preview text, the copy for each block, alt text, CTA label, sources | `references/copy.md` |
| 6 | **Build.** Put it all in `<out>/<brand-slug>/spec.json` and run `scripts/build.py`. It renders, copies images, zips, writes `email.md` and runs preflight. Fix the spec until every email PASSes; never hand-edit `email.html` | `references/spec.md`, `references/layout.md`, `references/klaviyo.md` |
| 7 | **Check.** `scripts/render.py` on each email until PASS (680px, 375px, 320px, images-off, dark mode: overflow, orphans, broken images, button height, text lost in dark mode, console errors), then look at the screenshots yourself. If the user's own instructions require a design-QA subagent, spawn it now and report its verdict | `references/layout.md` section 8, `data/rules.csv` |
| 8 | **Popups** (when asked, or when the occasion names one): add `popups` to the spec and run `scripts/popup.py` for mockups and Klaviyo build sheets | `references/popups.md`, `data/popups.json` |
| 9 | **Package and report** (below) | `references/klaviyo.md` sections 6 and 7 |

```bash
S=<this skill's folder>/scripts                                    # e.g. ~/.claude/skills/margarita/scripts
python3 $S/build.py <out>/<brand>/spec.json --out <out>/<brand>              # build + preflight
python3 $S/build.py <out>/<brand>/spec.json --out <out>/<brand> --styles a,b  # style options in _styles/
python3 $S/render.py <out>/<brand>/01-<theme>/email.html                       # render check
python3 $S/gallery.py <out>/<brand>                                            # one page with every email
```

Any build error or preflight FAIL blocks delivery. Each WARN is fixed or explained in notes.md.
Other tools: `build.py --list` (styles and blocks), `preflight.py contrast "#a" "#b"`, and the
self-tests `build.py --self-test` and `preflight.py --self-test`. render.py needs Playwright
(`pip install playwright`); if it cannot run, say so in notes.md and do the screenshot review in a
browser instead.

**When the user wants to choose a look** ("show me options"): first show the matching previews from
`library/INDEX.md`: the style tour shows one email in all 13 styles, and each niche entry shows its
primary and alternate style. No build is needed for that. Then build the first real email with
`--styles` set to the 2 or 3 styles they liked, run `gallery.py`, show the gallery, and continue with
their pick. Library entries are fictional demos: borrow structure and look, never their facts.

## Output

```
<out>/<brand-slug>/          <out> = the folder the user named, else ./margarita-out
  .source/                   pages read during intake (evidence for the fact log)
  spec.json                  the single source for every email below
  notes.md                   brand profile, inferred elements, assumptions, compliance flags,
                             preflight + render results, Klaviyo import checklist, skill version
  gallery.html               optional: every email at desktop and phone width, plus popup mockups
  popups/<slug>/             mockup.html and build-sheet.md for each Klaviyo sign-up form
  01-<theme>/
    email.html               Klaviyo-ready template (the file to import)
    preview.html             review copy with sample values for Klaviyo tags; never import it
    email.md                 subjects A/B, preview text, copy by block, fact sources
    images/                  local assets used (omitted if every image is hosted)
    klaviyo-import.zip       email.html + images/ (omitted if every image is hosted)
  02-<theme>/ ...
```

Final reply to the user, short:
1. One line per email: `NN theme: Subject A / Preview text` and the email folder path.
2. **Inferred brand elements** to verify (from notes.md, bullets).
3. **Compliance flags**: build and preflight status per email, any WARN kept and why, the niche's
   compliance notes, anything Klaviyo must have set (organization address, coupon, event variables).
4. **Assumptions** the user can change (niche, style, campaign type, audience, number of emails).

## Files

| File | What it holds |
|---|---|
| `references/brand-intake.md` | Link, asset and palette intake; palette roles; fonts; notes.md brand template |
| `references/campaign-selection.md` | Defaults for type and audience, taxonomy, block order by theme with library evidence, choosing the style, flows, scoring |
| `references/copy.md` | Voice matching, subject and preview rules with theme habits, body and CTA rules, house style |
| `references/spec.md` | spec.json format and every block's fields |
| `references/layout.md` | Taste rules, mobile, spacing, images-off, client safety, dark mode, orphans, render check |
| `references/klaviyo.md` | Verified legal and personalization tags, event variables, UTM, import zip, send checklist |
| `data/styles.json` | 13 styles: shape, type scale, rhythm, alignment, hidden blocks, fallback fonts (never colors) |
| `data/niches.csv` | 56 niches in 10 groups: keywords, library evidence, best styles, playbook, compliance |
| `data/presets.json` | 10 saved niche presets from the approved demos: style, alternate, fonts, palette approach, skeleton, header and footer |
| `data/occasions.json` | Calendar, product and relationship moments plus 5 flows: skeleton, needs, angle, timing, sensitivity, matching popup |
| `data/popups.json`, `references/popups.md` | 8 Klaviyo sign-up form presets and the popup rules |
| `data/themes.csv`, `data/rules.csv`, `data/industry_playbooks.json` | Theme openers and subject habits, the rules index, 8 playbooks (voice, banned phrases, button shape, photo rules) |
| `assets/shell.html`, `assets/blocks.html` | Email shell and the 31-block library in the engine's `[[ ]]` syntax |
| `library/INDEX.md`, `library/index.json` | The bundled example library: fictional demo brands by niche, occasion and style, each with a spec (`library/specs/`) and a preview (`library/previews/`), plus a style tour of all 13 styles |
| `assets/example.spec.json`, `assets/example.html` | Fixture spec covering every block; a built email that passes preflight |
| `scripts/build.py` | Templating engine: spec.json to emails, images, zip, email.md, preflight |
| `scripts/preflight.py` | The linter (stdlib) |
| `scripts/render.py` | Render check with screenshots (Playwright) |
| `scripts/gallery.py` | Preview page of every built email and popup (stdlib) |
| `scripts/popup.py` | Popup mockups and Klaviyo build sheets (stdlib) |
| `scripts/library.py` | `find` queries the library (stdlib); `index` rebuilds its previews, index.json and INDEX.md (Playwright) |
