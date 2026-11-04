# spec.json: what `scripts/build.py` renders

One spec per brand run. Write it to `<out>/<brand-slug>/spec.json`, then:

```bash
python3 scripts/build.py <out>/<brand-slug>/spec.json --out <out>/<brand-slug>
python3 scripts/build.py --list      # styles and blocks with required fields
```

The build renders every email, copies local images into `images/`, writes `klaviyo-import.zip`,
`email.md` and `preview.html` (sample values in place of Klaviyo tags, for review only; import
`email.html`), then runs preflight. Exit 0 = every email PASS; 1 = a preflight FAIL; 2 = a build error
(missing field, unknown block, palette contrast). Fix the spec and rebuild; never hand-edit
`email.html` (the next build overwrites it).

Working example with every block: `assets/example.spec.json`.

## Top level

```json
{
 "style": "editorial",                  // data/styles.json id; an email can override with its own "style"
 "utm_prefix": "harbor",                // utm_campaign = <prefix>_<email slug>
 "assets_dir": "/path/to/asset/folder", // relative image paths resolve here
 "banned": ["phrase", "..."],           // playbook banned_phrases + brief; preflight A10
 "allow": ["#FFFFFF"],                  // logged neutrals outside the palette (brand-intake section 3)
 "brand": {
  "name": "Harbor & Kiln",
  "home_url": "https://brand.com/",     // links on this domain get UTM automatically
  "logo_src": "logo.png",               // optional; without it the header shows the name as a wordmark
  "logo_width": 140,
  "heading_stack": "'Fraunces', Georgia, serif",
  "body_stack": "'Inter', Helvetica, Arial, sans-serif",
  "fonts_link": "https://fonts.googleapis.com/css2?family=...",   // optional
  "heading_source": "site",             // the heading font was read from the brand's site: it beats a style's
                                        // "headings in the body font" token (bold-retail, clean-tech, ...)
  "lang": "es",                         // html lang and the fixed words (footer legal links, "Hi", "Qty"):
                                        // en es pt fr de it built in; other languages need "words"
  "words": {"unsubscribe": "..."},      // optional override: hi qty unsubscribe preferences web_view
  "palette": {"canvas": "#", "ink": "#", "accent": "#"}   // required; any other role is optional:
              // page band border ink2 on_accent dark_bg dark_text dark_text2 accent_text.
              // Missing roles are derived by mixing these three (printed as [derived]; copy them to notes.md)
 },
 "emails": [ ... ]
}
```

## One email

```json
{
 "slug": "01-product-drop", "theme": "product-drop", "idea": "one line",
 "audience": "Engaged 90 days, never purchased", "send": "Campaign",
 "klaviyo_name": "Brand | Campaign | 01 product-drop | 2026-11",
 "subject": ["Subject A", "Subject B"], "ab_variable": "what differs", "preheader": "Preview text",
 "style": "optional override",
 "blocks": [ {"type": "header"}, ..., {"type": "cta", ...}, ..., {"type": "footer", ...} ],
 "sources": [{"claim": "12 oz, thrown by hand", "source": "https://brand.com/products/mug"}]
}
```

Exactly one `cta` per email (the build refuses zero or two). Start with `header`, end with `footer`.

## Blocks (required fields in bold)

| type | fields | notes |
|---|---|---|
| `announcement` | **text**, url | Accent bar at the very top. Real news or a real offer only |
| `header` | layout (centered, split, inverse), links, tagline | Centered logo (links become a nav row), split (logo left, links right) or an inverse ink bar; `brand.logo_inverse_src` for a light logo |
| `hero_image` | **src, alt, url** | Full-bleed photo, 1200px wide or more |
| `split_hero` | **src, alt, url, headline**, label, subhead, image_right | Image beside text; stacks on phones |
| `hero_text` | **headline**, label, subhead, greeting_default | `greeting_default` adds `Hi {{ first_name\|default:'...' }},` |
| `image_band` | **src, alt**, url, caption | Lifestyle photo with no product |
| `story` | **body** (string or list of paragraphs), heading, label, signature, signature_title | Brand, founder, materials, craft |
| `letter` | **body, signature**, greeting_default, signoff, signature_title | Plain personal letter, always left-aligned |
| `quote` | **quote, author**, author_title, photo | A real quote (founder, expert, press); photo is a round headshot |
| `cta` | **label, url**, note | The one primary button, bulletproof for Outlook |
| `offer_code` | **code**, label, terms | Only a real code; `{% coupon_code 'Name' %}` for Klaviyo unique codes |
| `products` | **items** [{**title, url**, src, alt, price, was_price, label, link_label}], heading, columns | 2 or 3 columns (auto: 3 or 6 items = 3). Same image ratio for all |
| `spotlight` | **src, alt, url, title**, label, text, price, link_label, image_right | One product with a reason |
| `category_tiles` | **items** [{**title, url**, src, alt}], heading | 2 per row |
| `steps` | **items** [{**title**, text}], heading, intro | Numbered 01, 02... automatically |
| `comparison` | **left_label, right_label, rows** [{label, left, right}], heading | Only sourced facts in each cell |
| `faq` | **items** [{**q, a**}], heading | Objections answered with site facts |
| `reviews` | **items** [{**quote, author**, stars, photo}], heading | Real reviews only; `stars` only if the source shows the rating |
| `trust_row` | **items** [{**text**}] | 2 or 3 real policies |
| `overlay_hero` | **src, headline, url**, label, subhead, height | Live text over a photo (VML for Outlook). The photo must already be darkened where the text sits; with images off the text shows on `dark_bg` |
| `stats_row` | **items** [{**value, label**}], heading | 2 or 3 real numbers; stays in one row on phones |
| `feature_grid` | **items** [{**title**, text, icon_src}], heading | 3 features; icons are PNG files (never emoji); stacks on phones |
| `ingredients` | **items** [{**title**, text, src}], heading | Ingredient or material callouts, round image left |
| `press_strip` | **items** [{**name**, src}], heading | Real press only; logo image or the outlet's name as text |
| `media_rows` | **items** [{**src, alt, title**, text, url, label, link_label}], heading | Zigzag image/text rows; stacks on phones |
| `mosaic` | **items** (1 or 3 [{**src, alt**, url}]) | One large image, then two side by side (stay paired on phones) |
| `link_list` | **items** [{**label, url**}], heading | Stacked category or menu rows with arrows |
| `disclaimer` | **text** | Bordered small print: FDA, legal-age, financial or offer terms the niche requires |
| `cart_items` | heading | Klaviyo checkout loop for abandoned-cart flows |
| `social` | **items** [{**label, url**}] | Text links to the brand's channels |
| `footer` | **signup_reason**, layout (simple, rich, inverse), note, links, social, contact | Klaviyo legal tags and organization address are built in; rich and inverse add logo, brand note, nav and social |

Text you write may use `&nbsp;` and `<br>`. The build adds the last-two-word glue, straight quotes,
nowrap on hyphenated words in headings, UTM on brand links, the Outlook button width and case, and
picks label and star colors that pass contrast. It warns when grid images differ in shape or are too
small for a sharp 2x render; crop or replace them before shipping.
