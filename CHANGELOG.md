# Changelog

## 2.2 (2026-11-05)
- The library ships inside the skill: 16 example emails from fictional demo brands (10 niches, 6 occasions
  and flows), 37 previews including a tour of all 13 styles, `library/INDEX.md` and `library/index.json`.
- `scripts/library.py`: `find` queries the library, `index` rebuilds its previews and catalog.
- SKILL.md shows library previews before building when the user is choosing a look.
- Fix: 2-column product grids failed to build. CI now builds every library spec.
- `evals/test-prompts.json`, `agents/openai.yaml`, and install with `npx skills add yenderfonseca/margarita`.

## 2.1 (2026-11-05)
- Runs in Claude Code, Claude.ai and Google Antigravity: every path is relative to the skill folder.
- `--help` on every script.
- Story list (`link_list`): the arrow no longer wraps under long labels on phones.
- Dark mode: dark borders that melt into a dark surface (a coupon frame) get a visible color; text on lifted ink bars is checked against the lift.
- Product grids: the light plate behind photos shrinks with the phone image (no light bars in dark mode); cards without an eyebrow keep titles level.
- Popups: a local side image is copied next to the mockup; more space above the button. Gallery no longer overflows on phones.
- Full README, MIT license, CI self-tests.

## 2.0 (2026-11-04)
- 13 styles, 31 blocks, 56 niches, 10 presets, occasions and lifecycle flows, 8 sign-up form presets.
- `build.py` templating engine with preflight, import zip and `email.md`.
- `render.py` render check at 680, 375 and 320px, images off and dark mode.
- `gallery.py` and `popup.py`.
