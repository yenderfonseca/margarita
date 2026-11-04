# Brand intake: link + assets + palette -> brand profile

Doctrine: **a missing fact stays missing.** Read what
exists, derive only what the inputs force, and log everything that was not read directly.

Write the profile into `notes.md` as you go (sections below). Every line carries a source tag:
`[site]` read from the link, `[asset]` from the folder, `[brief]` stated by the user,
`[derived]` computed from those (say from what), `[inferred]` a judgment call the user should check.

## 1. The link

Fetch in this order, stop at the first that works:
1. **Firecrawl CLI**, if installed (check `firecrawl --status`). Shopify storefronts often
   answer plain fetchers with HTTP 429; Firecrawl gets through. Save every page as evidence for the
   fact log:
   ```bash
   firecrawl scrape "<url>" --format markdown,links,images,branding -o <out>/<brand-slug>/.source/home.json
   firecrawl scrape "<url>/products.json?limit=12" -o <out>/<brand-slug>/.source/products.json   # Shopify: titles, prices, image URLs, handles
   firecrawl scrape "<product or collection url>" --only-main-content -o <out>/<brand-slug>/.source/<page>.md
   ```
   `branding` returns the site's fonts, colors and logo: use the fonts and logo; the colors are only
   a cross-check, never a replacement for the supplied palette. Budget about 6 scrapes per brand
   (credits are metered; concurrency is limited, so run at most 2 at once).
2. The agent's own web fetch tool, if Firecrawl is not installed or not authenticated.
3. A browser tool (Chrome or Playwright MCP), if connected.

Record `link=ok` or `link=unreachable (<reason>)` in the preflight line.

**Unreachable link** (DNS fails, every route errors, or the page is empty): stop retrying after one
attempt per route. Then: voice comes from the brief and asset filenames, tagged `[inferred]`; no
products, prices, policies or reviews exist, so use text-led blocks (hero_text, story, cta, steps);
every link in the email points at the given domain and notes.md flags "confirm the domain resolves
before sending" (preflight warns on reserved test domains).

Pull, with the exact source page:

| Cue | Where to look | Keep |
|---|---|---|
| Voice | Hero headline, About page, product descriptions, policy pages | 3 to 5 verbatim sentences as voice samples. Note: sentence length, person ("we"/"you"), formality, humor, emoji yes/no, caps habits, brand words they repeat |
| Typography | `font-family` in CSS, Google Fonts or Typekit `<link>`, `@font-face` names | Display font and body font names. Classify each as serif / sans / mono / script |
| Imagery | Hero and product photos | Light or dark, studio or lifestyle, crop ratio (4:5, 1:1, 16:9), people or product only, props, texture |
| Products | Product pages or `products.json` | Title, price with currency as displayed, URL, main image URL. Only products that have all four |
| Offers | Announcement bar, popup copy, `/pages/*` | The exact offer text and code, plus its terms. No offer found means there is no offer |
| Policies | Footer, shipping and returns pages | Free-shipping threshold, returns window, warranty, made-in claims, as worded |
| Proof | Product reviews, press bar | Verbatim quotes with the reviewer name and rating as shown; press names as shown |
| Social | Footer links | Instagram, TikTok, etc. URLs |

Never: invent a product, round or convert a price, merge two reviews, attribute a quote, imply a
discount, or infer a policy from "most stores do this".

## 2. The asset folder

Inventory every file (`ls -la`, then `sips -g pixelWidth -g pixelHeight <file>` on macOS or
`python3 -c` with `struct` reading PNG/JPEG headers):

| Column | Use |
|---|---|
| file, px size, aspect | Hero needs width >= 1200px (2x for 600px). Product cards need >= 480px |
| role | `logo` (filename has logo/wordmark/mark, or transparent PNG/SVG with wide aspect), `product`, `lifestyle`, `texture`, `icon` |
| transparency | Transparent logos need a dark-mode plan (layout.md section 6) |
| format | JPG/PNG/GIF ship. SVG does not render in Gmail/Outlook: rasterize it to PNG at 2x with `rsvg-convert -w 280 logo.svg -o logo.png` (or `qlmanage -t -s 600`, which pads to a square: crop it) and log it |
| logo size | Ship the logo at 2x its display width (140px display: 280px file). If the file has wide transparent padding (square thumbnails), crop to the artwork first, or the logo renders tiny |

