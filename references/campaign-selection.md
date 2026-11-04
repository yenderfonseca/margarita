# Campaign selection: what to send, to whom, in which block order

Built on the Margarita library: the anatomy study (block order and pairing across 689 curated DTC
emails), the flow study (lifecycle flows), the flow recipes and the assembler's scoring. Lift = how much more often a pairing
appears in that theme than across the library; a pairing counts only when 3+ brands use it and no
brand is more than half the examples. The library has no open or click data: "best" means what many
strong brands converge on.

## 0. Occasion presets

`data/occasions.json` holds ready skeletons for calendar moments (BFCM, gift guide, last shipping
day, new year, Valentine's, Mother's and Father's Day with their opt-out practice, seasonal sale,
anniversary), product moments (launch, back in stock, VIP early access, bestsellers), relationship
moments (birthday, review request, referral) and the five flows. Each lists the facts it `needs`;
without them use its `no_offer_skeleton` or skip it. `build.py --scaffold <preset> <occasion>` turns
one into a starter spec.

## 1. Decide, then note it in one line

Order of authority: **brief > link > assets > defaults.** Write each decision to notes.md as
`Assumption: <decision> because <evidence>. Change: <what the user would say>`.

### Campaign type when the brief is silent

| What the link is | Default set |
|---|---|
| A product page | 1 email: `product-drop` (spotlight variant) for that product |
| A collection or new-arrivals page | 1 email: `product-drop` for that collection |
| A sale page, or the site shows a live offer | 1 email: `sale` (only with the real offer and its terms) |
| A blog post or guide | 1 email: `education` built on that article |
| The homepage, or nothing specific | 3-email starter: `welcome-story`, `product-drop` (bestsellers), `education` |
| The brief says "a welcome email" (one) | 1 email: `welcome-offer` if a real offer exists, else `welcome-story`. Without products or policies it closes on the cta alone (3 body blocks is fine) |
| The brief says "welcome series" / "flow" | The flow skeleton from section 4 |

Never pick `sale`, `welcome-offer` or a `cart`/`winback` incentive email without a real offer. If the
brief asks for one and no offer exists, build the no-offer variant and flag it.

### Audience when the brief is silent

- Broadcast: engaged subscribers who have not purchased (TOFU/MOFU). Note the suggested Klaviyo
  segment: "Engaged 90 days AND Placed Order zero times".
- Product drop or bestsellers: all engaged subscribers (customers included).
- Flows: the trigger defines the audience (section 4).

### Niche and playbook

Match the brand to `data/niches.csv` keywords, then to a playbook in `data/industry_playbooks.json`:

| Niche (library label) | Playbook slug |
|---|---|
| Fashion & Apparel | fashion_apparel |
| Beauty & Personal Care | beauty_skincare |
| Food & Beverage | food_beverage |
| Home & Living | home_living |
| Sports & Outdoor | sports_outdoor |
| Pet Supplies & Lifestyle | pet_supplies |
| Tech & Gadgets | tech_gadgets |
| Health & Wellness | health_wellness |
| Lifestyle & Retail, Jewelry, gifts, anything else | none: use the site's own voice and the anatomy study only, and log `[inferred] no playbook for <niche>` |

From a playbook take: tone, power words (only those the brand would say), `banned_phrases` (pass them to
preflight `--banned`), button shape (radius, case, tracking), photography ratio. **Never its palette
or its fonts**: the user's palette and the site's fonts win.

## 2. Taxonomy (the library's labels, for notes.md and Klaviyo naming)

- **flow_type:** Broadcast Campaign, Welcome Series, Cart & Checkout Abandonment, Browse Abandonment,
  Post-Purchase & Cross-Sell, Winback & Re-engagement.
- **funnel_stage:** TOFU, MOFU, BOFU, Retention & Loyalty.
- **intention:** Product Drop & Catalog, Discount & Incentive, Social Proof & Reviews, Objection &
  Comparison, Brand Story & Mission, Education & Guide, Urgency & FOMO.
- **copy_angle:** Brand Story & Heritage, Offer & Scarcity, FAQ & Objection Buster, Customer Proof &
  Reviews, Educational & Moats.

Klaviyo template name: `<Brand> | <flow_type or Campaign> | <NN> <theme> | <YYYY-MM>`.

## 3. Block order by theme (anatomy study; block types are listed by `build.py --list`; this table is the single source of skeletons)

Rules for every theme:
1. **3 to 6 body blocks** (curated median is 3 to 4). One idea per email.
2. **The opener sets the theme; the second block does the work** (answers, proves or converts).
3. **Proof is rare:** only 10% of curated emails carry a proof block. Use it where the job is trust
   (welcome, objection, cart email 2), never by default, and only with real quotes.
4. **Close with somewhere to go:** longer retail emails end on a trust row, not a dead end.
5. **The one primary CTA** (`cta` block) sits right after the block it converts; `build.py` refuses an email with zero or two.

