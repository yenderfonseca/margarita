# Popups: Klaviyo native sign-up forms

Margarita designs sign-up forms for Klaviyo's form editor. It never ships custom site code: Klaviyo
handles consent, frequency, targeting and A/B tests. Each popup gets a rendered mockup and a build
sheet with the exact settings to enter. Options verified 2026-11-04 on help.klaviyo.com:
- https://help.klaviyo.com/hc/en-us/articles/360026474752 (getting started, steps, components)
- https://help.klaviyo.com/hc/en-us/articles/4413544555547 (targeting and behavior)
- https://help.klaviyo.com/hc/en-us/articles/4406161800987 (mobile)

## Pick a preset (data/popups.json)

| Preset | Type | Use when |
|---|---|---|
| `welcome-offer` | popup | A real first-order offer exists (feeds the welcome flow) |
| `newsletter-no-offer` | flyout | The brand does not discount; content leads |
| `exit-intent` | popup | Second chance on product and collection pages |
| `sms-two-step` | popup | The brand sends SMS: email step, then phone step with disclosure |
| `birthday-capture` | embed | Feed the birthday flow (date input) |
| `launch-waitlist` | full page | Before a launch or restock, on its own landing URL |
| `holiday-early-access` | popup | Before a real sale or BFCM; countdown only to the real start |
| `preference-quiz` | popup | Wide catalogs: one radio question, then email; answer saved for segments |

Occasions in `data/occasions.json` name their matching popup in `popup`.

## Spec (the same spec.json as the emails)

```json
"popups": [{"slug": "welcome", "preset": "welcome-offer",
  "image": "hero.jpg", "label": "Welcome", "headline": "10% off your first bag",
  "subhead": "What they get and how often", "button": "Get my 10% off",
  "offer": "10% off the first order", "terms": "One use per customer.", "decline": "No thanks",
  "success_headline": "Your code is ready", "success_text": "It is in your inbox too.", "code": "HELLO10",
  "teaser": "Get 10% off"}]
```

Other fields by preset: `countdown_to` (a real date), `question` and `options` (quiz),
`sms_headline` and `sms_disclosure` (SMS step), `style` (override). Run:

```bash
python3 scripts/popup.py <spec.json> --out <out>/<brand>
```

It writes `popups/<slug>/mockup.html` (desktop over a dimmed page, phone, every step, success,
teaser) and `popups/<slug>/build-sheet.md`, and fails on missing required copy.

## Rules

- **Offer popups need a real offer and its terms** (the check fails without them). A code shown on
  the success step is static; for one code per person use a Klaviyo unique coupon in the coupon block.
- **SMS consent needs disclosure language** wherever the phone is collected (Klaviyo requires it).
  Alcohol and CBD brands add the age line, and Klaviyo's age gate input where SMS is used.
- **Countdowns only to real dates.** No evergreen timers.
- **Say what they get and how often** in the subhead.
- **Decline links are plain** ("No thanks"), never shaming.
- **Mobile:** side image set to Desktop, click-outside-to-close off on mobile, a large close icon,
  side margins; flyouts dock to the bottom.
- **Search traffic:** on pages that rank organically, use a time delay so the form does not cover
  the content at once.
- **Exclude existing profiles** for acquisition forms; early-access forms include them.
- Same house style as email: no dashes, straight quotes, no stacked exclamation points, last two
  words glued.
