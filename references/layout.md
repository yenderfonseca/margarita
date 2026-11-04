# Layout and visual design

Sources: the Margarita house style, its client-safety and QA checklists, and its dark-mode rules.
The blocks in
`assets/blocks.html`, rendered by `scripts/build.py`, already follow everything here; this file is for judgment calls.

## 1. Taste: what "considered" means in an email

- **One focal point per screen.** At 375px the reader sees about 600px of height at a time: each
  screenful should carry one thing (an image, a headline, a button), not three.
- **Rhythm from two backgrounds.** Alternate `canvas` and `band` to separate sections instead of
  rules and boxes. At most one `band` in a row.
- **Type does the hierarchy.** Display 40/46, h2 28/34, body 16/26, small 13/20, label 11/16 uppercase
  tracked 0.14em. Three sizes per email in practice. Mobile: display 30/36, h2 24/30.
- **Left or center, not both.** Center for short campaign emails; left for letters, story-led and
  text-heavy emails (the letter styles are left-aligned).
- **Whitespace is the luxury signal.** 48px section padding, 48px side gutters (24px on phones).
- **Button shape from the brand:** square (0px) for editorial and fashion, 4px for most, pill (999px)
  only if the site's buttons are pills. Case and tracking match the site's buttons.
- **Photography:** use the site's crop ratio. Hero 4:5 or 3:2; never stretch, never upscale past the
  source; sharp at 2x (1200px wide for a 600px slot).
- **Restraint:** no gradients, no drop shadows, no emoji bullets, no clip-art icons, no stock photos.

## 2. Mobile-first

- Build at 600px, check at 375px. The 620px breakpoint in `shell.html` stacks `.m-stack` columns,
  narrows gutters (`.m-pad`), makes the primary button full width (`.m-btn`) and shrinks headings.
- Two-column blocks stack with the image first.
- Tap targets: 48px tall minimum for the button, 44px for any other link (footer links get 6px
  padding for this reason).
- Body text never below 16px; small print never below 12px.

## 3. Spacing (house style: breathing room)

- Every block carries its own top and bottom padding (48px default, 24-40px for bands). Never ship a
  block with `padding:0 Xpx 0`; it leans on neighbors and collapses when one is removed.
- At least 24px between stacked blocks and interactive elements (buttons, cards, images, bands);
  28 to 32px above the primary CTA (the `cta` block's top padding). Text inside one block keeps its
  own tighter rhythm (label to headline 14px, headline to subhead 16px).
- Gap collapse (automatic in build.py): neighbours on the same background share one gap, so the lower
  block's top padding goes to 0; the block right above `cta` drops its bottom padding. Otherwise
  two 48px paddings stack into a 96px hole.
- Padding on `<td>`, never on `<table>` (clients ignore table padding).
- An optional slot with no data is deleted, not left as an empty strip.

## 4. Images off (Outlook desktop and many corporate inboxes block images by default)

The email must still read and convert with every image blocked:
1. **Live text for all words.** Headline, offer, price, button: never inside an image.
2. **Descriptive alt** on every content image: what it shows plus why it is there
   ("The Harbor Mug in sea-glass glaze on a linen cloth"), never the filename, never "image".
   Decorative spacers and dividers get `alt=""`.
3. **Styled alt:** the `<img>` carries `font-family`, `font-size`, `line-height` and `color` so the
   alt text renders like copy (blocks do this).
4. **bgcolor on the image cell** (`band`) so the layout keeps its shape and color.
5. **Width set, height auto.** No fixed heights that leave a blank hole.
6. **Ratio:** at least about 250 characters of live text per email; an image-only email is a FAIL
   in spirit even if it passes code (preflight warns under 250).

## 5. Email-client safety (preflight A6, A8, A16)

- Tables with `role="presentation"`, 600px shell inside an MSO ghost table.
- Inline styles on every element; the `<style>` block only holds resets, the breakpoint and dark
  mode (Gmail keeps head styles, older clients do not).
- Bulletproof button: VML `v:roundrect` for Outlook plus an HTML anchor for everyone else (the `cta`
  block). Never an image button.
- No SVG, `position:absolute`, flexbox, grid, `<script>`, `<form>`, `<iframe>`, `<video>`,
  background-image-only heroes, or CSS animations carrying meaning.
- Web fonts degrade to the stack; Outlook gets the web-safe part of the body stack.
- Keep the HTML under 102 KB (Gmail clips the rest, including the footer and unsubscribe).

## 6. Dark mode (preflight A7)

Dark mode colors come from the palette too: `dark_bg` is the darkest supplied color, `dark_text` the
lightest, with `dark_band`, `dark_border` and `dark_accent` mixed from them. `build.py` assigns the
dark-mode classes itself (Apple Mail, iOS Mail, and `[data-ogsc]`/`[data-ogsb]` for Outlook.com): it
follows the surface each element really sits on. Surfaces close to the canvas turn dark; accent bands,
inverse bars and image cells keep their colors, and so does the text on them. Any text that would drop
under 4.5:1 moves to `dark_text`, `dark_text2` or `dark_accent`, light hairlines go `dark_border`, and
an ink button that would melt into the dark canvas flips to a light button, and ink bars
(announcement, inverse footer, accent band) lift to `dark_lift` so they still read as bands. Headlines
stay the brightest text in dark, as they are the darkest in light. `render.py` renders the
email with dark mode on and fails any text under 3:1 against its real background. Dark styles
(dark canvas) are left as they are. Gmail apps do a forced partial invert you cannot control, so:
- Avoid pure `#000000` on pure `#FFFFFF` when the palette offers softer ends.
- **Logos:** a dark logo on a transparent PNG disappears on dark backgrounds. Use a logo file with a
  light outline or its own background tile, or the wordmark text header. Log which.
- The accent should keep at least 3:1 against both `canvas` and `dark_bg` (check with `contrast`);
  if it cannot, the button still works because its text color is set explicitly.
- Bands and dividers stay subtle: no harsh breaks between modes.

## 7. Orphans and widows (standing rule)

No single word alone on the last line of a heading, eyebrow, button label, tagline or short
paragraph, at 600px or 375px. Glue the last two words with `&nbsp;` (email clients ignore
`text-wrap`). Multi-part lines (trust chips, a tagline) glue each phrase so it breaks only at the
separator. Hyphenated compounds ("hand-poured") can break at the hyphen on phones: wrap them in
`<span style="white-space:nowrap;">`. If a line still orphans at 375px, shorten it.

## 8. Render check (step 7 of the workflow)

```bash
python3 scripts/render.py <email folder>/email.html
```
Needs Playwright for Python (`pip install playwright`); it uses Playwright's Chromium or falls back
to the installed Chrome. It writes `render-680.png` (desktop: the 600px shell sits above the 620px
breakpoint only in a wider window), `render-375.png` (phone) and `render-375-images-off.png` (each
image swapped for its styled alt text, as blocking clients show it), and prints JSON. It FAILs on
horizontal overflow, orphan words (measured per line box), broken images and a button under 44px.

Then look at the three screenshots yourself for what code cannot judge: sections with real content,
no stretched or blurry images, no cramped stacks or holes, the email still readable images-off, the
footer present, and whether it looks like the brand. Record PASS, or FAIL with each defect's
location and fix. Fix, re-render, re-check. If the user's own instructions require a separate
design-QA agent, run that too and report its verdict.