| Theme | Opener (library share) | Skeleton (block types) | Evidence | Avoid |
|---|---|---|---|---|
| sale | offer-led 35%, image 27% | hero_image > hero_text (offer stated) > offer_code > cta > products > trust_row | offer then products 30 brands 1.9x; offer then code box 10 brands 2.2x | offer buried under an offer-less image; code only in the subject |
| product-drop | image 48%, headline 15%, offer 4% | hero_image > hero_text > story (short) > products or spotlight > cta | image, story, products 17 brands 1.7x | opening a launch with a discount; a grid with no reason it exists |
| welcome-offer | offer 35% | hero_image > hero_text > offer_code > cta > products | offer then code box 5 brands 4.2x (strongest found) | a code that is only in the subject |
| welcome-story | headline 26% | hero_text > story > cta > spotlight or trust_row | headline then brand story 4 brands 3.3x | long founder essays; two ideas |
| education | headline 27-32% | hero_image > hero_text > steps > cta > spotlight | headline then explanation 2.9x; explanation then products 3.4x | teaching without showing what to buy |
| objection | image 68% | hero_image > story (materials, craft) > spotlight > cta > trust_row | image then making-story 5 brands 3.0x | arguing without showing |
| social-proof | image 42% | hero_image > hero_text > reviews > cta > products | thin: no pairing passed the 3-brand rule | reviews in every email |
| cart (flow) | short familiar headline | hero_text > cart_items > cta > trust_row | thin (16 emails): the best show the cart with quantity and total | a discount in the first reminder |
| winback (flow) | warm miss-you headline | hero_text > products > cta | thin (4 distinct emails): warm opener, question-led follow-up | fake scarcity; a discount in email 1 |
| announcement | headline | announcement > hero_text > story > cta | design choice (no pairing data) | burying the news |
| founder note / letter | the letter itself | letter > cta | design choice; use the plain-note or founder-letter style | more than one ask |

Niche openers (anatomy study): image leads almost everywhere (35-52%). Health & Wellness and Pet
lean on headline or offer openers, which suits products that need explaining or a trial.

## 3b. Choosing the style (data/styles.json, 13 styles)

1. Find the niche in `data/niches.csv` (56 niches in 10 groups; match on keywords, else the nearest
   group). Its `styles` column lists 2 or 3 fitting styles, best first.
2. Pick the one that matches the brand's own site: its button shape (square, rounded, pill), heading
   case, density and mood. The site beats the niche default. Log `Style: <id> because <evidence>`.
3. Campaign type can override the look: `founder-letter` or `plain-note` for welcome-story, founder
   notes, winback and cart reminders; `text-only` for announcements, policy and shipping updates.
4. `dark-premium` wants a dark canvas. On a light palette the build swaps the darkest and lightest
   supplied colors (same palette, no new hue) and re-derives the rest; check the result in the gallery.
5. Not sure between two? Build both: `build.py spec.json --out <dir> --styles a,b` writes previews
   to `<dir>/_styles/`; render them and keep the one that looks most like the brand.
6. A niche row's `compliance` column lists claims that niche must not make (alcohol, supplements,
   CBD, finance, kids, eco). Copy follows it, and notes.md repeats it as a compliance flag.

## 4. Flows (flow study + recipes). Each email still follows section 3

**Rules for every flow:** the first email of any recovery flow carries no discount; incentives come
last, only with a real, approved offer and a real deadline; one job per email; every flow has an
exit condition; confirm every event variable in Klaviyo preview with a real event.

| Flow | Trigger / filters | Emails (timing: job) |
|---|---|---|
| Welcome | Joins newsletter list; optionally exclude customers | 4 by default: 0: welcome + first products (or offer + code box if a real welcome offer exists); +1-2d: what makes it different; +3-4d: the collection; +5-7d: proof (real reviews only) |
| Abandoned checkout | Started Checkout; not Placed Order since; Smart Sending on; re-entry 60d | 1h: light reminder, exact cart, no discount; 24h: objections (quality, warranty, returns); 48h: alternatives; 72h: final nudge, incentive only if approved |
| Browse abandonment | Viewed Product; not Started Checkout / Placed Order; 24-72h away from cart flow; re-entry 7-14d | 4h: the exact product viewed, no discount; +1d: why it is worth it, two alternatives; +2d: remove friction (shipping, returns), best sellers |
| Post-purchase | Placed Order; not in flow in 30d | 0: thank you + order summary; +3d: care or use guide, no selling; +10d: review request (say "tap a star" only if each star links to a rating); +21d: pairs well with; +45d: a reason to come back |
| Winback | Segment: 1+ orders, none in 120d (check the brand's median reorder time) | 0: we miss you, what is new, no discount; +5d: what held you back; +7d: a reason to return (offer only if approved); +5d: last call, deadline tied to the real offer; +10d unengaged: stay in touch, button to `{% manage_preferences_link %}` |

Event variables per flow are in `klaviyo.md` section 4.

## 5. Scoring when several blocks could fill a slot (from `email_assembler.py`)

`score = 0.35 goal + 0.25 audience + 0.20 tone + 0.20 evidence - staleness`. Goal: exact theme
match 1.0, related 0.5. Staleness: -0.15 each time the same block type appeared in the previous 4
emails of the set (header and footer exempt). Constraints: one offer per email; no two dense blocks
(products, reviews, steps) adjacent; no two buttons with the same label; no product repeated
across a set; a block whose facts are missing is dropped, never filled with filler.

## 6. Optional: a Margarita library MCP

If an MCP server with the Margarita library tools is connected, `search_emails` / `search_components`
with the niche and intention returns real reference emails. The skill works fully without it. Use them for layout and rhythm cues only: never copy their
copy, colors or brand names. Do not use any tool that rebrands or replicates a whole email: such tools rewrite Klaviyo unsubscribe
links to store URLs.
