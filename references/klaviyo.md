# Klaviyo: tags, footer, validation, import

Verified 2026-11-03 against Klaviyo's help center:
- Message personalization reference: https://help.klaviyo.com/hc/en-us/articles/4408802648731
- Troubleshooting template errors: https://help.klaviyo.com/hc/en-us/articles/4402386684187
- Importing a custom HTML template: https://help.klaviyo.com/hc/en-us/articles/115005254068

Re-check these pages if Klaviyo reports a tag error; the syntax below is what they documented that day.

## 1. Legal tags (preflight A1)

| Purpose | Full link (renders its own `<a>`) | URL only (goes inside your `href`) |
|---|---|---|
| Unsubscribe (required for marketing email) | `{% unsubscribe %}` or `{% unsubscribe 'Opt out' %}` | `{% unsubscribe_link %}` |
| Manage preferences | `{% manage_preferences %}` or `{% manage_preferences 'Email settings' %}` | `{% manage_preferences_link %}` |
| View in browser | `{% web_view %}` or `{% web_view 'Open in browser' %}` | `{% web_view_link %}` |

Margarita uses the URL-only forms inside styled links (the `footer` block). Never put a full-link
form inside `href`: it nests an `<a>` inside an attribute and breaks the link (preflight fails it).
Without any unsubscribe tag Klaviyo refuses an imported template ("An {% unsubscribe %} tag is
required") or appends its default footer at send time.

## 2. Sender identity (preflight A2)

Values come from the Klaviyo account (Settings > Account > Organization). Set them there; never
hard-code an address in the HTML.

| Tag | Output |
|---|---|
| `{{ organization.name }}` | Organization name |
| `{{ organization.full_address }}` | Full postal address (CAN-SPAM requires a physical address) |
| `{{ organization.url }}` | Website URL as text |
| `{{ organization.street_address }}`, `.city`, `.region`, `.zip_code` | Parts of the address |

Year: `{% current_year %}` is **not** in Klaviyo's reference (preflight fails it). If a year is
needed: `{% today "%Y" as year %}{{ year }}`. Margarita's footer omits the year.

## 3. Personalization (preflight A13)

- Always with a default: `{{ first_name|default:'there' }}`. Write the default in the brand's voice
  ("friend", "maker"). A bare `{{ first_name }}` renders empty for profiles without a name.
- Other profile fields: `{{ person.full_name }}`, `{{ person.City }}`,
  `{{ person|lookup:'Custom Property' }}` (lookup for names with spaces or `$`).
- Conditionals: `{% if first_name %}Hi {{ first_name }},{% else %}Hi there,{% endif %}`. Every `if`
  needs `endif`, every `for` needs `endfor` (unclosed tags fail the parser).
- Only `{{ }}` and `{% %}` are parsed. `*|FNAME|*` (Mailchimp), `%%tag%%`, `{{{ }}}` and Liquid-only
  filters (`| money`, `| map`) are not Klaviyo; remove them.
- Watch quotes inside tags: "Could not parse the remainder" means misplaced or repeated quotes, a
  space in a property name, or a bad filter.

## 4. Flow event variables (flow study; names vary by account, confirm in Klaviyo preview with a real event)

| Flow | Variables |
|---|---|
| Abandoned checkout | `{% for item in event.extra.line_items %}...{% endfor %}`, `{{ item.product.title }}`, `{{ item.quantity }}`, `{{ item.line_price }}`, `{{ item.product.images.0.src }}`, `{{ event.extra.checkout_url }}` (or `responsive_checkout_url`), `{{ event.value }}` |
| Browse abandonment | `{{ event.ProductName }}` (or `event.Name`), `{{ event.URL }}`, `{{ event.ImageURL }}`, `{{ event.Price }}` |
| Post-purchase | `{{ event.extra.order_name }}`, `{% for item in event.extra.line_items %}`, `{{ event.extra.order_status_url }}` |
| Coupons | `{% coupon_code 'Coupon Name' %}`: a unique code from a coupon set up in Klaviyo (Coupons tab). Only with a coupon the user named |

The `cart_items` block renders the checkout loop (`{% for item in event.extra.line_items %}` with image, title, quantity and line price). Pair it with a `cta` whose url is `{{ event.extra.checkout_url }}`.

## 5. Links and tracking (preflight A5)

- Append UTM to every link to the brand's site:
  `?utm_source=klaviyo&utm_medium=email&utm_campaign=<brand>_<NN>-<theme>` (use `&` if the URL
  already has a `?`). Klaviyo's own UTM tracking can add these too; keep them consistent.
- Every link points somewhere real: no `href="#"`, no empty href.
- Social links need no UTM.

## 6. Images and the import zip (preflight A14)

- Images on the brand's site: reference the full `https://` URL.
- Images from the asset folder: keep them in `images/` next to `email.html` and reference them
  relatively (`images/hero.jpg`). Zip `email.html` and `images/` together; on import Klaviyo copies
  each image to its CDN and rewrites the reference. The path in the zip must match the HTML exactly.
- Each image 10 MB or smaller. JPG, PNG, GIF. No empty `background=""` attributes.

```bash
cd <email folder> && python3 -m zipfile -c klaviyo-import.zip email.html images/   # never .source/ or render-*.png
```

## 7. Import and send checklist (goes in notes.md)

1. Klaviyo > Content > Templates > Create template > Import (or the code editor) > upload
   `klaviyo-import.zip` (or paste `email.html` when every image is hosted).
2. Name it as in email.md. Set the subject and preview text in the campaign or flow message (they
   live outside the template). Paste subject A and B into an A/B test.
3. Preview with a real profile (and a real event for flows): the name default, coupon and loops
   resolve; no `{{` or `{%` shows literally.
4. Confirm Settings > Organization has the real name and postal address.
5. Send a test to Gmail, Apple Mail and Outlook; check dark mode and images off.

API alternative (when a Klaviyo connector or key is available): `POST /api/templates` with
`{"data":{"type":"template","attributes":{"name":"...","editor_type":"CODE","html":"..."}}}`.
Images must already be hosted for this route.
