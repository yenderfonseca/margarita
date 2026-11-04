# Copy: subject, preview text, body, CTA

Sources: the Margarita subject study (675 curated DTC subject lines), the Margarita house style and
the Margarita subject-line and email-QA guides. Preflight enforces the numbers (codes in brackets).

## 1. Sound like the brand, not like marketing

Before writing, put the 3 to 5 verbatim voice samples from intake next to you and match:
- **Sentence length and rhythm.** If the site writes "Built to order. Shipped in a week.", so do you.
- **Person.** Their "we/you" balance; their name for customers if they use one.
- **Register.** Formal, warm, dry, playful. Humor only if the site jokes.
- **Their words.** Reuse nouns they repeat (materials, place names, product names). Power words from
  the playbook only if the brand would say them.
- **Emoji, caps, exclamation marks:** only at the rate the site uses them. Default: none.

Test each line: could a competitor send it unchanged? Then it is generic. Replace an adjective with a
fact (material, number, place, process) taken from the site.

**Filler to cut on sight:** "elevate", "unlock", "discover the magic", "game-changer", "curated
just for you", "we're so excited", "look no further", "treat yourself", "must-have", "in today's
world", "take your X to the next level", "don't miss out" (without a real deadline), "best-in-class",
"seamless". Also any sentence that restates the headline.

## 2. Subject lines [B]

| Rule | Detail |
|---|---|
| Length | Target 30 to 45 characters (curated median 32; phones cut near 35 to 40). Warn over 50, fail over 60 |
| Shape | One idea, stated. Name the product, the offer or the benefit. Statements, not questions (questions only for education and cart reminders) |
| Offer | An offer email states the real offer plainly. No offer means the subject must not imply one |
| Caps | At most one word in caps. No ALL CAPS subject |
| Punctuation | No `!!`, `?!`, `!?`. Prefer no exclamation mark at all on promo subjects |
| Emoji | At most one, only if the brand's own site or social uses them, never in place of a word |
| Personalization | `{{ first_name\|default:'there' }}` (no backslash in the HTML) with a default in the brand's voice; never a bare tag [A13] |
| Spam triggers [S] | free, guarantee, 100%, winner, urgent, act now, limited time, buy now, click here, risk-free, cash, cheap, lowest price, miracle, order now: only when a real offer, policy or deadline backs them ("Free shipping over $75" is fine if the policy says so) |
| Truth | What the subject promises, the email delivers |
| Options | Write **two** per email for an A/B test, differing in one variable (named in email.md) |

Theme habits (subject study):

| Theme | Length | Habit | Library example |
|---|---|---|---|
| Sale | ~34 | States the offer plainly | "Our biggest sale ever / 25% Off everything" |
| Product drop | ~30, 5 words | Shortest; names the product or collection | "Solid Hardwood. Built to Order." |
| Objection | ~34 | Product leads, argument lives in the body | "Meet the Moose Behind Moose" |
| Education | ~39, longest | Speaks to "you" (60%) | "Kickstart Your Blendtec Journey with 3 Recipes" |
| Brand story | ~31 | No questions, no caps; colon or pipe in 36% | "Celebrating 10 years of failures at Gantri" |
| Social proof | ~34 | States the proof as news | "We ran an actual sleep study." |
| Welcome | ~35 | Offer in 15%; never a question | "Welcome to Huha" |
| Cart | ~33 | 80% speak to "you"; short, familiar | "Forgot something?" |
| Post-purchase | ~41 | Practical (delivery, care, rewards) | |

Approaches to choose the A/B pair from: value-forward (states the payoff), specificity (a number,
product or material), curiosity gap (a loop the body closes, never bait), direct announcement
("New: <product> is here"), personalization (mirrors the reader's situation).

## 3. Preview text [B]

- At most 100 characters (aim 40 to 90). It **completes** the subject: the subject states the idea,
  the preview adds the reason or the detail. Never repeats the subject or its first words.
- Lives in the hidden div right after `<body>` (the spec's `preheader`), padded with `&zwnj;`
  so the inbox does not pull body text after it.
- Same house style as the subject.

## 4. Body

- **Headline:** 2 to 8 words, the idea of the email. Glue the last two words with `&nbsp;`.
- **Subhead:** one sentence, 12 to 25 words, a concrete detail.
- **Story / education blocks:** at most 120 words; 60 to 120 when the sources are rich, 25 to 60
  when they are thin. Never pad to reach a length: a short true block beats a long invented one.
  Short paragraphs. One fact per sentence. No promises about future emails or products unless the
  brief makes them.
- **Product cards:** title and price exactly as on the site. No invented descriptors.
- **Readable at a glance:** someone who reads only the headline, the button and the image alt text
  must understand the email.
- **Facts only from sources** [manual, logged in notes.md]: prices, codes, deadlines, stock levels,
  reviews, stats, awards, shipping and returns, "handmade", "organic", "best-selling". Missing fact
  means the line goes, not that a plausible one is written.
- **No fake urgency:** "last chance", "ending soon", "only X left" need a real, sourced deadline or
  stock number.
- **Exclamation points:** none by default; never two in a row [B]; two per email at most.

## 5. The CTA

- One primary button per email [C1, C3], 2 to 4 words, verb first, says where it goes:
  "Shop the Harbor Mug", "Read the guide", "Claim 15% off" (only with a real offer).
  Not "Click here", "Learn more" (unless it truly is an article), "Submit".
- Glue the last two words with `&nbsp;` so the label never orphans.
- Secondary destinations are text links (spotlight `link_label`, or a text link inside copy), worded as specifically as the button.
- Copy matches what the link does: "Manage your emails" must go to `{% manage_preferences_link %}`;
  "Tap a star to rate" only if each star links to a rating.

## 6. House style [A11]

- No em dashes or en dashes, raw or as `&mdash;` / `&ndash;`. Rewrite with a comma, colon or period.
- Straight quotes only (`"` `'`), never curly or `&ldquo;`.
- No orphan words: glue the last two words of headings, labels, buttons and short lines with `&nbsp;`;
  for multi-part lines glue each phrase. Also set `text-wrap: balance` on headings (blocks do).
- Numbers as numerals, currency as the site displays it.

## 7. email.md template (one per email)

```
# NN <theme>: <one-line idea>
- Audience: <segment>      - Send: <campaign date or flow position + delay>
- Klaviyo name: <Brand> | <Campaign or flow_type> | NN <theme> | YYYY-MM

## Subject A (NN chars): ...
## Subject B (NN chars): ...
A/B variable: <what differs>
## Preview text (NN chars): ...

## Copy (as it appears, top to bottom)
- [hero_image] alt: "..."
- [hero_text] label / headline / subhead
- [story] ...
- [cta] "<label>" -> <url with UTM>
- [footer] signup reason: "..."

## Sources for every fact in this email
- "<claim>" <- <url or asset file>
```