Look at the key images (Read the image file) before choosing a hero: the subject should survive a
600px crop and a 375px phone width.

Image source priority for each slot: asset folder file (ships in `images/` inside the Klaviyo zip)
> https image URL from the site > drop the block. Never hotlink an image you did not see.

## 3. The palette: map supplied colors to roles

The supplied colors are law. The industry playbook palettes in `data/industry_playbooks.json` are
**never** used; take only voice, type, button shape and photography rules from them.

Roles (the spec's `brand.palette` keys). Only `canvas`, `ink` and `accent` are required: `build.py` derives
every missing role by mixing those three (no new hue), repairs a small-label accent toward ink until
4.5:1, prints each as `[derived]` for notes.md, and refuses roles that still fail contrast. Set a role
yourself when the palette has a real color for it:

| Role | Pick |
|---|---|
| `canvas` | Lightest supplied color the brand uses as a page background (or the darkest, for a dark brand site) |
| `page` | `canvas`, or a second light color to frame it |
| `band` | A second background from the palette for alternating sections; else `canvas` |
| `ink` | The color with the highest contrast on `canvas` (must be >= 4.5:1) |
| `ink2` | A softer supplied neutral that has >= 4.6:1 on `canvas` AND `band` (keep a margin over 4.5). Never the accent; if no neutral qualifies, `ink2` = `ink` |
| `accent` | The most saturated or brand-signature color. Button fill, labels |
| `on_accent` | Whichever of `canvas`/`ink` has the higher contrast on `accent` (>= 4.5:1) |
| `border` | A supplied color that differs from `canvas` and stays subtle (about 1.2:1 to 3:1 on `canvas`); else `ink2`. Never equal to `canvas` (an invisible divider) |
| `dark_bg` / `dark_text` | The darkest and lightest supplied colors (swap of `ink` and `canvas` is the default) |
| `dark_text2` (optional) | A second light color for secondary text in dark mode; else `dark_text` |

Check every text pair with `python3 scripts/preflight.py contrast "#a" "#b"`.

When the palette cannot satisfy a role:
1. Re-assign within the palette first (e.g. use `ink` for labels when `accent` fails on `canvas`).
2. Still short (e.g. the palette has no light color at all): use pure `#FFFFFF` or `#000000` as the
   neutral, pass it with `--allow`, and log it as `[derived] neutral added: #FFFFFF (palette has no
   light color)`. Never introduce a hue the user did not supply.
3. An accent that fails 4.5:1 with both `canvas` and `ink` for button text: keep it for large
   display text and decorative marks only, and make the button `ink` with `canvas` text. Log it.

## 4. Fonts in email

- Build every stack as `'Brand Font', <web-safe of the same class>`: serif -> `Georgia, 'Times New Roman', serif`;
  sans -> `Helvetica, Arial, sans-serif`; mono -> `'Courier New', monospace`.
- A Google Font can load through one `<link>` in the head (Apple Mail, iOS Mail, some Android).
  Gmail and Outlook will show the fallback, so pick a fallback with similar width.
- Typekit, self-hosted or licensed fonts: do not embed. Use the fallback and log `[inferred] display
  font <name> is licensed; email uses <fallback>`.
- Outlook gets the web-safe part of `body_stack` automatically.
- Fonts read from the site: set `brand.heading_source: "site"` so the brand's heading font beats a
  style that sets headings in the body font (bold-retail, clean-tech and others).
- Brand fonts unknown: use the chosen style's `fonts` pairing from `data/styles.json` (including its Google Fonts link) and log it `[inferred]`.

## 5. notes.md brand section (template)

```
## Brand profile
- Link: <url> (ok | unreachable: reason). Pages read: <list>
- Voice: <3 adjectives> [site]. Samples: "<verbatim>", "<verbatim>"
- Display font: <name> -> stack <stack> [site|inferred]
- Body font: <name> -> stack <stack> [site|inferred]
- Imagery: <one line> [site|asset]
- Palette roles: canvas #.. ink #.. ink2 #.. accent #.. on_accent #.. band #.. border #.. (contrast: ink/canvas 12.9, on_accent/accent 4.9 ...)
- Products used: <title, price, url> [site]
- Offer: none found | "<exact text>" code <CODE> terms "<text>" [site|brief]
- Policies used: <verbatim> [site]

## Inferred (please verify)
- <each [inferred] and [derived] item, one line, with why>
```
